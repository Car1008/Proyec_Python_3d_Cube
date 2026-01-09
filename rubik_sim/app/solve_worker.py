# rubik_sim/app/solve_worker.py
from PySide6.QtCore import QThread, Signal
from rubik_sim.solve.iddfs_solver import iddfs_solve
from rubik_sim.core.cube_model import CubeModel

class SolveWorker(QThread):
    depth_update = Signal(int)        # emite profundidad actual
    finished_solution = Signal(object) # list[str] o None

    def __init__(self, model: CubeModel, max_depth: int):
        super().__init__()
        # Copia del estado para que no cambie mientras se busca
        self.model = CubeModel()
        self.model.state = {f: list(model.state[f]) for f in model.FACES}
        self.max_depth = max_depth

    def run(self):
        sol = iddfs_solve(
            self.model,
            self.max_depth,
            on_depth=self.depth_update.emit,
            should_cancel=self.isInterruptionRequested
        )
        self.finished_solution.emit(sol)

