# rubik_sim/app/solve_worker.py
from __future__ import annotations

import traceback
from typing import Callable, Optional, List

from PySide6.QtCore import QThread, Signal

from rubik_sim.core.cube_model import CubeModel
from rubik_sim.solve.iddfs_solver import iddfs_solve


class SolveWorker(QThread):
    """Hilo de trabajo para buscar una solución del cubo sin bloquear la UI.

    Ejecuta un solver IDDFS (búsqueda en profundidad iterativa) sobre una copia del estado
    del cubo, emitiendo señales para informar progreso y resultado.

    Signals:
        depth_update(int): Se emite cuando el solver cambia/probara una nueva profundidad.
        finished_solution(object): Se emite al terminar con una solución (list[str]) o None.
        error(str): Se emite si ocurre una excepción durante la búsqueda.
    """

    depth_update = Signal(int)          # profundidad actual
    finished_solution = Signal(object)  # list[str] o None
    error = Signal(str)                 # traceback si algo falla

    def __init__(self, model: CubeModel, max_depth: int) -> None:
        """Crea el worker y clona el estado del cubo para trabajo en segundo plano.

        Importante: se clona el `state` para evitar condiciones de carrera, ya que la UI
        puede seguir modificando el cubo original.

        Args:
            model: Modelo del cubo cuyo estado se quiere resolver.
            max_depth: Profundidad máxima permitida para la búsqueda IDDFS.
        """
        super().__init__()
        self.model: CubeModel = CubeModel()
        # Copia profunda del estado: dict[face] -> list[stickers]
        self.model.state = {f: list(model.state[f]) for f in model.FACES}
        self.max_depth: int = max_depth

    def run(self) -> None:
        """Punto de entrada del hilo.

        Llama al solver IDDFS y emite el resultado por señales.
        """
        try:
            sol: Optional[List[str]] = iddfs_solve(
                self.model,
                self.max_depth,
                on_depth=self.depth_update.emit,
                should_cancel=self.isInterruptionRequested,
            )
            self.finished_solution.emit(sol)
        except Exception:
            msg = traceback.format_exc()
            self.error.emit(msg)
