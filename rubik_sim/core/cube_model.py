# rubik_sim/core/cube_model.py
from copy import deepcopy


class CubeModel:
    """
    Modelo lógico de un cubo Rubik 3x3.

    Representación:
    - 6 caras: U, D, L, R, F, B
    - cada cara es una lista de 9 elementos (3x3 en orden fila-major)
      índices:
        0 1 2
        3 4 5
        6 7 8
    """

    FACES = ("U", "D", "L", "R", "F", "B")

    def __init__(self):
        self.reset()

    def reset(self):
        # Colores por defecto (puedes cambiarlos después)
        self.state = {
            "U": ["W"] * 9,  # Up = White
            "D": ["Y"] * 9,  # Down = Yellow
            "L": ["O"] * 9,  # Left = Orange
            "R": ["R"] * 9,  # Right = Red
            "F": ["G"] * 9,  # Front = Green
            "B": ["B"] * 9,  # Back = Blue
        }

    def copy(self):
        c = CubeModel()
        c.state = deepcopy(self.state)
        return c

    def is_solved(self) -> bool:
        for face in self.FACES:
            v = self.state[face]
            if any(x != v[0] for x in v):
                return False
        return True

    def to_hashable(self):
        """
        Devuelve una tupla inmutable (útil para comparar estados o solvers).
        """
        return tuple(self.state[f][i] for f in self.FACES for i in range(9))

    # --------- helpers de rotación ----------
    @staticmethod
    def _rotate_face_cw(face_list):
        """
        Rota una cara 3x3 (lista de 9) en sentido horario.
        """
        return [
            face_list[6], face_list[3], face_list[0],
            face_list[7], face_list[4], face_list[1],
            face_list[8], face_list[5], face_list[2],
        ]

    @staticmethod
    def _rotate_face_ccw(face_list):
        """
        Rota una cara 3x3 (lista de 9) en sentido antihorario.
        """
        return [
            face_list[2], face_list[5], face_list[8],
            face_list[1], face_list[4], face_list[7],
            face_list[0], face_list[3], face_list[6],
        ]

    # --------- movimientos ----------
    def apply_move(self, move: str):
        """
        Aplica un movimiento:
        - "U", "D", "L", "R", "F", "B"
        - inversos: "U'", ...
        - dobles: "U2", ...
        """
        move = move.strip()
        if not move:
            return

        base = move[0]
        if base not in ("U", "D", "L", "R", "F", "B"):
            raise ValueError(f"Movimiento inválido: {move}")

        # Determinar cantidad de giros (cw)
        if move.endswith("2"):
            times = 2
        elif move.endswith("'"):
            times = 3  # 3 cw = 1 ccw
        else:
            times = 1

        for _ in range(times):
            self._apply_base_move_cw(base)

    def apply_sequence(self, seq: str):
        """
        Aplica una secuencia tipo: "R U R' U'"
        """
        tokens = [t for t in seq.split() if t.strip()]
        for t in tokens:
            self.apply_move(t)

    def _apply_base_move_cw(self, base: str):
        """
        Aplica un movimiento base en sentido horario (cw):
        U, D, L, R, F, B
        """
        if base == "U":
            self._move_U()
        elif base == "D":
            self._move_D()
        elif base == "L":
            self._move_L()
        elif base == "R":
            self._move_R()
        elif base == "F":
            self._move_F()
        elif base == "B":
            self._move_B()

    # NOTA: por ahora implementaremos solo U (para partir y testear),
    # y luego en el siguiente paso completamos D,L,R,F,B.

    def _move_U(self):
        # Rotar cara U clockwise
        self.state["U"] = self._rotate_face_cw(self.state["U"])

        # Ciclo de bordes superiores: F -> R -> B -> L -> F (fila superior)
        F = self.state["F"]
        R = self.state["R"]
        B = self.state["B"]
        L = self.state["L"]

        f_top = F[0:3]
        r_top = R[0:3]
        b_top = B[0:3]
        l_top = L[0:3]

        # F top <- L top
        F[0:3] = l_top
        # R top <- F top (old)
        R[0:3] = f_top
        # B top <- R top (old)
        B[0:3] = r_top
        # L top <- B top (old)
        L[0:3] = b_top

    def _move_D(self):
        raise NotImplementedError("D aún no implementado")

    def _move_L(self):
        raise NotImplementedError("L aún no implementado")

    def _move_R(self):
        raise NotImplementedError("R aún no implementado")

    def _move_F(self):
        raise NotImplementedError("F aún no implementado")

    def _move_B(self):
        raise NotImplementedError("B aún no implementado")
