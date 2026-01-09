# rubik_sim/logic/moves.py

VALID_FACES = {"U", "D", "L", "R", "F", "B"}
VALID_SUFFIX = {"", "'", "2"}

def normalize_token(tok: str) -> str:
    """
    Normaliza un token de movimiento.
    - Convierte comilla tipográfica ’ a '
    - Convierte D2' -> D2
    """
    tok = tok.strip().replace("’", "'")
    if not tok:
        return ""
    if len(tok) == 1 and tok in VALID_FACES:
        return tok
    base = tok[0]
    suf = tok[1:]
    if base not in VALID_FACES:
        raise ValueError(f"Movimiento inválido: {tok}")
    if suf == "2'":
        suf = "2"
    if suf not in VALID_SUFFIX:
        raise ValueError(f"Sufijo inválido en: {tok}")
    return base + suf

def inverse_move(m: str) -> str:
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
    return m

def parse_sequence(text: str) -> list[str]:
    """
    Convierte un string 'R U R' U'' en lista de tokens normalizados.
    """
    tokens = [t for t in text.strip().split() if t.strip()]
    out = []
    for t in tokens:
        out.append(normalize_token(t))
    return out
