# rubik_sim/app/solve_worker.py
import traceback
from PySide6.QtCore import QThread, Signal

from rubik_sim.solve.iddfs_solver import iddfs_solve
from rubik_sim.core.cube_model import CubeModel

class SolveWorker(QThread):
    depth_update = Signal(int)          # profundidad actual
    finished_solution = Signal(object)  # list[str] o None
    error = Signal(str)                # mensaje de error (si algo falla)

    def __init__(self, model: CubeModel, max_depth: int):
        super().__init__()
        self.model = CubeModel()
        self.model.state = {f: list(model.state[f]) for f in model.FACES}
        self.max_depth = max_depth

    def run(self):
        try:
            sol = iddfs_solve(
                self.model,
                self.max_depth,
                on_depth=self.depth_update.emit,
                should_cancel=self.isInterruptionRequested
            )
            self.finished_solution.emit(sol)
        except Exception:
            msg = traceback.format_exc()
            self.error.emit(msg)
