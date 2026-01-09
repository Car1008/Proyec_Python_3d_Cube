# rubik_sim/app/main_window.py
import random
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QSpinBox, QListWidget, QMessageBox
)

from rubik_sim.core.cube_model import CubeModel
from rubik_sim.render.cube_gl_widget import CubeGLWidget
from rubik_sim.solve.iddfs_solver import iddfs_solve
from rubik_sim.core.cube_model import CubeModel
from rubik_sim.app.solve_worker import SolveWorker
from PySide6.QtWidgets import QProgressBar





def inverse_move(m: str) -> str:
    m = m.strip()
    if not m:
        return m
    base = m[0]
    suf = m[1:] if len(m) > 1 else ""
    if suf == "":
        return base + "'"
    if suf == "'":
        return base
    if suf == "2":
        return base + "2"
    return m  # fallback


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rubik 3D - PySide6")

        # Modelo + render
        self.model = CubeModel()
        self.gl_widget = CubeGLWidget(self.model, self)

        # Historial para Undo
        self.history = []

        # UI
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.addWidget(self.gl_widget, 1)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel.setFixedWidth(280)

        self.lbl_state = QLabel("Estado: resuelto ✅")
        panel_layout.addWidget(self.lbl_state)

        # --- Botones principales ---
        btn_row = QHBoxLayout()

        self.btn_reset = QPushButton("Reset")
        self.btn_undo = QPushButton("Undo")
        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_undo)

        panel_layout.addLayout(btn_row)

        # --- Scramble ---
        panel_layout.addWidget(QLabel("Scramble (mezclar)"))

        scramble_row = QHBoxLayout()
        self.spin_scramble = QSpinBox()
        self.spin_scramble.setRange(1, 200)
        self.spin_scramble.setValue(25)

        self.btn_scramble = QPushButton("Scramble")
        scramble_row.addWidget(self.spin_scramble, 1)
        scramble_row.addWidget(self.btn_scramble, 1)

        panel_layout.addLayout(scramble_row)

        # --- Aplicar secuencia ---
        panel_layout.addWidget(QLabel("Aplicar secuencia (ej: R U R' U')"))

        self.txt_seq = QLineEdit()
        self.txt_seq.setPlaceholderText("Ej: R U R' U'")
        panel_layout.addWidget(self.txt_seq)

        self.btn_apply = QPushButton("Aplicar")
        panel_layout.addWidget(self.btn_apply)

        # --- Historial ---
        panel_layout.addWidget(QLabel("Historial"))
        self.list_history = QListWidget()
        panel_layout.addWidget(self.list_history, 1)

        root_layout.addWidget(panel)

        self.setCentralWidget(root)

        # Conexiones
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_scramble.clicked.connect(self.on_scramble)
        self.btn_apply.clicked.connect(self.on_apply_sequence)
        self.btn_undo.clicked.connect(self.on_undo)

        self.btn_redo = QPushButton("Redo")
        btn_row.addWidget(self.btn_redo)
        self.btn_redo.clicked.connect(self.on_redo) 
        self.btn_redo.setShortcut("Ctrl+Y")

        
        # Señal desde OpenGL: movimiento aplicado al final de animación
        self.gl_widget.move_applied.connect(self.on_move_applied)

        # Atajos simples (opcional, pero útil)
        self.btn_undo.setShortcut("Ctrl+Z")
        self.btn_reset.setShortcut("Ctrl+R")

        self._refresh_state_label()

        
        self.redo_stack = []

        self._mode = "normal"   # "normal" | "undo" | "redo" | "apply" | "scramble"

        # --- Solver IDDFS ---
        panel_layout.addWidget(QLabel("Resolver (básico IDDFS)"))

        solve_row = QHBoxLayout()
        self.spin_solve_depth = QSpinBox()
        self.spin_solve_depth.setRange(1, 10)
        self.spin_solve_depth.setValue(6)

        self.btn_solve = QPushButton("Solve")
        solve_row.addWidget(self.spin_solve_depth, 1)
        solve_row.addWidget(self.btn_solve, 1)
        panel_layout.addLayout(solve_row)

        # --- Solver educativo ---
        panel_layout.addWidget(QLabel("Resolver (mostrar pasos)"))

        solve_row = QHBoxLayout()
        self.spin_solve_depth = QSpinBox()
        self.spin_solve_depth.setRange(1, 10)
        self.spin_solve_depth.setValue(7)

        self.btn_find_solve = QPushButton("Buscar solución")
        solve_row.addWidget(self.spin_solve_depth, 1)
        solve_row.addWidget(self.btn_find_solve, 1)
        panel_layout.addLayout(solve_row)

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

        self._pending_solution = None
        self._solve_worker = None
        self.btn_cancel_solve = QPushButton("Cancelar búsqueda")
        self.btn_cancel_solve.setEnabled(False)
        panel_layout.addWidget(self.btn_cancel_solve)


    # -------------------
    # Helpers UI
    # -------------------
    def _refresh_state_label(self):
        self.lbl_state.setText("Estado: resuelto ✅" if self.model.is_solved() else "Estado: mezclado 🔄")

    def _push_history(self, move: str):
        self.history.append(move)
        self.list_history.addItem(move)
        self.list_history.scrollToBottom()

    # -------------------
    # Eventos
    # -------------------
    def on_move_applied(self, move: str):
        # Si es Undo, NO registramos el move (porque ya quitamos el último del historial)
        if self._mode == "undo":
            self._mode = "normal"
            self._refresh_state_label()
            # habilitar controles solo si ya terminó todo
            if not self.gl_widget.animating and not getattr(self.gl_widget, "_move_queue", []):
                self._set_controls_enabled(True)
            return

        # Si es Redo o movimientos normales/apply/scramble, sí se registran
        self._push_history(move)

        # si el usuario hizo un movimiento normal (drag), se invalida el redo
        if self._mode == "normal":
            self.redo_stack.clear()

        # si era redo/apply/scramble, volvemos a normal cuando vaya terminando
        if self._mode in ("redo", "apply", "scramble"):
            # si la cola ya terminó, volvemos a normal
            if not self.gl_widget.animating and not getattr(self.gl_widget, "_move_queue", []):
                self._mode = "normal"

        self._refresh_state_label()

        if not self.gl_widget.animating and not getattr(self.gl_widget, "_move_queue", []):
            self._set_controls_enabled(True)


    def on_reset(self):
        # cancelamos animación/cola antes
        self.gl_widget.cancel_animation(clear_queue=True)

        self.model.reset()
        self.history.clear()
        self.list_history.clear()
        self.redo_stack.clear()

        self.gl_widget.selected = None
        self.gl_widget.update()
        self._refresh_state_label()
        
        
    def on_undo(self):
        if self.gl_widget.animating or not self.history:
            return

        last = self.history.pop()
        self.list_history.takeItem(self.list_history.count() - 1)

        self.redo_stack.append(last)
        inv = inverse_move(last)

        self._mode = "undo"
        self._set_controls_enabled(False)
        self.gl_widget.start_move_animation(inv)



    def on_apply_sequence(self):
        seq = self.txt_seq.text().strip()
        if not seq:
            return

        # cancelamos animación actual y cola
        self.gl_widget.cancel_animation(clear_queue=True)

        # Validación básica (si hay token raro, avisamos)
        try:
            self._set_controls_enabled(False)
            self.redo_stack.clear()
            self._mode = "apply"  
            self._set_controls_enabled(False)

            # Encolar movimientos animados
            self.gl_widget.play_sequence(seq)
        except Exception as e:
            QMessageBox.warning(self, "Secuencia inválida", str(e))

    def on_scramble(self):
        if self.gl_widget.animating:
            return

        n = int(self.spin_scramble.value())
        moves = ["U", "D", "L", "R", "F", "B"]
        suffix = ["", "'", "2"]

        seq = []
        last_face = None
        for _ in range(n):
            face = random.choice([m for m in moves if m != last_face])
            last_face = face
            seq.append(face + random.choice(suffix))

        scramble_seq = " ".join(seq)

        # cancelamos animación/cola, y mezclamos animado
        self.gl_widget.cancel_animation(clear_queue=True)
        self._set_controls_enabled(False)

        self._set_controls_enabled(False)

        self.redo_stack.clear()
        self._mode = "scramble"
        self._set_controls_enabled(False)

        
        self.gl_widget.play_sequence(scramble_seq)


    def on_redo(self):
        if self.gl_widget.animating or not self.redo_stack:
            return

        mv = self.redo_stack.pop()

        self._mode = "redo"
        self._set_controls_enabled(False)
        self.gl_widget.start_move_animation(mv)

    def on_solve(self):
        if self.gl_widget.animating:
            return

        depth = int(self.spin_solve_depth.value())

        # (opcional) deshabilitar controles si tienes ese método
        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(False)

        sol = iddfs_solve(self.model, max_depth=depth)

        if sol is None:
            if hasattr(self, "_set_controls_enabled"):
                self._set_controls_enabled(True)
            QMessageBox.information(
                self,
                "No encontrado",
                f"No se encontró solución con profundidad ≤ {depth}.\n"
                f"Prueba un scramble más corto (3–6) o sube el depth."
            )
            return

        # Ejecutar animado
        if hasattr(self, "redo_stack"):
            self.redo_stack.clear()

        if hasattr(self, "_mode"):
            self._mode = "apply"

        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(False)

        self.gl_widget.play_sequence(" ".join(sol))


    def on_find_solution(self):
        if self.gl_widget.animating:
            return

        depth = int(self.spin_solve_depth.value())

        # limpiar resultados previos
        self._pending_solution = None
        self.list_solution.clear()
        self.btn_apply_solution.setEnabled(False)
        self.btn_cancel_solve.setEnabled(True)
        

        # feedback UI (barra indeterminada)
        self.solve_status.setText("Buscando solución...")
        self.solve_bar.setRange(0, 0)   # indeterminado (spinner)
        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(False)

        if self._solve_worker is not None and self._solve_worker.isRunning():
            return  # ya hay una búsqueda en curso

        # lanzar hilo
        self._solve_worker = SolveWorker(self.model, depth)
        self._solve_worker.depth_update.connect(self._on_solve_depth_update)
        self._solve_worker.finished_solution.connect(self._on_solve_finished)

        # limpieza segura
        self._solve_worker.finished.connect(self._on_solve_thread_finished)

        self._solve_worker.start()

        
    def _on_solve_depth_update(self, d: int):
        self.solve_status.setText(f"Buscando... probando profundidad {d}")

    def _on_solve_finished(self, sol):
        # parar barra
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(1)
        self.btn_cancel_solve.setEnabled(False)

        if sol is None:
            self.solve_status.setText("No se encontró solución (prueba subir depth o usar scramble corto).")
            self._pending_solution = None
            self.btn_apply_solution.setEnabled(False)
        else:
            self.solve_status.setText(f"Solución encontrada: {len(sol)} pasos.")
            self._pending_solution = sol

            # mostrar pasos
            self.list_solution.clear()
            for i, mv in enumerate(sol, start=1):
                self.list_solution.addItem(f"{i}. {mv}")

            self.btn_apply_solution.setEnabled(True)

        # reactivar controles (pero sin iniciar animación aún)
        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(True)

    def on_apply_solution(self):
        if not self._pending_solution:
            return
        if self.gl_widget.animating:
            return

        seq = " ".join(self._pending_solution)

        # opcional: limpiar redo al ejecutar solución
        if hasattr(self, "redo_stack"):
            self.redo_stack.clear()

        if hasattr(self, "_mode"):
            self._mode = "apply"

        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(False)

        self.solve_status.setText("Aplicando solución...")
        self.solve_bar.setRange(0, 0)  # indeterminado mientras anima

        self.gl_widget.play_sequence(seq)

        # cuando termine la cola, tu on_move_applied ya re-habilita controles.
        # para dejar la barra “terminada” al final, puedes hacerlo simple:
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(1)

    def _on_solve_thread_finished(self):
        # Thread terminó: liberar referencia (evita "Destroyed while running")
        if self._solve_worker is not None:
            self._solve_worker.deleteLater()
            self._solve_worker = None

    def closeEvent(self, event):
        # Si se está buscando solución, pedir cancelación y esperar un poquito
        if self._solve_worker is not None and self._solve_worker.isRunning():
            self._solve_worker.requestInterruption()
            self._solve_worker.wait(1500)  # espera hasta 1.5s a que pare
        event.accept()

    def cancel_solve_search(self):
        # Cancelar hilo si está corriendo
        if self._solve_worker is not None and self._solve_worker.isRunning():
            self._solve_worker.requestInterruption()
            # no bloquees mucho la UI; con wait corto basta
            self._solve_worker.wait(200)

        # limpiar estado de UI del solver
        self._pending_solution = None
        self.list_solution.clear()
        self.btn_apply_solution.setEnabled(False)

        self.solve_status.setText("Búsqueda cancelada.")
        self.solve_bar.setRange(0, 1)
        self.solve_bar.setValue(0)

        self.btn_cancel_solve.setEnabled(False)

        # re-habilitar controles generales
        if hasattr(self, "_set_controls_enabled"):
            self._set_controls_enabled(True)


    def _set_controls_enabled(self, enabled: bool):
        self.btn_reset.setEnabled(enabled)
        self.btn_undo.setEnabled(enabled)
        self.btn_redo.setEnabled(enabled)
        self.btn_scramble.setEnabled(enabled)
        self.btn_apply.setEnabled(enabled)
        self.txt_seq.setEnabled(enabled)
        self.spin_scramble.setEnabled(enabled)
        self.btn_solve.clicked.connect(self.on_solve)
        self.btn_find_solve.clicked.connect(self.on_find_solution)
        self.btn_apply_solution.clicked.connect(self.on_apply_solution)
        self.btn_cancel_solve.clicked.connect(self.cancel_solve_search)


