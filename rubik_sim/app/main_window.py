# rubik_sim/app/main_window.py
from __future__ import annotations

from typing import Optional, Literal, Sequence, List

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rubik_sim.app.solve_worker import SolveWorker
from rubik_sim.core.cube_model import CubeModel
from rubik_sim.logic.moves import inverse_move
from rubik_sim.logic.scramble import generate_scramble
from rubik_sim.render.cube_gl_widget import CubeGLWidget

Mode = Literal["normal", "undo", "redo", "apply", "scramble"]


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación (UI) para el simulador 3D del cubo Rubik.

    Esta clase coordina:
    - El modelo lógico del cubo (`CubeModel`)
    - La visualización y animación 3D (`CubeGLWidget`)
    - El historial (undo/redo)
    - La búsqueda de solución en segundo plano (`SolveWorker`)
    """

    def __init__(self) -> None:
        """Inicializa la ventana principal, crea la UI y conecta señales."""
        super().__init__()
        self.setWindowTitle("Rubik 3D - PySide6")

        # --- Modelo + render ---
        self.model: CubeModel = CubeModel()
        self.gl_widget: CubeGLWidget = CubeGLWidget(self.model, self)

        # --- Historial ---
        self.history: List[str] = []
        self.redo_stack: List[str] = []
        self._mode: Mode = "normal"  # normal | undo | redo | apply | scramble
        self._auto_apply_when_found: bool = False

        # --- Estado solver ---
        self._pending_solution: Optional[List[str]] = None
        self._solve_worker: Optional[SolveWorker] = None

        # --- UI ---
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.addWidget(self.gl_widget, 1)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel.setFixedWidth(320)

        self.lbl_state = QLabel("")
        panel_layout.addWidget(self.lbl_state)

        # Botones principales
        row_main = QHBoxLayout()
        self.btn_reset = QPushButton("Reset")
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")
        row_main.addWidget(self.btn_reset)
        row_main.addWidget(self.btn_undo)
        row_main.addWidget(self.btn_redo)
        panel_layout.addLayout(row_main)

        # Scramble
        panel_layout.addWidget(QLabel("Scramble (mezclar)"))
        row_scr = QHBoxLayout()
        self.spin_scramble = QSpinBox()
        self.spin_scramble.setRange(1, 200)
        self.spin_scramble.setValue(25)
        self.btn_scramble = QPushButton("Scramble")
        row_scr.addWidget(self.spin_scramble, 1)
        row_scr.addWidget(self.btn_scramble, 1)
        panel_layout.addLayout(row_scr)

        # Aplicar secuencia
        panel_layout.addWidget(QLabel("Aplicar secuencia (ej: R U R' U')"))
        self.txt_seq = QLineEdit()
        self.txt_seq.setPlaceholderText("Ej: R U R' U'")
        panel_layout.addWidget(self.txt_seq)
        self.btn_apply = QPushButton("Aplicar")
        panel_layout.addWidget(self.btn_apply)

        # Solver (un solo bloque, 2 botones)
        panel_layout.addWidget(QLabel("Resolver (IDDFS: buscar pasos / resolver)"))

        row_solve = QHBoxLayout()
        self.spin_solve_depth = QSpinBox()
        self.spin_solve_depth.setRange(1, 10)
        self.spin_solve_depth.setValue(7)
        row_solve.addWidget(QLabel("Depth"), 0)
        row_solve.addWidget(self.spin_solve_depth, 1)
        panel_layout.addLayout(row_solve)

        row_solve_btns = QHBoxLayout()
        self.btn_find_solve = QPushButton("Buscar solución")
        self.btn_solve = QPushButton("Solve (auto)")
        row_solve_btns.addWidget(self.btn_find_solve)
        row_solve_btns.addWidget(self.btn_solve)
        panel_layout.addLayout(row_solve_btns)

        self.btn_cancel_solve = QPushButton("Cancelar búsqueda")
        panel_layout.addWidget(self.btn_cancel_solve)

        self.solve_status = QLabel("Listo.")
        panel_layout.addWidget(self.solve_status)

        self.solve_bar = QProgressBar()
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(0)
        panel_layout.addWidget(self.solve_bar)

        panel_layout.addWidget(QLabel("Pasos encontrados"))
        self.list_solution = QListWidget()
        panel_layout.addWidget(self.list_solution, 1)

        self.btn_apply_solution = QPushButton("Aplicar solución")
        self.btn_apply_solution.setEnabled(False)
        panel_layout.addWidget(self.btn_apply_solution)

        # Historial (movimientos)
        panel_layout.addWidget(QLabel("Historial de movimientos"))
        self.list_history = QListWidget()
        panel_layout.addWidget(self.list_history, 1)

        root_layout.addWidget(panel)
        self.setCentralWidget(root)

        # --- Conexiones ---
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_scramble.clicked.connect(self.on_scramble)
        self.btn_apply.clicked.connect(self.on_apply_sequence)
        self.btn_undo.clicked.connect(self.on_undo)
        self.btn_redo.clicked.connect(self.on_redo)

        self.btn_find_solve.clicked.connect(self.on_find_solution)
        self.btn_solve.clicked.connect(self.on_solve)
        self.btn_apply_solution.clicked.connect(self.on_apply_solution)
        self.btn_cancel_solve.clicked.connect(self.cancel_solve_search)

        # Señal desde OpenGL: movimiento aplicado al final de animación
        self.gl_widget.move_applied.connect(self.on_move_applied)

        # Atajos
        self.btn_undo.setShortcut("Ctrl+Z")
        self.btn_redo.setShortcut("Ctrl+Y")
        self.btn_reset.setShortcut("Ctrl+R")

        self._refresh_state_label()

    # -------------------
    # Helpers UI
    # -------------------
    def _refresh_state_label(self) -> None:
        """Actualiza el label de estado del cubo y la disponibilidad de botones."""
        self.lbl_state.setText(
            "Estado: resuelto ✅" if self.model.is_solved() else "Estado: mezclado 🔄"
        )
        self._update_solution_buttons()

    def _push_history(self, move: str) -> None:
        """Agrega un movimiento al historial y actualiza la lista visual.

        Args:
            move: Movimiento en notación del cubo (ej: "R", "U'", "F2").
        """
        self.history.append(move)
        self.list_history.addItem(move)
        self.list_history.scrollToBottom()

    def _is_gl_idle(self) -> bool:
        """Indica si el widget OpenGL está sin animación y sin cola pendiente."""
        queue = getattr(self.gl_widget, "_move_queue", [])
        return (not self.gl_widget.animating) and (not queue)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita los controles principales.

        Args:
            enabled: True para habilitar; False para deshabilitar (por ejemplo durante animación).
        """
        self.btn_reset.setEnabled(enabled)
        self.btn_undo.setEnabled(enabled)
        self.btn_redo.setEnabled(enabled)
        self.btn_scramble.setEnabled(enabled)
        self.btn_apply.setEnabled(enabled)
        self.txt_seq.setEnabled(enabled)
        self.spin_scramble.setEnabled(enabled)
        self.spin_solve_depth.setEnabled(enabled)
        self.btn_find_solve.setEnabled(enabled)
        self.btn_solve.setEnabled(enabled)

        can_apply_solution = (
            enabled
            and (self._pending_solution is not None)
            and (not self.model.is_solved())
        )
        self.btn_apply_solution.setEnabled(can_apply_solution)

    # -------------------
    # Movimiento aplicado (desde GL)
    # -------------------
    def on_move_applied(self, move: str) -> None:
        """Callback cuando el GL widget confirma que un movimiento terminó de aplicarse.

        Dependiendo del modo (undo/redo/apply/scramble/normal), se registra o no en historial,
        y se re-habilitan controles al finalizar la cola.

        Args:
            move: Movimiento aplicado (notación estándar).
        """
        # Si es Undo, NO lo guardamos (porque ya sacamos el último del historial)
        if self._mode == "undo":
            self._mode = "normal"
            self._refresh_state_label()
            if self._is_gl_idle():
                self._set_controls_enabled(True)
            return

        # Movimientos normales / redo / apply / scramble: sí se registran
        self._push_history(move)

        # Si el usuario hizo un movimiento normal, se invalida redo
        if self._mode == "normal":
            self.redo_stack.clear()

        self._refresh_state_label()

        # Si el cubo quedó resuelto, una solución pendiente deja de tener sentido
        if self.model.is_solved():
            self._pending_solution = None
            self.btn_apply_solution.setEnabled(False)

        # Si terminó la cola, re-habilitar
        if self._is_gl_idle():
            self._mode = "normal"
            self.solve_status.setText("Listo.")
            self.solve_bar.setRange(0, 1)
            self.solve_bar.setValue(1)
            self._set_controls_enabled(True)

    # -------------------
    # Botones básicos
    # -------------------
    def on_reset(self) -> None:
        """Resetea el cubo, historial, estado de solver y UI."""
        self.gl_widget.cancel_animation(clear_queue=True)
        self.cancel_solve_search()

        self.model.reset()
        self.history.clear()
        self.redo_stack.clear()
        self.list_history.clear()

        self._pending_solution = None
        self.list_solution.clear()
        self.btn_apply_solution.setEnabled(False)

        self.gl_widget.selected = None
        self.gl_widget.update()
        self._refresh_state_label()

        self.solve_status.setText("Listo.")
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(0)
        self._update_solution_buttons()

        self._pending_solution = None
        self.btn_apply_solution.setEnabled(False)

    def on_undo(self) -> None:
        """Revierte el último movimiento (si existe historial y no hay animación)."""
        if self.gl_widget.animating or not self.history:
            return

        last = self.history.pop()
        self.list_history.takeItem(self.list_history.count() - 1)
        self.redo_stack.append(last)

        inv = inverse_move(last)
        self._mode = "undo"
        self._set_controls_enabled(False)
        self.gl_widget.start_move_animation(inv)

    def on_redo(self) -> None:
        """Re-aplica el último movimiento deshecho (si existe redo y no hay animación)."""
        if self.gl_widget.animating or not self.redo_stack:
            return

        mv = self.redo_stack.pop()
        self._mode = "redo"
        self._set_controls_enabled(False)
        self.gl_widget.start_move_animation(mv)

    def on_apply_sequence(self) -> None:
        """Aplica una secuencia ingresada por el usuario (ej: 'R U R' U'')."""
        seq = self.txt_seq.text().strip()
        if not seq:
            return

        self.cancel_solve_search()
        self.gl_widget.cancel_animation(clear_queue=True)

        self.redo_stack.clear()
        self._mode = "apply"
        self._set_controls_enabled(False)

        try:
            self.gl_widget.play_sequence(seq)
        except Exception as exc:  # noqa: BLE001 (queremos mostrar el mensaje al usuario)
            self._set_controls_enabled(True)
            QMessageBox.warning(self, "Secuencia inválida", str(exc))

    def on_scramble(self) -> None:
        """Mezcla el cubo aplicando una secuencia aleatoria de N movimientos."""
        if self.gl_widget.animating:
            return

        # Cancela búsqueda y animación actual
        self.cancel_solve_search()
        self.gl_widget.cancel_animation(clear_queue=True)

        n = int(self.spin_scramble.value())
        scramble_seq = generate_scramble(n)

        self.redo_stack.clear()
        self._mode = "scramble"

        self._set_controls_enabled(False)
        self.gl_widget.play_sequence(scramble_seq)

    # -------------------
    # Solver (thread)
    # -------------------
    def on_find_solution(self) -> None:
        """Inicia búsqueda de solución sin aplicarla automáticamente."""
        self._start_solve_search(auto_apply=False)

    def on_solve(self) -> None:
        """Inicia búsqueda de solución y la aplica automáticamente si se encuentra."""
        self._start_solve_search(auto_apply=True)

    def _start_solve_search(self, auto_apply: bool) -> None:
        """Lanza un hilo de búsqueda (IDDFS) para encontrar una solución.

        Args:
            auto_apply: Si True, al encontrar solución se aplica inmediatamente.
        """
        if self.gl_widget.animating:
            return
        if self._solve_worker is not None and self._solve_worker.isRunning():
            return

        depth = int(self.spin_solve_depth.value())
        self._auto_apply_when_found = auto_apply

        self._pending_solution = None
        self.list_solution.clear()
        self.btn_apply_solution.setEnabled(False)
        self.btn_cancel_solve.setEnabled(True)

        self.solve_status.setText("Buscando solución...")
        self.solve_bar.setRange(0, 0)  # indeterminado
        self.solve_status.repaint()
        self.solve_bar.repaint()

        self.btn_cancel_solve.setEnabled(True)
        self._set_controls_enabled(False)

        self._solve_worker = SolveWorker(self.model, depth)
        self._solve_worker.depth_update.connect(self._on_solve_depth_update)
        self._solve_worker.finished_solution.connect(self._on_solve_finished)
        self._solve_worker.error.connect(self._on_solve_error)
        self._solve_worker.finished.connect(self._on_solve_thread_finished)
        self._solve_worker.start()

    def _on_solve_depth_update(self, d: int) -> None:
        """Actualiza el texto de estado durante la búsqueda incremental.

        Args:
            d: Profundidad actual que se está probando.
        """
        self.solve_status.setText(f"Buscando... probando profundidad {d}")

    def _on_solve_finished(self, sol: Optional[List[str]]) -> None:
        """Recibe el resultado final del solver (solución o None).

        Args:
            sol: Lista de movimientos si se encontró solución; None en caso contrario.
        """
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(1)
        self.btn_cancel_solve.setEnabled(False)

        if sol is None:
            self.solve_status.setText(
                "No se encontró solución (sube depth o usa scramble corto)."
            )
            self._pending_solution = None
            self.btn_apply_solution.setEnabled(False)
            self._set_controls_enabled(True)
            return

        self._pending_solution = sol
        self.solve_status.setText(f"Solución encontrada: {len(sol)} pasos.")
        self._update_solution_buttons()

        self.list_solution.clear()
        for i, mv in enumerate(sol, start=1):
            self.list_solution.addItem(f"{i}. {mv}")

        self.btn_apply_solution.setEnabled(True)

        if self._auto_apply_when_found:
            self.on_apply_solution()
        else:
            self._set_controls_enabled(True)

    def on_apply_solution(self) -> None:
        """Aplica la solución encontrada por el solver, si existe."""
        if not self._pending_solution:
            return
        if self.gl_widget.animating:
            return

        seq = " ".join(self._pending_solution)

        self.redo_stack.clear()
        self._mode = "apply"
        self._set_controls_enabled(False)

        self.btn_apply_solution.setEnabled(False)
        self.solve_status.setText("Aplicando solución...")
        self.solve_bar.setRange(0, 0)

        self.gl_widget.play_sequence(seq)

    def _on_solve_error(self, msg: str) -> None:
        """Maneja errores emitidos por el hilo del solver.

        Args:
            msg: Mensaje/trace del error.
        """
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(0)
        self.solve_status.setText("Error en la búsqueda (revisa consola).")
        self.btn_cancel_solve.setEnabled(False)
        self._set_controls_enabled(True)

        print("=== ERROR SOLVER THREAD ===")
        print(msg)

    def _on_solve_thread_finished(self) -> None:
        """Limpia el worker cuando el hilo finaliza."""
        if self._solve_worker is not None:
            self._solve_worker.deleteLater()
            self._solve_worker = None

    def cancel_solve_search(self) -> None:
        """Cancela la búsqueda del solver si está corriendo y limpia el estado asociado."""
        if self._solve_worker is not None and self._solve_worker.isRunning():
            self._solve_worker.requestInterruption()
            self._solve_worker.wait(300)

        self._pending_solution = None
        self.list_solution.clear()
        self.btn_apply_solution.setEnabled(False)

        self.solve_status.setText("Búsqueda cancelada.")
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(0)
        self.btn_cancel_solve.setEnabled(False)

        # No tocar animación del cubo aquí (solo cancela búsqueda)
        self._set_controls_enabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Evento de cierre de ventana: detiene el hilo del solver si está activo.

        Args:
            event: Evento de cierre de Qt.
        """
        if self._solve_worker is not None and self._solve_worker.isRunning():
            self._solve_worker.requestInterruption()
            self._solve_worker.wait(1500)
        event.accept()

    def _update_solution_buttons(self) -> None:
        """Habilita/deshabilita el botón de aplicar solución según el estado actual."""
        # Si está resuelto, no tiene sentido aplicar solución
        if self.model.is_solved():
            self.btn_apply_solution.setEnabled(False)
            return

        # Si no está resuelto, solo habilita si hay solución pendiente
        self.btn_apply_solution.setEnabled(self._pending_solution is not None)
