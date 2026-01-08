# rubik_sim/render/cube_gl_widget.py
from PySide6.QtCore import Qt, QPoint
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

# selecionar el color de highlight
#hb = (1.0, 1.0, 0.2)  # amarillo suave
hb = (0.10, 0.95, 0.85)  # calipso / turquesa



class CubeGLWidget(QOpenGLWidget):
    """
    Render 3D (OpenGL clásico) + stickers 3x3 + picking por color.
    - Left click: selecciona sticker (cara, fila, columna)
    - Right drag: orbit
    - Wheel: zoom
    """

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
        self.sticker_margin = 0.06
        self.sticker_offset = 0.01

        # Selección (face, r, c)
        self.selected = None
        
        self._dragging_left = False
        self._drag_start = QPoint()
        self._drag_hit = None  # (face, r, c)
        self._drag_threshold = 10  # pixeles

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

        # Cámara
        self._apply_camera()

        # 1) Cubo plástico base
        self._draw_plastic_cube()

        # 2) Stickers desde el modelo (con highlight si hay selección)
        self._draw_all_stickers(highlight=self.selected)

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
                msg = "Sin selección (clic fuera de stickers)."

            w = self.window()
            if hasattr(w, "statusBar") and w.statusBar():
                w.statusBar().showMessage(msg, 2000)
            else:
                print(msg)

            self.update()
            event.accept()
            return


            # Mostrar en status bar si existe
            w = self.window()
            if hasattr(w, "statusBar") and w.statusBar():
                w.statusBar().showMessage(msg, 3000)
            else:
                print(msg)

            self.update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
        # Drag izquierdo: aplicar un movimiento cuando supere umbral
        if self._dragging_left and (event.buttons() & Qt.LeftButton):
            if not self._drag_hit:
                return

            dx = event.position().x() - self._drag_start.x()
            dy = event.position().y() - self._drag_start.y()

            if abs(dx) < self._drag_threshold and abs(dy) < self._drag_threshold:
                return

            face, r, c = self._drag_hit
            move = self._decide_move_from_drag(face, r, c, dx, dy)


            if move:
                self.model.apply_move(move)
                self.update()

                # feedback
                w = self.window()
                if hasattr(w, "statusBar") and w.statusBar():
                    w.statusBar().showMessage(f"Move: {move}", 1500)
                else:
                    print("Move:", move)

            # terminar drag (un movimiento por drag)
            self._dragging_left = False
            self._drag_hit = None
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self._orbiting:
            self._orbiting = False
            event.accept()
            
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
        dpr = self.devicePixelRatioF()

        # coords en framebuffer real
        gl_x = int(x * dpr)
        gl_y = int((self.height() - y - 1) * dpr)

        self.makeCurrent()

        # (opcional) desactivar multisample si existe
        try:
            from OpenGL.GL import glDisable, GL_MULTISAMPLE
            glDisable(GL_MULTISAMPLE)
        except Exception:
            pass

        glDisable(GL_DITHER)
        glDisable(GL_BLEND)

        # Render pass picking
        glClearColor(0.0, 0.0, 0.0, 1.0)  # id=0 fondo
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._apply_camera()
        mapping = self._draw_all_stickers_pick()

        glFlush()

        pixel = glReadPixels(gl_x, gl_y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)

        # pixel puede venir como bytes o array
        if pixel is None:
            return None

        if isinstance(pixel, (bytes, bytearray)):
            r, g, b = pixel[0], pixel[1], pixel[2]
        else:
            # a veces retorna array-like
            try:
                r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
            except Exception:
                return None

        pick_id = r + (g << 8) + (b << 16)
        return mapping.get(pick_id, None)


    def _encode_id_color(self, pick_id: int):
        """
        Convierte un ID (1..54) a un color RGB (0..1) para picking.
        """
        r = (pick_id & 0xFF) / 255.0
        g = ((pick_id >> 8) & 0xFF) / 255.0
        b = ((pick_id >> 16) & 0xFF) / 255.0
        return (r, g, b)

    # --------------------------
    # Dibujos
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

    def _draw_all_stickers(self, highlight=None):
        """
        Dibuja stickers con colores del modelo.
        highlight: (face, r, c) o None
        """
        step = 2.0 / 3.0
        m = self.sticker_margin

        def draw_quad(v0, v1, v2, v3, rgb):
            glColor3f(*rgb)
            glVertex3f(*v0)
            glVertex3f(*v1)
            glVertex3f(*v2)
            glVertex3f(*v3)

        glBegin(GL_QUADS)

        # FRONT (F)
        z = 1.0 + self.sticker_offset
        self._draw_face_stickers("F", z, step, m, draw_quad, highlight)

        # BACK (B)
        z = -1.0 - self.sticker_offset
        self._draw_face_stickers("B", z, step, m, draw_quad, highlight)

        # RIGHT (R)
        x = 1.0 + self.sticker_offset
        self._draw_side_face_stickers("R", x, step, m, draw_quad, highlight)

        # LEFT (L)
        x = -1.0 - self.sticker_offset
        self._draw_side_face_stickers("L", x, step, m, draw_quad, highlight)

        # UP (U)
        y = 1.0 + self.sticker_offset
        self._draw_up_down_face_stickers("U", y, step, m, draw_quad, highlight)

        # DOWN (D)
        y = -1.0 - self.sticker_offset
        self._draw_up_down_face_stickers("D", y, step, m, draw_quad, highlight)

        glEnd()

    def _draw_all_stickers_pick(self):
        """
        Dibuja stickers pero con color único por sticker.
        Retorna dict: pick_id -> (face, r, c)
        """
        step = 2.0 / 3.0
        m = self.sticker_margin + 0.03

        mapping = {}
        pick_id = 1

        def draw_quad(v0, v1, v2, v3, rgb):
            glColor3f(*rgb)
            glVertex3f(*v0)
            glVertex3f(*v1)
            glVertex3f(*v2)
            glVertex3f(*v3)

        glBegin(GL_QUADS)

        # F
        z = 1.0 + self.sticker_offset
        pick_id = self._draw_face_pick("F", z, step, m, draw_quad, mapping, pick_id)

        # B
        z = -1.0 - self.sticker_offset
        pick_id = self._draw_face_pick("B", z, step, m, draw_quad, mapping, pick_id)

        # R
        x = 1.0 + self.sticker_offset
        pick_id = self._draw_side_face_pick("R", x, step, m, draw_quad, mapping, pick_id)

        # L
        x = -1.0 - self.sticker_offset
        pick_id = self._draw_side_face_pick("L", x, step, m, draw_quad, mapping, pick_id)

        # U
        y = 1.0 + self.sticker_offset
        pick_id = self._draw_up_down_face_pick("U", y, step, m, draw_quad, mapping, pick_id)

        # D
        y = -1.0 - self.sticker_offset
        pick_id = self._draw_up_down_face_pick("D", y, step, m, draw_quad, mapping, pick_id)

        glEnd()

        return mapping

    # ---------- helpers dibujo caras ----------
    def _draw_face_stickers(self, face, z, step, m, draw_quad, highlight):
        # F normal; B con flip X (como ya tenías)
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                if face == "B":
                    x_max = 1.0 - c * step
                    x_min = x_max - step
                else:
                    x_min = -1.0 + c * step
                    x_max = x_min + step

                color = self.model.state[face][r * 3 + c]
                rgb = self._color_rgb(color)

                # highlight: dibuja un “marco” (quad más grande) antes del sticker
                if highlight and highlight == (face, r, c):
                    

                    hm = m * 0.35
                    v0 = (x_min + hm, y_min + hm, z)
                    v1 = (x_max - hm, y_min + hm, z)
                    v2 = (x_max - hm, y_max - hm, z)
                    v3 = (x_min + hm, y_max - hm, z)
                    draw_quad(v0, v1, v2, v3, hb)

                v0 = (x_min + m, y_min + m, z)
                v1 = (x_max - m, y_min + m, z)
                v2 = (x_max - m, y_max - m, z)
                v3 = (x_min + m, y_max - m, z)
                draw_quad(v0, v1, v2, v3, rgb)

    def _draw_side_face_stickers(self, face, x, step, m, draw_quad, highlight):
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                if face == "L":
                    z_max = 1.0 - c * step
                    z_min = z_max - step
                else:
                    z_min = -1.0 + c * step
                    z_max = z_min + step

                color = self.model.state[face][r * 3 + c]
                rgb = self._color_rgb(color)

                if highlight and highlight == (face, r, c):
                    hm = m * 0.35
                    v0 = (x, y_min + hm, z_min + hm)
                    v1 = (x, y_min + hm, z_max - hm)
                    v2 = (x, y_max - hm, z_max - hm)
                    v3 = (x, y_max - hm, z_min + hm)
                    draw_quad(v0, v1, v2, v3, hb)

                v0 = (x, y_min + m, z_min + m)
                v1 = (x, y_min + m, z_max - m)
                v2 = (x, y_max - m, z_max - m)
                v3 = (x, y_max - m, z_min + m)
                draw_quad(v0, v1, v2, v3, rgb)

    def _draw_up_down_face_stickers(self, face, y, step, m, draw_quad, highlight):
        for r in range(3):
            if face == "D":
                z_max = 1.0 - r * step
                z_min = z_max - step
            else:
                z_min = -1.0 + r * step
                z_max = z_min + step

            for c in range(3):
                x_min = -1.0 + c * step
                x_max = x_min + step

                color = self.model.state[face][r * 3 + c]
                rgb = self._color_rgb(color)

                if highlight and highlight == (face, r, c):
                    hm = m * 0.35
                    v0 = (x_min + hm, y, z_min + hm)
                    v1 = (x_max - hm, y, z_min + hm)
                    v2 = (x_max - hm, y, z_max - hm)
                    v3 = (x_min + hm, y, z_max - hm)
                    draw_quad(v0, v1, v2, v3, hb)

                v0 = (x_min + m, y, z_min + m)
                v1 = (x_max - m, y, z_min + m)
                v2 = (x_max - m, y, z_max - m)
                v3 = (x_min + m, y, z_max - m)
                draw_quad(v0, v1, v2, v3, rgb)

    # ---------- helpers picking ----------
    def _draw_face_pick(self, face, z, step, m, draw_quad, mapping, pick_id):
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                if face == "B":
                    x_max = 1.0 - c * step
                    x_min = x_max - step
                else:
                    x_min = -1.0 + c * step
                    x_max = x_min + step

                mapping[pick_id] = (face, r, c)
                rgb = self._encode_id_color(pick_id)

                v0 = (x_min + m, y_min + m, z)
                v1 = (x_max - m, y_min + m, z)
                v2 = (x_max - m, y_max - m, z)
                v3 = (x_min + m, y_max - m, z)
                draw_quad(v0, v1, v2, v3, rgb)
                pick_id += 1
        return pick_id

    def _draw_side_face_pick(self, face, x, step, m, draw_quad, mapping, pick_id):
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                if face == "L":
                    z_max = 1.0 - c * step
                    z_min = z_max - step
                else:
                    z_min = -1.0 + c * step
                    z_max = z_min + step

                mapping[pick_id] = (face, r, c)
                rgb = self._encode_id_color(pick_id)

                v0 = (x, y_min + m, z_min + m)
                v1 = (x, y_min + m, z_max - m)
                v2 = (x, y_max - m, z_max - m)
                v3 = (x, y_max - m, z_min + m)
                draw_quad(v0, v1, v2, v3, rgb)
                pick_id += 1
        return pick_id

    def _draw_up_down_face_pick(self, face, y, step, m, draw_quad, mapping, pick_id):
        for r in range(3):
            if face == "D":
                z_max = 1.0 - r * step
                z_min = z_max - step
            else:
                z_min = -1.0 + r * step
                z_max = z_min + step

            for c in range(3):
                x_min = -1.0 + c * step
                x_max = x_min + step

                mapping[pick_id] = (face, r, c)
                rgb = self._encode_id_color(pick_id)

                v0 = (x_min + m, y, z_min + m)
                v1 = (x_max - m, y, z_min + m)
                v2 = (x_max - m, y, z_max - m)
                v3 = (x_min + m, y, z_max - m)
                draw_quad(v0, v1, v2, v3, rgb)
                pick_id += 1
        return pick_id

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
    
    def _decide_move_from_drag(self, face, r, c, dx, dy):
        # vectores base por cara (coinciden con cómo dibujas r/c)
        basis = {
            "F": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
            "B": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
            "R": ((1, 0, 0), (0, 0, 1), (0, 1, 0)),
            "L": ((-1, 0, 0), (0, 0, -1), (0, 1, 0)),
            "U": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
            "D": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
        }

        def cross(a, b):
            return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

        def dot(a, b):
            return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

        def sgn(v):
            return 1 if v > 0 else (-1 if v < 0 else 0)

        # centro discreto del sticker en coords de cubo (x,y,z en {-1,0,1})
        def sticker_center(face, r, c):
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

        n, a, b = basis[face]
        p = sticker_center(face, r, c)

        horizontal = abs(dx) >= abs(dy)

        # drag direction en plano de la cara (en coords de cubo)
        if horizontal:
            d = a if dx > 0 else (-a[0], -a[1], -a[2])
        else:
            # dy>0 es “hacia abajo” en pantalla => -b
            d = (-b[0], -b[1], -b[2]) if dy > 0 else b

        axis = cross(n, d)  # eje de giro (±x, ±y, ±z)

        # elegir eje dominante
        ax = [abs(axis[0]), abs(axis[1]), abs(axis[2])]
        i = ax.index(max(ax))
        axis_pos = "xyz"[i]
        axis_sign = sgn(axis[i])

        # layer: -1,0,1 según coordenada del sticker en ese eje
        layer = int(round(p[i]))

        # dirección de giro: probamos +90 sobre el eje real (con signo) usando v = w x p
        axis_unit = (0, 0, 0)
        axis_unit = (axis_sign, 0, 0) if axis_pos == "x" else axis_unit
        axis_unit = (0, axis_sign, 0) if axis_pos == "y" else axis_unit
        axis_unit = (0, 0, axis_sign) if axis_pos == "z" else axis_unit

        v = cross(axis_unit, p)
        rot_about_axis_unit = 1 if dot(v, d) > 0 else -1

        # convertir a rotación sobre eje POSITIVO (x,y,z)
        rot_about_pos = rot_about_axis_unit * axis_sign

        # mapear (axis_pos, layer, rot_about_pos) -> movimiento
        if axis_pos == "y":
            if layer == 1:   # U
                return "U" if rot_about_pos == 1 else "U'"
            if layer == 0:   # E (E es -90)
                return "E'" if rot_about_pos == 1 else "E"
            if layer == -1:  # D (D es -90)
                return "D'" if rot_about_pos == 1 else "D"

        if axis_pos == "x":
            if layer == 1:   # R (R es -90)
                return "R'" if rot_about_pos == 1 else "R"
            if layer == 0:   # M (M es +90)
                return "M" if rot_about_pos == 1 else "M'"
            if layer == -1:  # L (L es +90)
                return "L" if rot_about_pos == 1 else "L'"

        if axis_pos == "z":
            if layer == 1:   # F (F es -90)
                return "F'" if rot_about_pos == 1 else "F"
            if layer == 0:   # S (S es -90)
                return "S'" if rot_about_pos == 1 else "S"
            if layer == -1:  # B (B es +90)
                return "B" if rot_about_pos == 1 else "B'"

        return None


