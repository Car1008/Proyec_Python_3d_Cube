# rubik_sim/render/cube_gl_widget.py
import math

from PySide6.QtCore import Qt, QPoint, QTimer, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import (
    glClearColor, glClear, glEnable, glDisable, glViewport,
    glBegin, glEnd, glColor3f, glVertex3f,
    glMatrixMode, glLoadIdentity, glRotatef, glTranslatef,
    glReadPixels, glFlush,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST,
    GL_PROJECTION, GL_MODELVIEW, GL_QUADS,
    GL_RGB, GL_UNSIGNED_BYTE,
    GL_DITHER, GL_BLEND
)
from OpenGL.GLU import gluPerspective



class CubeGLWidget(QOpenGLWidget):
    """
    Rubik render OpenGL clásico (sin shaders):
    - Cubo plástico + stickers 3x3
    - Picking por color (HiDPI OK)
    - Highlight
    - Drag (cámara-aware) => movimiento por capa (incluye E/M/S)
    - Animación suave con QTimer
    """
    move_applied = Signal(str)
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

        # Cámara / orbit
        self.yaw = 35.0
        self.pitch = -20.0
        self.distance = 6.0

        self._last_mouse_pos = QPoint()
        self._orbiting = False

        # Stickers
        self.sticker_margin = 0.04
        self.sticker_offset = 0.01


        # Selección
        self.selected = None

        # Drag
        self._dragging_left = False
        self._drag_start = QPoint()
        self._drag_hit = None
        self._drag_threshold = 14

        # Animación
        self.animating = False
        self.anim_move = None
        self.anim_axis = None      # 'x','y','z'
        self.anim_layer = None     # -1,0,1
        self.anim_sign = 1         # +1 o -1
        self.anim_angle = 0.0
        self.anim_target = 90.0
        self.anim_step = 6.0       # deg/frame

        self._move_queue = []
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self.setFocusPolicy(Qt.ClickFocus)

    # --------------------------
    # OpenGL lifecycle
    # --------------------------
    def initializeGL(self):
        glClearColor(0.10, 0.10, 0.12, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        if h == 0:
            h = 1

        dpr = self.devicePixelRatioF()
        fb_w = int(w * dpr)
        fb_h = int(h * dpr)

        glViewport(0, 0, fb_w, fb_h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = fb_w / float(fb_h)
        gluPerspective(45.0, aspect, 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._apply_camera()

        # self._draw_plastic_cube()  # desactivado: se reemplaza por plástico por sticker


        # Stickers: primero NO animados, luego animados encima
        self._draw_stickers_pass(animated_only=False)
        if self.animating:
            self._draw_stickers_pass(animated_only=True)

    def _apply_camera(self):
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -self.distance)
        glRotatef(self.pitch, 1.0, 0.0, 0.0)
        glRotatef(self.yaw, 0.0, 1.0, 0.0)

    # --------------------------
    # Interacción
    # --------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._orbiting = True
            self._last_mouse_pos = event.pos()
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            hit = self.pick_sticker(event.pos().x(), event.pos().y())
            self.selected = hit
            self._dragging_left = True
            self._drag_start = event.pos()
            self._drag_hit = hit

            if hit:
                face, r, c = hit
                msg = f"Seleccionado: {face} (fila={r}, col={c})"
            else:
                msg = "Sin selección."

            w = self.window()
            if hasattr(w, "statusBar") and w.statusBar():
                w.statusBar().showMessage(msg, 2000)
            else:
                print(msg)

            self.update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Orbit
        if self._orbiting:
            dx = event.position().x() - self._last_mouse_pos.x()
            dy = event.position().y() - self._last_mouse_pos.y()
            self._last_mouse_pos = event.pos()

            sens = 0.4
            self.yaw += dx * sens
            self.pitch += dy * sens
            self.pitch = max(-89.0, min(89.0, self.pitch))

            self.update()
            event.accept()
            return

        # Drag izquierdo => movimiento (con animación)
        if self._dragging_left and (event.buttons() & Qt.LeftButton):
            if not self._drag_hit or self.animating:
                return

            dx = event.position().x() - self._drag_start.x()
            dy = event.position().y() - self._drag_start.y()

            if abs(dx) < self._drag_threshold and abs(dy) < self._drag_threshold:
                return

            face, r, c = self._drag_hit
            move = self._decide_move_from_drag(face, r, c, dx, dy)

            if move:
                self.start_move_animation(move)

                w = self.window()
                if hasattr(w, "statusBar") and w.statusBar():
                    w.statusBar().showMessage(f"Move: {move}", 1200)
                else:
                    print("Move:", move)

            self._dragging_left = False
            self._drag_hit = None
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self._orbiting:
            self._orbiting = False
            event.accept()
            return

        if event.button() == Qt.LeftButton and self._dragging_left:
            self._dragging_left = False
            self._drag_hit = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.distance -= delta * 0.3
        self.distance = max(2.5, min(20.0, self.distance))
        self.update()
        event.accept()

    # --------------------------
    # Picking (color picking)
    # --------------------------
    def pick_sticker(self, x, y):
        if self.animating:
            return None

        dpr = self.devicePixelRatioF()
        gl_x = int(x * dpr)
        gl_y = int((self.height() - y - 1) * dpr)

        self.makeCurrent()

        glDisable(GL_DITHER)
        glDisable(GL_BLEND)

        # pass picking
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._apply_camera()
        mapping = self._draw_all_stickers_pick()

        glFlush()

        pixel = glReadPixels(gl_x, gl_y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)

        # restaurar clear color “normal”
        glClearColor(0.10, 0.10, 0.12, 1.0)

        if pixel is None:
            return None

        if isinstance(pixel, (bytes, bytearray)):
            r, g, b = pixel[0], pixel[1], pixel[2]
        else:
            try:
                r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
            except Exception:
                return None

        pick_id = r + (g << 8) + (b << 16)
        return mapping.get(pick_id, None)

    def _encode_id_color(self, pick_id: int):
        r = (pick_id & 0xFF) / 255.0
        g = ((pick_id >> 8) & 0xFF) / 255.0
        b = ((pick_id >> 16) & 0xFF) / 255.0
        return (r, g, b)

    # --------------------------
    # Animación
    # --------------------------
    def _move_to_params(self, move: str):
        base = move[0].upper()
        table = {
            "U": ("y",  1, +1),
            "D": ("y", -1, -1),
            "R": ("x",  1, -1),
            "L": ("x", -1, +1),
            "F": ("z",  1, -1),
            "B": ("z", -1, +1),
            "M": ("x",  0, +1),
            "E": ("y",  0, -1),
            "S": ("z",  0, -1),
        }
        return table[base]

    def _parse_move_for_anim(self, move: str):
        axis, layer, sign_base = self._move_to_params(move)
        suffix = move[1:] if len(move) > 1 else ""

        sign = sign_base
        target = 90.0

        if suffix == "":
            pass
        elif suffix == "'":
            sign *= -1
        elif suffix == "2":
            target = 180.0
        else:
            raise ValueError(f"Sufijo no soportado: {move}")

        return axis, layer, sign, target, move

    def start_move_animation(self, move: str):
        if self.animating:
            self._move_queue.append(move)
            return

        self.anim_axis, self.anim_layer, self.anim_sign, self.anim_target, self.anim_move = self._parse_move_for_anim(move)
        self.anim_angle = 0.0
        self.animating = True
        self._anim_timer.start()

    def _on_anim_tick(self):
        if not self.animating:
            self._anim_timer.stop()
            return

        self.anim_angle += self.anim_step
        if self.anim_angle >= self.anim_target:
            self.anim_angle = self.anim_target
            self._finish_move_animation()
            return

        self.update()

    def _finish_move_animation(self):
        move = self.anim_move

        self.animating = False
        self._anim_timer.stop()

        self.anim_axis = None
        self.anim_layer = None
        self.anim_sign = 1
        self.anim_angle = 0.0
        self.anim_target = 90.0
        self.anim_move = None

        self.model.apply_move(move)
        self.move_applied.emit(move)

        self.update()

        if self._move_queue:
            nxt = self._move_queue.pop(0)
            self.start_move_animation(nxt)

    # --------------------------
    # Render helpers
    # --------------------------
    def _draw_plastic_cube(self):
        plastic = (0.05, 0.05, 0.06)
        glBegin(GL_QUADS)
        glColor3f(*plastic)

        # Front z=+1
        glVertex3f(-1, -1,  1)
        glVertex3f( 1, -1,  1)
        glVertex3f( 1,  1,  1)
        glVertex3f(-1,  1,  1)

        # Back z=-1
        glVertex3f( 1, -1, -1)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1,  1, -1)
        glVertex3f( 1,  1, -1)

        # Left x=-1
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, -1,  1)
        glVertex3f(-1,  1,  1)
        glVertex3f(-1,  1, -1)

        # Right x=+1
        glVertex3f( 1, -1,  1)
        glVertex3f( 1, -1, -1)
        glVertex3f( 1,  1, -1)
        glVertex3f( 1,  1,  1)

        # Up y=+1
        glVertex3f(-1,  1, -1)
        glVertex3f( 1,  1, -1)
        glVertex3f( 1,  1,  1)
        glVertex3f(-1,  1,  1)

        # Down y=-1
        glVertex3f(-1, -1,  1)
        glVertex3f( 1, -1,  1)
        glVertex3f( 1, -1, -1)
        glVertex3f(-1, -1, -1)

        glEnd()

    def _rot_point(self, p, axis, angle_deg):
        x, y, z = p
        a = math.radians(angle_deg)
        c = math.cos(a)
        s = math.sin(a)

        if axis == "x":
            return (x, y*c - z*s, y*s + z*c)
        if axis == "y":
            return (x*c + z*s, y, -x*s + z*c)
        if axis == "z":
            return (x*c - y*s, x*s + y*c, z)
        return p

    def _sticker_center(self, face, r, c):
        if face == "F":
            return (c-1, 1-r, 1)
        if face == "B":
            return (1-c, 1-r, -1)
        if face == "R":
            return (1, 1-r, c-1)
        if face == "L":
            return (-1, 1-r, 1-c)
        if face == "U":
            return (c-1, 1, r-1)
        if face == "D":
            return (c-1, -1, 1-r)
        return (0, 0, 0)

    def _is_in_anim_layer(self, face, r, c):
        if not self.animating:
            return False
        p = self._sticker_center(face, r, c)
        idx = {"x": 0, "y": 1, "z": 2}[self.anim_axis]
        return int(round(p[idx])) == self.anim_layer

    def _sticker_quad(self, face, r, c, margin, offset=None):
        off = self.sticker_offset if offset is None else offset


        step = 2.0 / 3.0
        m = margin

        # Rangos base por cara (mismo criterio que tu render original)
        if face == "F":
            z = 1.0 + off 
            x_min = -1.0 + c * step
            x_max = x_min + step
            y_max = 1.0 - r * step
            y_min = y_max - step
            return [
                (x_min + m, y_min + m, z),
                (x_max - m, y_min + m, z),
                (x_max - m, y_max - m, z),
                (x_min + m, y_max - m, z),
            ]

        if face == "B":
            z = -1.0 - off
            x_max = 1.0 - c * step
            x_min = x_max - step
            y_max = 1.0 - r * step
            y_min = y_max - step
            return [
                (x_min + m, y_min + m, z),
                (x_max - m, y_min + m, z),
                (x_max - m, y_max - m, z),
                (x_min + m, y_max - m, z),
            ]

        if face == "R":
            x = 1.0 + off
            z_min = -1.0 + c * step
            z_max = z_min + step
            y_max = 1.0 - r * step
            y_min = y_max - step
            return [
                (x, y_min + m, z_min + m),
                (x, y_min + m, z_max - m),
                (x, y_max - m, z_max - m),
                (x, y_max - m, z_min + m),
            ]

        if face == "L":
            x = -1.0 - off
            z_max = 1.0 - c * step
            z_min = z_max - step
            y_max = 1.0 - r * step
            y_min = y_max - step
            return [
                (x, y_min + m, z_min + m),
                (x, y_min + m, z_max - m),
                (x, y_max - m, z_max - m),
                (x, y_max - m, z_min + m),
            ]

        if face == "U":
            y = 1.0 + off
            z_min = -1.0 + r * step
            z_max = z_min + step
            x_min = -1.0 + c * step
            x_max = x_min + step
            return [
                (x_min + m, y, z_min + m),
                (x_max - m, y, z_min + m),
                (x_max - m, y, z_max - m),
                (x_min + m, y, z_max - m),
            ]

        if face == "D":
            y = -1.0 - off
            z_max = 1.0 - r * step
            z_min = z_max - step
            x_min = -1.0 + c * step
            x_max = x_min + step
            return [
                (x_min + m, y, z_min + m),
                (x_max - m, y, z_min + m),
                (x_max - m, y, z_max - m),
                (x_min + m, y, z_max - m),
            ]

        return [(0, 0, 0)] * 4

    def _draw_stickers_pass(self, animated_only: bool):
        faces = ["F", "B", "R", "L", "U", "D"]

        glBegin(GL_QUADS)

        for face in faces:
            for r in range(3):
                for c in range(3):
                    in_layer = self._is_in_anim_layer(face, r, c)
                    if animated_only != in_layer:
                        continue

                    # Color sticker
                    color = self.model.state[face][r * 3 + c]
                    rgb = self._color_rgb(color)

                    # Highlight
                    if self.selected and self.selected == (face, r, c):
                        hb = (0.10, 0.95, 0.85)  # calipso
                        hm = self.sticker_margin * 0.35
                        quad_h = self._sticker_quad(face, r, c, hm)
                        if self.animating and in_layer:
                            ang = self.anim_sign * self.anim_angle
                            quad_h = [self._rot_point(v, self.anim_axis, ang) for v in quad_h]
                        glColor3f(*hb)
                        for v in quad_h:
                            glVertex3f(*v)

                    # --- Base "plástico" detrás del sticker (se anima también) ---
                    plastic = (0.05, 0.05, 0.06)

                    # Un poco más grande que el sticker (menos margen) y un poco más atrás (offset menor)
                    quad_bg = self._sticker_quad(face, r, c, margin=0.02, offset=self.sticker_offset * 0.55)

                    if self.animating and in_layer:
                        ang = self.anim_sign * self.anim_angle
                        quad_bg = [self._rot_point(v, self.anim_axis, ang) for v in quad_bg]

                    glColor3f(*plastic)
                    for v in quad_bg:
                        glVertex3f(*v)

                    # Sticker normal
                    quad = self._sticker_quad(face, r, c, self.sticker_margin)
                    if self.animating and in_layer:
                        ang = self.anim_sign * self.anim_angle
                        quad = [self._rot_point(v, self.anim_axis, ang) for v in quad]

                    glColor3f(*rgb)
                    for v in quad:
                        glVertex3f(*v)

        glEnd()

    def _draw_all_stickers_pick(self):
        mapping = {}
        pick_id = 1
        faces = ["F", "B", "R", "L", "U", "D"]

        glBegin(GL_QUADS)

        for face in faces:
            for r in range(3):
                for c in range(3):
                    mapping[pick_id] = (face, r, c)
                    rgb = self._encode_id_color(pick_id)

                    quad = self._sticker_quad(face, r, c, self.sticker_margin + 0.03)  # área pick más centrada

                    glColor3f(*rgb)
                    for v in quad:
                        glVertex3f(*v)

                    pick_id += 1

        glEnd()
        return mapping

    # --------------------------
    # Drag => movimiento (camera-aware)
    # --------------------------
    def _decide_move_from_drag(self, face, r, c, dx, dy):
        def cross(a, b):
            return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

        def dot(a, b):
            return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

        def norm(v):
            return math.sqrt(dot(v, v))

        def scale(v, s):
            return (v[0]*s, v[1]*s, v[2]*s)

        def sub(a, b):
            return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

        def sgn(v):
            return 1 if v > 0 else (-1 if v < 0 else 0)

        FACE_NORMAL = {
            "F": (0, 0, 1),
            "B": (0, 0, -1),
            "R": (1, 0, 0),
            "L": (-1, 0, 0),
            "U": (0, 1, 0),
            "D": (0, -1, 0),
        }

        n = FACE_NORMAL[face]
        p = self._sticker_center(face, r, c)

        # drag en pantalla => mundo
        d_world = (dx, -dy, 0.0)

        # mundo -> cubo (inversa de la cámara)
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)

        cx = math.cos(-pitch); sx = math.sin(-pitch)
        x0, y0, z0 = d_world
        d1 = (x0, cx*y0 - sx*z0, sx*y0 + cx*z0)

        cy = math.cos(-yaw); sy = math.sin(-yaw)
        x1, y1, z1 = d1
        d_cube = (cy*x1 + sy*z1, y1, -sy*x1 + cy*z1)

        # proyectar al plano de la cara
        d_plane = sub(d_cube, scale(n, dot(d_cube, n)))
        if norm(d_plane) < 1e-6:
            return None

        axis = cross(n, d_plane)

        ax = [abs(axis[0]), abs(axis[1]), abs(axis[2])]
        i = ax.index(max(ax))
        axis_pos = "xyz"[i]
        axis_sign = sgn(axis[i])

        layer = int(round(p[i]))

        axis_unit = (axis_sign, 0, 0) if axis_pos == "x" else (0, axis_sign, 0) if axis_pos == "y" else (0, 0, axis_sign)
        v = cross(axis_unit, p)
        rot_about_axis_unit = 1 if dot(v, d_plane) > 0 else -1
        rot_about_pos = rot_about_axis_unit * axis_sign

        # map convención del CubeModel geométrico
        if axis_pos == "y":
            if layer == 1:
                return "U" if rot_about_pos == 1 else "U'"
            if layer == 0:
                return "E'" if rot_about_pos == 1 else "E"
            if layer == -1:
                return "D'" if rot_about_pos == 1 else "D"

        if axis_pos == "x":
            if layer == 1:
                return "R'" if rot_about_pos == 1 else "R"
            if layer == 0:
                return "M" if rot_about_pos == 1 else "M'"
            if layer == -1:
                return "L" if rot_about_pos == 1 else "L'"

        if axis_pos == "z":
            if layer == 1:
                return "F'" if rot_about_pos == 1 else "F"
            if layer == 0:
                return "S'" if rot_about_pos == 1 else "S"
            if layer == -1:
                return "B" if rot_about_pos == 1 else "B'"

        return None

    # --------------------------
    # Color map
    # --------------------------
    def _color_rgb(self, c: str):
        palette = {
            "W": (1.0, 1.0, 1.0),
            "Y": (1.0, 1.0, 0.0),
            "O": (1.0, 0.5, 0.0),
            "R": (1.0, 0.0, 0.0),
            "G": (0.0, 0.85, 0.0),
            "B": (0.0, 0.35, 1.0),
        }
        return palette.get(c, (0.8, 0.8, 0.8))

    
    def cancel_animation(self, clear_queue=True):
        if self.animating:
            self.animating = False
            self._anim_timer.stop()

            self.anim_axis = None
            self.anim_layer = None
            self.anim_sign = 1
            self.anim_angle = 0.0
            self.anim_target = 90.0
            self.anim_move = None

        if clear_queue:
            self._move_queue.clear()

        self.update()


    def play_sequence(self, seq: str):
        tokens = [t.strip() for t in seq.split() if t.strip()]
        if not tokens:
            return
        for t in tokens:
            self.start_move_animation(t)
