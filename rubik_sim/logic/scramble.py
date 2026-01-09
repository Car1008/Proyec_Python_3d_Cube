# rubik_sim/logic/scramble.py
from __future__ import annotations

import random
from typing import List, Optional

FACES: List[str] = ["U", "D", "L", "R", "F", "B"]
SUFFIX: List[str] = ["", "'", "2"]


def generate_scramble(n: int, seed: Optional[int] = None) -> str:
    """Genera una secuencia de mezcla (scramble) aleatoria para el cubo.

    La secuencia se construye evitando repetir la misma cara en movimientos consecutivos
    (por ejemplo, evita "U U'" o "R R2" seguidos), lo que produce scrambles más variados.

    Args:
        n: Cantidad de movimientos a generar.
        seed: Semilla opcional para obtener resultados reproducibles. Si es None,
            el scramble será distinto en cada ejecución.

    Returns:
        Un string con movimientos separados por espacios, por ejemplo:
        "R U' F2 L D2 ..."

    Raises:
        ValueError: Si `n` es menor o igual a 0.
    """
    if n <= 0:
        raise ValueError("n debe ser mayor que 0.")

    rng = random.Random(seed)

    seq: List[str] = []
    last_face: Optional[str] = None

    for _ in range(n):
        # Evitar repetir la misma cara consecutiva
        candidates = [m for m in FACES if m != last_face]
        face = rng.choice(candidates)
        last_face = face

        seq.append(face + rng.choice(SUFFIX))

    return " ".join(seq)
