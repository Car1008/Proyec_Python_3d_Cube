# main.py
import sys
from PySide6.QtWidgets import QApplication
from rubik_sim.app.main_window import MainWindow

# Activar entorno virutual
# .\.venv\Scripts\Activate.ps1
# instalcion de dependencias (estar en la raiz del proyecto)
# python -m pip install --upgrade pip
# python -m pip install -r requirements.txt


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
