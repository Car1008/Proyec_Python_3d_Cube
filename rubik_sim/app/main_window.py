# rubik_sim/app/main_window.py
import random
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QSpinBox, QListWidget, QMessageBox
)

from rubik_sim.core.cube_model import CubeModel
from rubik_sim.render.cube_gl_widget import CubeGLWidget


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

        # Señal desde OpenGL: movimiento aplicado al final de animación
        self.gl_widget.move_applied.connect(self.on_move_applied)

        # Atajos simples (opcional, pero útil)
        self.btn_undo.setShortcut("Ctrl+Z")
        self.btn_reset.setShortcut("Ctrl+R")

        self._refresh_state_label()

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
        # Cuando el render termina la animación y aplica el movimiento real al modelo
        self._push_history(move)
        self._refresh_state_label()

    def on_reset(self):
        # cancelamos animación/cola antes
        self.gl_widget.cancel_animation(clear_queue=True)

        self.model.reset()
        self.history.clear()
        self.list_history.clear()
        self.gl_widget.selected = None
        self.gl_widget.update()
        self._refresh_state_label()

    def on_undo(self):
        if self.gl_widget.animating:
            return  # no hacemos undo a mitad de animación

        if not self.history:
            return

        last = self.history.pop()
        self.list_history.takeItem(self.list_history.count() - 1)

        inv = inverse_move(last)

        # Importante: no queremos que el undo se agregue al historial como si fuera "nuevo"
        # Solución simple: aplicamos el movimiento al modelo directo (sin anim) y actualizamos.
        # Si quieres undo animado, lo hacemos luego.
        self.model.apply_move(inv)
        self.gl_widget.update()
        self._refresh_state_label()

    def on_apply_sequence(self):
        seq = self.txt_seq.text().strip()
        if not seq:
            return

        # cancelamos animación actual y cola
        self.gl_widget.cancel_animation(clear_queue=True)

        # Validación básica (si hay token raro, avisamos)
        try:
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
        self.gl_widget.play_sequence(scramble_seq)
