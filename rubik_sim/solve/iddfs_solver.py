# rubik_sim/solve/iddfs_solver.py
from __future__ import annotations

from typing import Callable, Iterable, Optional, Sequence, Set, Tuple, List

from rubik_sim.core.cube_model import CubeModel

# Tipo del "hash" del cubo. Debe calzar con lo que retorna CubeModel.to_hashable().
CubeHash = Tuple[Tuple[str, ...], ...]
OnDepthCallback = Callable[[int], None]
ShouldCancelCallback = Callable[[], bool]

MOVES: List[str] = [
    "U", "U'", "U2",
    "D", "D'", "D2",
    "L", "L'", "L2",
    "R", "R'", "R2",
    "F", "F'", "F2",
    "B", "B'", "B2",
]

INV: dict[str, str] = {
    "U": "U'", "U'": "U", "U2": "U2",
    "D": "D'", "D'": "D", "D2": "D2",
    "L": "L'", "L'": "L", "L2": "L2",
    "R": "R'", "R'": "R", "R2": "R2",
    "F": "F'", "F'": "F", "F2": "F2",
    "B": "B'", "B'": "B", "B2": "B2",
}


def _copy_model(model: CubeModel) -> CubeModel:
    """Crea una copia del modelo del cubo copiando su estado interno.

    Args:
        model: Cubo a copiar.

    Returns:
        Una nueva instancia de `CubeModel` con el mismo estado.
    """
    c = CubeModel()
    c.state = {f: list(model.state[f]) for f in model.FACES}
    return c


def _hash(model: CubeModel) -> CubeHash:
    """Convierte el estado del cubo a una forma hasheable.

    Args:
        model: Cubo a hashear.

    Returns:
        Una tupla inmutable (hashable) que representa el estado del cubo.
    """
    return model.to_hashable()


def iddfs_solve(
    model: CubeModel,
    max_depth: int = 6,
    on_depth: Optional[OnDepthCallback] = None,
    should_cancel: Optional[ShouldCancelCallback] = None,
) -> Optional[List[str]]:
    """Busca una solución del cubo usando IDDFS (búsqueda en profundidad iterativa).

    El algoritmo itera el límite de profundidad desde 1 hasta `max_depth`, y en cada
    iteración ejecuta DFS con podas simples para reducir el espacio de búsqueda:
    - Evita repetir la misma cara consecutivamente (por ejemplo: U seguido de U/U'/U2).
    - Evita aplicar inmediatamente el inverso del último movimiento.

    Args:
        model: Cubo a resolver.
        max_depth: Profundidad máxima que se probará en la búsqueda.
        on_depth: Callback opcional que se llama con la profundidad actual probada.
        should_cancel: Callback opcional para cancelar la búsqueda (retorna True si se cancela).

    Returns:
        Una lista de movimientos (notación estándar, ej: ["R", "U", "R'", "U'"])
        si se encuentra solución dentro de `max_depth`. Si no se encuentra o se
        cancela, retorna None. Si el cubo ya está resuelto, retorna una lista vacía.

    Notes:
        - Este solver es útil para scrambles cortos o como demostración educativa.
        - Para scrambles largos, IDDFS se vuelve muy costoso (explosión combinatoria).
    """
    if model.is_solved():
        return []

    start = _copy_model(model)
    start_hash = _hash(start)

    for depth_limit in range(1, max_depth + 1):
        if should_cancel is not None and should_cancel():
            return None

        if on_depth is not None:
            on_depth(depth_limit)

        path: List[str] = []
        seen_on_path: Set[CubeHash] = {start_hash}

        res = _dfs(
            start,
            depth_limit,
            path,
            seen_on_path,
            last_move=None,
            should_cancel=should_cancel,
        )
        if res is not None:
            return res

    return None


def _dfs(
    model: CubeModel,
    remaining: int,
    path: List[str],
    seen_on_path: Set[CubeHash],
    last_move: Optional[str],
    should_cancel: Optional[ShouldCancelCallback] = None,
) -> Optional[List[str]]:
    """DFS limitado en profundidad para IDDFS.

    Args:
        model: Estado actual del cubo.
        remaining: Profundidad restante (pasos disponibles).
        path: Ruta acumulada (movimientos aplicados hasta ahora).
        seen_on_path: Conjunto de estados visitados en la rama actual (evita ciclos).
        last_move: Último movimiento aplicado (para podas).
        should_cancel: Callback opcional de cancelación.

    Returns:
        La solución como lista de movimientos si se encuentra; si no, None.
    """
    if should_cancel is not None and should_cancel():
        return None

    if model.is_solved():
        return list(path)

    if remaining == 0:
        return None

    for mv in MOVES:
        # Poda 1: no repetir la misma cara dos veces seguidas (U luego U/U'/U2)
        if last_move is not None and mv[0] == last_move[0]:
            continue

        # Poda 2: no hacer inmediatamente el inverso del último
        if last_move is not None and INV.get(last_move) == mv:
            continue

        child = _copy_model(model)
        child.apply_move(mv)
        h = _hash(child)

        # Evitar ciclos dentro de la misma rama
        if h in seen_on_path:
            continue

        path.append(mv)
        seen_on_path.add(h)

        ans = _dfs(
            child,
            remaining - 1,
            path,
            seen_on_path,
            last_move=mv,
            should_cancel=should_cancel,
        )
        if ans is not None:
            return ans

        # Backtrack
        seen_on_path.remove(h)
        path.pop()

    return None
