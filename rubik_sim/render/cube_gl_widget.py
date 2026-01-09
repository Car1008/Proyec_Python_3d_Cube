# rubik_sim/render/cube_gl_widget.py
from __future__ import annotations

import math
from typing import Dict, List, Literal, Optional, Tuple, Union

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import (
    glBegin,
    glClear,
    glClearColor,
    glColor3f,
    glDisable,
    glEnable,
    glEnd,
    glFlush,
    glLoadIdentity,
    glMatrixMode,
    glReadPixels,
    glRotatef,
    glTranslatef,
    glVertex3f,
    glViewport,
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_DITHER,
    GL_MODELVIEW,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGB,
    GL_UNSIGNED_BYTE,
)
from OpenGL.GLU import gluPerspective

from rubik_sim.core.cube_model import CubeModel

Axis = Literal["x", "y", "z"]
Face = Literal["U", "D", "L", "R", "F", "B"]
StickerCoord = Tuple[Face, int, int]  # (cara, fila, columna)
Vec3f = Tuple[float, float, float]


class CubeGLWidget(QOpenGLWidget):
    """Widget OpenGL para renderizar e interactuar con un cubo Rubik 3D.

    Características:
    - Render OpenGL clásico (sin shaders).
    - Stickers 3x3 (y “plástico” detrás).
    - Picking por color (funciona con HiDPI).
    - Highlight del sticker seleccionado.
    - Drag “camera-aware” que decide el movimiento por capa (incluye E/M/S).
    - Animación suave usando QTimer.
    """

    move_applied = Signal(str)

    def __init__(self, model: CubeModel, parent=None) -> None:
        """Crea el widget OpenGL y configura estado inicial (cámara, drag, animación).

        Args:
            model: Modelo lógico del cubo.
            parent: Widget padre (Qt), opcional.
        """
        super().__init__(parent)
        self.model: CubeModel = model

        # Cámara / orbit
        self.yaw: float = 35.0
        self.pitch: float = -20.0
        self.distance: float = 6.0

        self._last_mouse_pos: QPoint = QPoint()
        self._orbiting: bool = False

        # Stickers
        self.sticker_margin: float = 0.04
        self.sticker_offset: float = 0.01

        # Selección
        self.selected: Optional[StickerCoord] = None

        # Drag
        self._dragging_left: bool = False
        self._drag_start: QPoint = QPoint()
        self._drag_hit: Optional[StickerCoord] = None
        self._drag_threshold: int = 14

        # Animación
        self.animating: bool = False
        self.anim_move: Optional[str] = None
        self.anim_axis: Optional[Axis] = None      # 'x','y','z'
        self.anim_layer: Optional[int] = None      # -1,0,1
        self.anim_sign: int = 1                    # +1 o -1
        self.anim_angle: float = 0.0
        self.anim_target: float = 90.0
        self.anim_step: float = 6.0               # deg/frame

        self._move_queue: List[str] = []
        self._anim_timer: QTimer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self.setFocusPolicy(Qt.ClickFocus)

    # --------------------------
    # OpenGL lifecycle
    # --------------------------
    def initializeGL(self) -> None:
        """Inicializa parámetros OpenGL (clear color y depth test)."""
        glClearColor(0.10, 0.10, 0.12, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w: int, h: int) -> None:
        """Ajusta viewport y proyección cuando cambia el tamaño del widget.

        Args:
            w: Ancho lógico del widget (Qt).
            h: Alto lógico del widget (Qt).
        """
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

    def paintGL(self) -> None:
        """Dibuja el frame actual del cubo (stickers + animación)."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._apply_camera()

        # Stickers: primero NO animados, luego animados encima
        self._draw_stickers_pass(animated_only=False)
        if self.animating:
            self._draw_stickers_pass(animated_only=True)

    def _apply_camera(self) -> None:
        """Aplica la transformación de cámara (orbit) al modelo."""
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -self.distance)
        glRotatef(self.pitch, 1.0, 0.0, 0.0)
        glRotatef(self.yaw, 0.0, 1.0, 0.0)

    # --------------------------
    # Interacción
    # --------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Maneja click: botón derecho para orbitar; botón izquierdo para seleccionar/drag.

        Args:
            event: Evento de mouse de Qt.
        """
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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Maneja movimiento del mouse: orbit (derecho) o drag (izquierdo) para mover capas.

        Args:
            event: Evento de mouse de Qt.
        """
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

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finaliza orbit o drag al soltar botones.

        Args:
            event: Evento de mouse de Qt.
        """
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

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom in/out con la rueda del mouse.

        Args:
            event: Evento de rueda de Qt.
        """
        delta = event.angleDelta().y() / 120.0
        self.distance -= delta * 0.3
        self.distance = max(2.5, min(20.0, self.distance))
        self.update()
        event.accept()

    # --------------------------
    # Picking (color picking)
    # --------------------------
    def pick_sticker(self, x: int, y: int) -> Optional[StickerCoord]:
        """Detecta qué sticker se encuentra bajo el cursor usando color picking.

        Args:
            x: Coordenada X en píxeles (Qt, coordenadas del widget).
            y: Coordenada Y en píxeles (Qt, coordenadas del widget).

        Returns:
            Tupla (cara, fila, columna) si se seleccionó un sticker; None si no.
        """
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

    def _encode_id_color(self, pick_id: int) -> Vec3f:
        """Codifica un ID entero a un color RGB (0..1) para picking.

        Args:
            pick_id: Identificador único (1..N) para cada sticker.

        Returns:
            Tupla (r, g, b) normalizada en rango [0, 1].
        """
        r = (pick_id & 0xFF) / 255.0
        g = ((pick_id >> 8) & 0xFF) / 255.0
        b = ((pick_id >> 16) & 0xFF) / 255.0
        return (r, g, b)

    # --------------------------
    # Animación
    # --------------------------
    def _move_to_params(self, move: str) -> Tuple[Axis, int, int]:
        """Traduce un movimiento base a parámetros de animación (eje, capa, signo).

        Args:
            move: Movimiento (por ejemplo: "R", "U'", "M2").

        Returns:
            (axis, layer, sign_base) donde:
            - axis: 'x' | 'y' | 'z'
            - layer: -1 | 0 | 1
            - sign_base: +1 o -1 (convención interna)
        """
        base = move[0].upper()
        table: Dict[str, Tuple[Axis, int, int]] = {
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

    def _parse_move_for_anim(self, move: str) -> Tuple[Axis, int, int, float, str]:
        """Convierte un movimiento a parámetros de animación.

        Args:
            move: Movimiento en notación estándar.

        Returns:
            (axis, layer, sign, target, move)
        """
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

    def start_move_animation(self, move: str) -> None:
        """Inicia la animación de un movimiento o lo encola si ya hay una animación activa.

        Args:
            move: Movimiento a animar.
        """
        if self.animating:
            self._move_queue.append(move)
            return

        (
            self.anim_axis,
            self.anim_layer,
            self.anim_sign,
            self.anim_target,
            self.anim_move,
        ) = self._parse_move_for_anim(move)

        self.anim_angle = 0.0
        self.animating = True
        self._anim_timer.start()

    def _on_anim_tick(self) -> None:
        """Tick del timer: avanza la animación hasta completar el ángulo objetivo."""
        if not self.animating:
            self._anim_timer.stop()
            return

        self.anim_angle += self.anim_step
        if self.anim_angle >= self.anim_target:
            self.anim_angle = self.anim_target
            self._finish_move_animation()
            return

        self.update()

    def _finish_move_animation(self) -> None:
        """Finaliza la animación: aplica el movimiento al modelo y emite la señal."""
        move = self.anim_move
        if move is None:
            # Estado inesperado: protegemos para evitar crash.
            self.animating = False
            self._anim_timer.stop()
            return

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
    def _rot_point(self, p: Vec3f, axis: Axis, angle_deg: float) -> Vec3f:
        """Rota un punto alrededor de un eje por un ángulo en grados.

        Args:
            p: Punto (x, y, z).
            axis: Eje de rotación ('x', 'y', 'z').
            angle_deg: Ángulo en grados.

        Returns:
            Punto rotado (x, y, z).
        """
        x, y, z = p
        a = math.radians(angle_deg)
        c = math.cos(a)
        s = math.sin(a)

        if axis == "x":
            return (x, y * c - z * s, y * s + z * c)
        if axis == "y":
            return (x * c + z * s, y, -x * s + z * c)
        if axis == "z":
            return (x * c - y * s, x * s + y * c, z)
        return p

    def _sticker_center(self, face: Face, r: int, c: int) -> Vec3f:
        """Centro geométrico de un sticker en una cara (coherente con CubeModel).

        Args:
            face: Cara ("F","B","R","L","U","D").
            r: Fila 0..2.
            c: Columna 0..2.

        Returns:
            Coordenada (x, y, z) del centro del sticker.
        """
        if face == "F":
            return (c - 1, 1 - r, 1)
        if face == "B":
            return (1 - c, 1 - r, -1)
        if face == "R":
            return (1, 1 - r, c - 1)
        if face == "L":
            return (-1, 1 - r, 1 - c)
        if face == "U":
            return (c - 1, 1, r - 1)
        if face == "D":
            return (c - 1, -1, 1 - r)
        return (0.0, 0.0, 0.0)

    def _is_in_anim_layer(self, face: Face, r: int, c: int) -> bool:
        """Indica si un sticker pertenece a la capa animada actual."""
        if not self.animating or self.anim_axis is None or self.anim_layer is None:
            return False
        p = self._sticker_center(face, r, c)
        idx = {"x": 0, "y": 1, "z": 2}[self.anim_axis]
        return int(round(p[idx])) == self.anim_layer

    def _sticker_quad(
        self,
        face: Face,
        r: int,
        c: int,
        margin: float,
        offset: Optional[float] = None,
    ) -> List[Vec3f]:
        """Retorna los 4 vértices del quad (sticker) para una cara y celda (r,c).

        Args:
            face: Cara.
            r: Fila 0..2.
            c: Columna 0..2.
            margin: Margen interno del sticker (reduce el quad).
            offset: Offset respecto al cubo (si None, usa `self.sticker_offset`).

        Returns:
            Lista de 4 vértices (x, y, z) en orden para dibujar con GL_QUADS.
        """
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

        return [(0.0, 0.0, 0.0)] * 4

    def _draw_stickers_pass(self, animated_only: bool) -> None:
        """Dibuja stickers (y fondo plástico) en un pase.

        Args:
            animated_only: Si True, dibuja solo los stickers de la capa animada.
                Si False, dibuja los que NO están en la capa animada.
        """
        faces: List[Face] = ["F", "B", "R", "L", "U", "D"]

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
                        if self.animating and in_layer and self.anim_axis is not None:
                            ang = self.anim_sign * self.anim_angle
                            quad_h = [self._rot_point(v, self.anim_axis, ang) for v in quad_h]
                        glColor3f(*hb)
                        for v in quad_h:
                            glVertex3f(*v)

                    # --- Base "plástico" detrás del sticker (se anima también) ---
                    plastic = (0.05, 0.05, 0.06)

                    # Un poco más grande que el sticker y un poco más atrás
                    quad_bg = self._sticker_quad(
                        face,
                        r,
                        c,
                        margin=0.02,
                        offset=self.sticker_offset * 0.55,
                    )

                    if self.animating and in_layer and self.anim_axis is not None:
                        ang = self.anim_sign * self.anim_angle
                        quad_bg = [self._rot_point(v, self.anim_axis, ang) for v in quad_bg]

                    glColor3f(*plastic)
                    for v in quad_bg:
                        glVertex3f(*v)

                    # Sticker normal
                    quad = self._sticker_quad(face, r, c, self.sticker_margin)
                    if self.animating and in_layer and self.anim_axis is not None:
                        ang = self.anim_sign * self.anim_angle
                        quad = [self._rot_point(v, self.anim_axis, ang) for v in quad]

                    glColor3f(*rgb)
                    for v in quad:
                        glVertex3f(*v)

        glEnd()

    def _draw_all_stickers_pick(self) -> Dict[int, StickerCoord]:
        """Dibuja todos los stickers con colores codificados y retorna el mapa ID->sticker.

        Returns:
            Diccionario {pick_id: (face, r, c)}.
        """
        mapping: Dict[int, StickerCoord] = {}
        pick_id = 1
        faces: List[Face] = ["F", "B", "R", "L", "U", "D"]

        glBegin(GL_QUADS)

        for face in faces:
            for r in range(3):
                for c in range(3):
                    mapping[pick_id] = (face, r, c)
                    rgb = self._encode_id_color(pick_id)

                    quad = self._sticker_quad(
                        face, r, c, self.sticker_margin + 0.03
                    )  # área pick un poco más grande

                    glColor3f(*rgb)
                    for v in quad:
                        glVertex3f(*v)

                    pick_id += 1

        glEnd()
        return mapping

    # --------------------------
    # Drag => movimiento (camera-aware)
    # --------------------------
    def _decide_move_from_drag(
        self,
        face: Face,
        r: int,
        c: int,
        dx: float,
        dy: float,
    ) -> Optional[str]:
        """Decide un movimiento a partir de un drag sobre un sticker, considerando la cámara.

        Args:
            face: Cara donde empezó el drag.
            r: Fila del sticker.
            c: Columna del sticker.
            dx: Delta X del drag en pantalla.
            dy: Delta Y del drag en pantalla.

        Returns:
            Movimiento en notación (ej: "U", "R'", "E", etc.) o None si no se puede decidir.
        """

        def cross(a: Vec3f, b: Vec3f) -> Vec3f:
            return (
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            )

        def dot(a: Vec3f, b: Vec3f) -> float:
            return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

        def norm(v: Vec3f) -> float:
            return math.sqrt(dot(v, v))

        def scale(v: Vec3f, s: float) -> Vec3f:
            return (v[0] * s, v[1] * s, v[2] * s)

        def sub(a: Vec3f, b: Vec3f) -> Vec3f:
            return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

        def sgn(v: float) -> int:
            return 1 if v > 0 else (-1 if v < 0 else 0)

        FACE_NORMAL: Dict[Face, Vec3f] = {
            "F": (0.0, 0.0, 1.0),
            "B": (0.0, 0.0, -1.0),
            "R": (1.0, 0.0, 0.0),
            "L": (-1.0, 0.0, 0.0),
            "U": (0.0, 1.0, 0.0),
            "D": (0.0, -1.0, 0.0),
        }

        n = FACE_NORMAL[face]
        p = self._sticker_center(face, r, c)

        # drag en pantalla => mundo
        d_world: Vec3f = (dx, -dy, 0.0)

        # mundo -> cubo (inversa de la cámara)
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)

        cx = math.cos(-pitch)
        sx = math.sin(-pitch)
        x0, y0, z0 = d_world
        d1: Vec3f = (x0, cx * y0 - sx * z0, sx * y0 + cx * z0)

        cy = math.cos(-yaw)
        sy = math.sin(-yaw)
        x1, y1, z1 = d1
        d_cube: Vec3f = (cy * x1 + sy * z1, y1, -sy * x1 + cy * z1)

        # proyectar al plano de la cara
        d_plane = sub(d_cube, scale(n, dot(d_cube, n)))
        if norm(d_plane) < 1e-6:
            return None

        axis = cross(n, d_plane)

        ax = [abs(axis[0]), abs(axis[1]), abs(axis[2])]
        i = ax.index(max(ax))
        axis_pos: Axis = "xyz"[i]  # type: ignore[assignment]
        axis_sign = sgn(axis[i])

        layer = int(round(p[i]))

        axis_unit: Vec3f = (
            (float(axis_sign), 0.0, 0.0)
            if axis_pos == "x"
            else (0.0, float(axis_sign), 0.0)
            if axis_pos == "y"
            else (0.0, 0.0, float(axis_sign))
        )
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
    def _color_rgb(self, c: str) -> Vec3f:
        """Convierte el símbolo de color del modelo a RGB.

        Args:
            c: Letra de color (por ejemplo: "W", "Y", "O", "R", "G", "B").

        Returns:
            Tupla (r, g, b) en rango [0, 1]. Si no existe el color, retorna gris.
        """
        palette: Dict[str, Vec3f] = {
            "W": (1.0, 1.0, 1.0),
            "Y": (1.0, 1.0, 0.0),
            "O": (1.0, 0.5, 0.0),
            "R": (1.0, 0.0, 0.0),
            "G": (0.0, 0.85, 0.0),
            "B": (0.0, 0.35, 1.0),
        }
        return palette.get(c, (0.8, 0.8, 0.8))

    def cancel_animation(self, clear_queue: bool = True) -> None:
        """Cancela la animación actual y opcionalmente limpia la cola.

        Args:
            clear_queue: Si True, también borra la cola de movimientos pendientes.
        """
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

    def play_sequence(self, seq: str) -> None:
        """Encola (y ejecuta con animación) una secuencia de movimientos separada por espacios.

        Args:
            seq: Secuencia tipo "R U R' U'".
        """
        tokens = [t.strip() for t in seq.split() if t.strip()]
        if not tokens:
            return
        for t in tokens:
            self.start_move_animation(t)
