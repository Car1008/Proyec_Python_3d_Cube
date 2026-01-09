# rubik_sim/logic/moves.py
from __future__ import annotations

from typing import List, Set

VALID_FACES: Set[str] = {"U", "D", "L", "R", "F", "B"}
VALID_SUFFIX: Set[str] = {"", "'", "2"}


def normalize_token(tok: str) -> str:
    """Normaliza un token de movimiento a un formato estándar.

    Reglas principales:
    - Elimina espacios y convierte comilla tipográfica (’ o ‘) a comilla simple (').
    - Acepta notación de una cara con sufijo opcional:
        - ""  (ej: "R")
        - "'" (ej: "R'")
        - "2" (ej: "R2")
    - Corrige el caso típico "D2'" -> "D2" (ya que el inverso de un 180° es el mismo).

    Args:
        tok: Token de movimiento (por ejemplo: "R", "U'", "F2", "D2'").

    Returns:
        Token normalizado (por ejemplo: "D2'" -> "D2").

    Raises:
        ValueError: Si la cara no es válida o si el sufijo no es válido.
    """
    tok = tok.strip().replace("’", "'").replace("‘", "'")
    if not tok:
        return ""

    # Caso simple: "R"
    if len(tok) == 1 and tok in VALID_FACES:
        return tok

    base = tok[0]
    suf = tok[1:]

    if base not in VALID_FACES:
        raise ValueError(f"Movimiento inválido: {tok}")

    # Corrección: "D2'" -> "D2"
    if suf == "2'":
        suf = "2"

    if suf not in VALID_SUFFIX:
        raise ValueError(f"Sufijo inválido en: {tok}")

    return base + suf


def inverse_move(m: str) -> str:
    """Devuelve el movimiento inverso de un token.

    Ejemplos:
        - "R"  -> "R'"
        - "R'" -> "R"
        - "R2" -> "R2"

    Args:
        m: Movimiento en notación estándar (o normalizable), por ejemplo: "R", "U'", "F2".

    Returns:
        El movimiento inverso. Si `m` es un string vacío, retorna "".

    Raises:
        ValueError: Si `m` no es un token válido.
    """
    m = normalize_token(m)
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

    # No debería ocurrir si normalize_token valida correctamente
    return m


def parse_sequence(text: str) -> List[str]:
    """Convierte una secuencia escrita como texto en una lista de movimientos normalizados.

    La entrada debe separar movimientos por espacios. Por ejemplo:
        "R U R' U'" -> ["R", "U", "R'", "U'"]

    Args:
        text: Secuencia de movimientos escrita como string.

    Returns:
        Lista de tokens normalizados, en el mismo orden.

    Raises:
        ValueError: Si algún token es inválido.
    """
    tokens = [t for t in text.strip().split() if t.strip()]
    out: List[str] = []
    for t in tokens:
        out.append(normalize_token(t))
    return out
