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
    Render 3D base con OpenGL clásico (sin shaders).
    - Dibuja un cubo coloreado por caras
    - Orbit: click derecho + arrastrar
    - Zoom: rueda
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Cámara / orbit
        self.yaw = 35.0
        self.pitch = -20.0
        self.distance = 6.0

        self._last_mouse_pos = QPoint()
        self._orbiting = False

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
        glViewport(0, 0, w, h)

        # Configurar proyección
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

        # Dibujar cubo (lado 2)
        self._draw_colored_cube()

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
    # Geometría
    # --------------------------
    def _draw_colored_cube(self):
        # Colores RGB por cara (U,D,L,R,F,B)
        colors = {
            "U": (1.0, 1.0, 1.0),   # White
            "D": (1.0, 1.0, 0.0),   # Yellow
            "L": (1.0, 0.5, 0.0),   # Orange
            "R": (1.0, 0.0, 0.0),   # Red
            "F": (0.0, 0.8, 0.0),   # Green
            "B": (0.0, 0.3, 1.0),   # Blue
        }

        # Dibujamos 6 quads
        glBegin(GL_QUADS)

        # Front (z=+1)
        glColor3f(*colors["F"])
        glVertex3f(-1, -1,  1)
        glVertex3f( 1, -1,  1)
        glVertex3f( 1,  1,  1)
        glVertex3f(-1,  1,  1)

        # Back (z=-1)
        glColor3f(*colors["B"])
        glVertex3f( 1, -1, -1)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1,  1, -1)
        glVertex3f( 1,  1, -1)

        # Left (x=-1)
        glColor3f(*colors["L"])
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, -1,  1)
        glVertex3f(-1,  1,  1)
        glVertex3f(-1,  1, -1)

        # Right (x=+1)
        glColor3f(*colors["R"])
        glVertex3f( 1, -1,  1)
        glVertex3f( 1, -1, -1)
        glVertex3f( 1,  1, -1)
        glVertex3f( 1,  1,  1)

        # Up (y=+1)
        glColor3f(*colors["U"])
        glVertex3f(-1,  1, -1)
        glVertex3f( 1,  1, -1)
        glVertex3f( 1,  1,  1)
        glVertex3f(-1,  1,  1)

        # Down (y=-1)
        glColor3f(*colors["D"])
        glVertex3f(-1, -1,  1)
        glVertex3f( 1, -1,  1)
        glVertex3f( 1, -1, -1)
        glVertex3f(-1, -1, -1)

        glEnd()
