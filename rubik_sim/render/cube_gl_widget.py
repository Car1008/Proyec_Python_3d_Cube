# rubik_sim/render/cube_gl_widget.py
from PySide6.QtCore import Qt, QPoint
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import (
    glClearColor, glClear, glEnable, glViewport,
    glBegin, glEnd, glColor3f, glVertex3f,
    glMatrixMode, glLoadIdentity, glRotatef, glTranslatef,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST,
    GL_PROJECTION, GL_MODELVIEW, GL_QUADS
)
from OpenGL.GLU import gluPerspective


class CubeGLWidget(QOpenGLWidget):
    """
    Render 3D con OpenGL clásico.
    - Dibuja cubo plástico oscuro + stickers 3x3 por cara
    - Colores vienen desde CubeModel.state (U,D,L,R,F,B)
    - Orbit: click derecho + arrastrar
    - Zoom: rueda
    """

    def __init__(self, model, parent=None):
        super().__init__(parent)

        self.model = model  # CubeModel

        # Cámara / orbit
        self.yaw = 35.0
        self.pitch = -20.0
        self.distance = 6.0

        self._last_mouse_pos = QPoint()
        self._orbiting = False

        self.setFocusPolicy(Qt.ClickFocus)

        # Tamaño de sticker y separación (margen dentro de cada celda)
        self.sticker_margin = 0.06      # en unidades del cubo (se ve como “líneas negras”)
        self.sticker_offset = 0.01      # levanta stickers para evitar z-fighting

    # --------------------------
    # OpenGL lifecycle
    # --------------------------
    def initializeGL(self):
        glClearColor(0.10, 0.10, 0.12, 1.0)
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        if h == 0:
            h = 1
        glViewport(0, 0, w, h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / float(h)
        gluPerspective(45.0, aspect, 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Cámara
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -self.distance)
        glRotatef(self.pitch, 1.0, 0.0, 0.0)
        glRotatef(self.yaw, 0.0, 1.0, 0.0)

        # 1) Cubo plástico base
        self._draw_plastic_cube()

        # 2) Stickers 3x3 por cara (desde CubeModel)
        self._draw_all_stickers()

    # --------------------------
    # Interacción (orbit)
    # --------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._orbiting = True
            self._last_mouse_pos = event.pos()
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
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton and self._orbiting:
            self._orbiting = False
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
    # Dibujos
    # --------------------------
    def _draw_plastic_cube(self):
        """
        Dibuja el cubo base oscuro (plástico).
        """
        plastic = (0.05, 0.05, 0.06)  # gris oscuro
        glBegin(GL_QUADS)

        # Front z=+1
        glColor3f(*plastic)
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

    def _draw_all_stickers(self):
        """
        Dibuja stickers 3x3 para U, D, L, R, F, B usando self.model.state.
        """
        # Paso de celda en coordenadas [-1,1] => 2/3
        step = 2.0 / 3.0
        m = self.sticker_margin

        # Helper para dibujar un sticker en un quad
        def draw_quad(v0, v1, v2, v3, rgb):
            glColor3f(*rgb)
            glVertex3f(*v0)
            glVertex3f(*v1)
            glVertex3f(*v2)
            glVertex3f(*v3)

        glBegin(GL_QUADS)

        # -------- FRONT (F) : z = +1 + offset
        z = 1.0 + self.sticker_offset
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                x_min = -1.0 + c * step
                x_max = x_min + step

                color = self.model.state["F"][r * 3 + c]
                rgb = self._color_rgb(color)

                v0 = (x_min + m, y_min + m, z)
                v1 = (x_max - m, y_min + m, z)
                v2 = (x_max - m, y_max - m, z)
                v3 = (x_min + m, y_max - m, z)
                draw_quad(v0, v1, v2, v3, rgb)

        # -------- BACK (B) : z = -1 - offset (invertimos columnas)
        z = -1.0 - self.sticker_offset
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                # flip en x para que el "lado izquierdo" del B al mirarlo desde fuera sea correcto
                x_max = 1.0 - c * step
                x_min = x_max - step

                color = self.model.state["B"][r * 3 + c]
                rgb = self._color_rgb(color)

                v0 = (x_min + m, y_min + m, z)
                v1 = (x_max - m, y_min + m, z)
                v2 = (x_max - m, y_max - m, z)
                v3 = (x_min + m, y_max - m, z)
                draw_quad(v0, v1, v2, v3, rgb)

        # -------- RIGHT (R) : x = +1 + offset (col -> z)
        x = 1.0 + self.sticker_offset
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                z_min = -1.0 + c * step
                z_max = z_min + step

                color = self.model.state["R"][r * 3 + c]
                rgb = self._color_rgb(color)

                v0 = (x, y_min + m, z_min + m)
                v1 = (x, y_min + m, z_max - m)
                v2 = (x, y_max - m, z_max - m)
                v3 = (x, y_max - m, z_min + m)
                draw_quad(v0, v1, v2, v3, rgb)

        # -------- LEFT (L) : x = -1 - offset (col -> z invertida)
        x = -1.0 - self.sticker_offset
        for r in range(3):
            y_max = 1.0 - r * step
            y_min = y_max - step
            for c in range(3):
                # flip z para mantener orientación al mirar desde fuera
                z_max = 1.0 - c * step
                z_min = z_max - step

                color = self.model.state["L"][r * 3 + c]
                rgb = self._color_rgb(color)

                v0 = (x, y_min + m, z_min + m)
                v1 = (x, y_min + m, z_max - m)
                v2 = (x, y_max - m, z_max - m)
                v3 = (x, y_max - m, z_min + m)
                draw_quad(v0, v1, v2, v3, rgb)

        # -------- UP (U) : y = +1 + offset (row -> z)
        y = 1.0 + self.sticker_offset
        for r in range(3):
            z_min = -1.0 + r * step
            z_max = z_min + step
            for c in range(3):
                x_min = -1.0 + c * step
                x_max = x_min + step

                color = self.model.state["U"][r * 3 + c]
                rgb = self._color_rgb(color)

                v0 = (x_min + m, y, z_min + m)
                v1 = (x_max - m, y, z_min + m)
                v2 = (x_max - m, y, z_max - m)
                v3 = (x_min + m, y, z_max - m)
                draw_quad(v0, v1, v2, v3, rgb)

        # -------- DOWN (D) : y = -1 - offset (row -> z invertida)
        y = -1.0 - self.sticker_offset
        for r in range(3):
            # flip z para orientación del D al mirarlo desde abajo
            z_max = 1.0 - r * step
            z_min = z_max - step
            for c in range(3):
                x_min = -1.0 + c * step
                x_max = x_min + step

                color = self.model.state["D"][r * 3 + c]
                rgb = self._color_rgb(color)

                v0 = (x_min + m, y, z_min + m)
                v1 = (x_max - m, y, z_min + m)
                v2 = (x_max - m, y, z_max - m)
                v3 = (x_min + m, y, z_max - m)
                draw_quad(v0, v1, v2, v3, rgb)

        glEnd()

    def _color_rgb(self, c: str):
        """
        Mapea los colores del CubeModel a RGB.
        """
        palette = {
            "W": (1.0, 1.0, 1.0),   # White
            "Y": (1.0, 1.0, 0.0),   # Yellow
            "O": (1.0, 0.5, 0.0),   # Orange
            "R": (1.0, 0.0, 0.0),   # Red
            "G": (0.0, 0.85, 0.0),  # Green
            "B": (0.0, 0.35, 1.0),  # Blue
        }
        return palette.get(c, (0.8, 0.8, 0.8))  # gris si aparece algo raro
