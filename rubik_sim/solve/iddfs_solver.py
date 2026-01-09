# rubik_sim/solve/iddfs_solver.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

from rubik_sim.core.cube_model import CubeModel


MOVES = [
    "U","U'","U2",
    "D","D'","D2",
    "L","L'","L2",
    "R","R'","R2",
    "F","F'","F2",
    "B","B'","B2",
]

INV = {
    "U":"U'","U'":"U","U2":"U2",
    "D":"D'","D'":"D","D2":"D2",
    "L":"L'","L'":"L","L2":"L2",
    "R":"R'","R'":"R","R2":"R2",
    "F":"F'","F'":"F","F2":"F2",
    "B":"B'","B'":"B","B2":"B2",
}


def _copy_model(model: CubeModel) -> CubeModel:
    c = CubeModel()
    c.state = {f: list(model.state[f]) for f in model.FACES}
    return c

def _hash(model: CubeModel) -> Tuple[Tuple[str, ...], ...]:
    return model.to_hashable()

def iddfs_solve(model: CubeModel, max_depth: int = 6, on_depth=None, should_cancel=None) -> Optional[List[str]]:

    if model.is_solved():
        return []

    start = _copy_model(model)
    start_hash = _hash(start)

    for depth_limit in range(1, max_depth + 1):
        if should_cancel and should_cancel():
            return None

        if on_depth:
            on_depth(depth_limit)


        path: List[str] = []
        seen_on_path = {start_hash}
        res = _dfs(start, depth_limit, path, seen_on_path, last_move=None, should_cancel=should_cancel)

        if res is not None:
            return res

    return None


def _dfs(model: CubeModel, remaining: int, path: List[str], seen_on_path: set,
         last_move: Optional[str], should_cancel=None) -> Optional[List[str]]:
    
    if should_cancel and should_cancel():
        return None

    if model.is_solved():
        return list(path)

    if remaining == 0:
        return None

    for mv in MOVES:
        # poda 1: no repetir la misma cara dos veces seguidas (U luego U/U')
        if last_move is not None and mv[0] == last_move[0]:
            continue
        # poda 2: no hacer inmediatamente el inverso del último
        if last_move is not None and INV.get(last_move) == mv:
            continue

        child = _copy_model(model)
        child.apply_move(mv)
        h = _hash(child)

        if h in seen_on_path:
            continue

        path.append(mv)
        seen_on_path.add(h)

        ans = _dfs(child, remaining - 1, path, seen_on_path, last_move=mv, should_cancel=should_cancel)

        if ans is not None:
            return ans

        # backtrack
        seen_on_path.remove(h)
        path.pop()

    return None
