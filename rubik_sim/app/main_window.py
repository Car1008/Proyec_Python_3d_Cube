# rubik_sim/app/main_window.py
from PySide6.QtWidgets import QMainWindow
from rubik_sim.render.cube_gl_widget import CubeGLWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rubik 3D Simulator (PySide6)")
        self.resize(1100, 750)

        self.gl_widget = CubeGLWidget(self)
        self.setCentralWidget(self.gl_widget)
