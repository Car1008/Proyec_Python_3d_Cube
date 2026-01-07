# main.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rubik 3D Simulator (PySide6)")
        self.resize(1000, 650)

        label = QLabel("Proyecto inicial listo ✅\nSiguiente: CubeModel (core) y tests.")
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
