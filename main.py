# main.py
from __future__ import annotations

import sys
from typing import NoReturn

from PySide6.QtWidgets import QApplication

from rubik_sim.app.main_window import MainWindow


def main() -> NoReturn:
    """Punto de entrada de la aplicación.

    Crea la instancia de `QApplication`, construye la ventana principal
    (`MainWindow`) y ejecuta el loop de eventos de Qt.

    Returns:
        No retorna (finaliza el proceso con `sys.exit`).
    """
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
