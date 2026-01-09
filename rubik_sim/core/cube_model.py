# rubik_sim/core/cube_model.py
from __future__ import annotations

from typing import Dict, List, Literal, Tuple

Face = Literal["U", "D", "L", "R", "F", "B"]
Color = str  # En tu implementación son letras: "W", "Y", "O", "R", "G", "B"
Vec3i = Tuple[int, int, int]
CubeHash = Tuple[Tuple[Color, ...], ...]


class CubeModel:
    """Modelo lógico del cubo Rubik 3x3 basado en rotaciones geométricas.

    Representación:
        - `state[face]` es una lista de 9 stickers (3x3) para cada cara.
        - El orden de stickers por cara corresponde a índices 0..8, en layout fila-columna.

    Rotaciones:
        - Se modela cada sticker como un "facelet" con una posición (x,y,z) y una normal.
        - Al aplicar un giro, se rotan posición y normal y se reubica el color resultante.

    Notación de movimientos:
        - Caras: U D L R F B
        - Sufijos:
            - ""  giro 90° (convención CW según `_apply_base_move_cw`)
            - "'" giro inverso (equivale a 3 giros CW)
            - "2" giro 180° (2 giros CW)
        - También soporta slices: E M S (según tu convención).
    """

    FACES: List[Face] = ["U", "D", "L", "R", "F", "B"]
    COLORS_SOLVED: Dict[Face, Color] = {
        "U": "W",
        "D": "Y",
        "L": "O",
        "R": "R",
        "F": "G",
        "B": "B",
    }

    # Normales por cara (x, y, z)
    FACE_NORMAL: Dict[Face, Vec3i] = {
        "F": (0, 0, 1),
        "B": (0, 0, -1),
        "R": (1, 0, 0),
        "L": (-1, 0, 0),
        "U": (0, 1, 0),
        "D": (0, -1, 0),
    }

    def __init__(self) -> None:
        """Inicializa el cubo en estado resuelto y construye los mapas geométricos."""
        self.state: Dict[Face, List[Color]] = {
            f: [self.COLORS_SOLVED[f]] * 9 for f in self.FACES
        }

        # Mapas: (face, idx) -> (pos, normal) y viceversa
        self._facelet_to_pn: Dict[Tuple[Face, int], Tuple[Vec3i, Vec3i]] = {}
        self._pn_to_facelet: Dict[Tuple[Vec3i, Vec3i], Tuple[Face, int]] = {}
        self._build_facelet_maps()

    # --------------------------
    # Public API
    # --------------------------
    def is_solved(self) -> bool:
        """Indica si el cubo está resuelto (cada cara con un solo color).

        Returns:
            True si el cubo está resuelto; False en caso contrario.
        """
        for f in self.FACES:
            if any(x != self.COLORS_SOLVED[f] for x in self.state[f]):
                return False
        return True

    def to_hashable(self) -> CubeHash:
        """Convierte el estado del cubo a una estructura inmutable y hasheable.

        Returns:
            Tupla de tuplas con los 9 stickers por cara, en el orden de `FACES`.
        """
        return tuple(tuple(self.state[f]) for f in self.FACES)

    def apply_sequence(self, seq: str) -> None:
        """Aplica una secuencia de movimientos separada por espacios.

        Args:
            seq: String con movimientos, por ejemplo: "R U R' U'".
        """
        for token in seq.split():
            self.apply_move(token)

    def apply_move(self, move: str) -> None:
        """Aplica un movimiento individual al cubo.

        Soporta:
            - Caras: U D L R F B
            - Slices: E M S
            - Sufijos: "'" y "2"

        Args:
            move: Movimiento en notación (por ejemplo: "R", "U'", "F2").

        Raises:
            ValueError: Si el movimiento base o sufijo no está soportado.
        """
        move = move.strip()
        if not move:
            return

        base = move[0].upper()
        if base not in ("U", "D", "L", "R", "F", "B", "E", "M", "S"):
            raise ValueError(f"Movimiento no soportado: {move}")

        suffix = move[1:] if len(move) > 1 else ""

        # turns = cuántas veces aplicar "base CW"
        turns = 1
        if suffix == "2":
            turns = 2
        elif suffix == "'":
            turns = 3
        elif suffix == "":
            turns = 1
        else:
            raise ValueError(f"Sufijo no soportado: {move}")

        for _ in range(turns):
            self._apply_base_move_cw(base)

    # --------------------------
    # Core rotation logic (geométrica)
    # --------------------------
    def _build_facelet_maps(self) -> None:
        """Construye el mapeo entre stickers (facelets) y su representación geométrica.

        Debe coincidir con cómo dibujas en OpenGL:
        - F: x=c-1, y=1-r, z=+1
        - B: x=1-c, y=1-r, z=-1   (flip X)
        - R: x=+1, y=1-r, z=c-1
        - L: x=-1, y=1-r, z=1-c   (flip Z)
        - U: x=c-1, y=+1, z=r-1
        - D: x=c-1, y=-1, z=1-r   (flip Z)
        """

        def idx_rc(i: int) -> Tuple[int, int]:
            return i // 3, i % 3

        for face in self.FACES:
            n = self.FACE_NORMAL[face]
            for i in range(9):
                r, c = idx_rc(i)

                if face == "F":
                    pos: Vec3i = (c - 1, 1 - r, 1)
                elif face == "B":
                    pos = (1 - c, 1 - r, -1)
                elif face == "R":
                    pos = (1, 1 - r, c - 1)
                elif face == "L":
                    pos = (-1, 1 - r, 1 - c)
                elif face == "U":
                    pos = (c - 1, 1, r - 1)
                elif face == "D":
                    pos = (c - 1, -1, 1 - r)
                else:
                    raise RuntimeError("Cara inválida")

                key = (face, i)
                pn = (pos, n)

                self._facelet_to_pn[key] = pn
                self._pn_to_facelet[(pos, n)] = key

    @staticmethod
    def _rot_x(v: Vec3i, turns: int) -> Vec3i:
        """Rota un vector 90°*turns alrededor de X (regla de la mano derecha)."""
        x, y, z = v
        turns %= 4
        if turns == 0:
            return (x, y, z)
        if turns == 1:
            return (x, -z, y)
        if turns == 2:
            return (x, -y, -z)
        return (x, z, -y)

    @staticmethod
    def _rot_y(v: Vec3i, turns: int) -> Vec3i:
        """Rota un vector 90°*turns alrededor de Y (regla de la mano derecha)."""
        x, y, z = v
        turns %= 4
        if turns == 0:
            return (x, y, z)
        if turns == 1:
            return (z, y, -x)
        if turns == 2:
            return (-x, y, -z)
        return (-z, y, x)

    @staticmethod
    def _rot_z(v: Vec3i, turns: int) -> Vec3i:
        """Rota un vector 90°*turns alrededor de Z (regla de la mano derecha)."""
        x, y, z = v
        turns %= 4
        if turns == 0:
            return (x, y, z)
        if turns == 1:
            return (y, -x, z)
        if turns == 2:
            return (-x, -y, z)
        return (-y, x, z)

    def _rotate_layer(self, axis: Literal["x", "y", "z"], layer_value: int, turns: int) -> None:
        """Rota una capa del cubo en pasos de 90 grados.

        Args:
            axis: Eje de rotación ('x', 'y' o 'z').
            layer_value: Capa a rotar (-1, 0 o 1).
            turns: Cantidad de cuartos de vuelta (mod 4). Ej: +1, -1, 2, etc.
        """
        # Normalizamos turns a [0..3]
        t = turns % 4

        # Copia del estado actual
        old: Dict[Face, List[Color]] = {f: self.state[f][:] for f in self.FACES}
        new: Dict[Face, List[Color]] = {f: self.state[f][:] for f in self.FACES}

        # Recorremos cada facelet y lo rotamos si está en la capa
        for face in self.FACES:
            for i in range(9):
                color = old[face][i]
                pos, n = self._facelet_to_pn[(face, i)]
                x, y, z = pos

                select = False
                if axis == "x" and x == layer_value:
                    select = True
                elif axis == "y" and y == layer_value:
                    select = True
                elif axis == "z" and z == layer_value:
                    select = True

                if not select:
                    continue

                # Rotar posición + normal
                if axis == "x":
                    pos2 = self._rot_x(pos, t)
                    n2 = self._rot_x(n, t)
                elif axis == "y":
                    pos2 = self._rot_y(pos, t)
                    n2 = self._rot_y(n, t)
                else:
                    pos2 = self._rot_z(pos, t)
                    n2 = self._rot_z(n, t)

                # Ubicar en nueva cara/índice
                dest_face, dest_i = self._pn_to_facelet[(pos2, n2)]
                new[dest_face][dest_i] = color

        self.state = new

    def _apply_base_move_cw(self, base: str) -> None:
        """Aplica un movimiento base en sentido horario (CW) según tu convención de render.

        Convención (coincide con tu render):
        - U: +90 alrededor de +Y en y=+1
        - D: -90 alrededor de +Y en y=-1
        - R: -90 alrededor de +X en x=+1
        - L: +90 alrededor de +X en x=-1
        - F: -90 alrededor de +Z en z=+1
        - B: +90 alrededor de +Z en z=-1

        Slices:
        - M: como L en x=0
        - E: como D en y=0
        - S: como F en z=0

        Args:
            base: Movimiento base (U, D, L, R, F, B, M, E, S).

        Raises:
            ValueError: Si el movimiento base no está soportado.
        """
        if base == "U":
            self._rotate_layer("y", 1, +1)
        elif base == "D":
            self._rotate_layer("y", -1, -1)
        elif base == "R":
            self._rotate_layer("x", 1, -1)
        elif base == "L":
            self._rotate_layer("x", -1, +1)
        elif base == "F":
            self._rotate_layer("z", 1, -1)
        elif base == "B":
            self._rotate_layer("z", -1, +1)
        elif base == "M":
            self._rotate_layer("x", 0, +1)
        elif base == "E":
            self._rotate_layer("y", 0, -1)
        elif base == "S":
            self._rotate_layer("z", 0, -1)
        else:
            raise ValueError(f"Movimiento no soportado: {base}")

    def reset(self) -> None:
        """Reinicia el cubo a estado resuelto."""
        self.state = {f: [self.COLORS_SOLVED[f]] * 9 for f in self.FACES}
