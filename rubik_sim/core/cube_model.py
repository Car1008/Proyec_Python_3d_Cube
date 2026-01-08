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
        if base not in ("U", "D", "L", "R", "F", "B", "E", "M", "S"):
            raise ValueError(f"Movimiento inválido: {move}")
        
        elif base == "E":
            self._move_E()
        elif base == "M":
            self._move_M()
        elif base == "S":
            self._move_S()

        
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
    def _get_col(self, face, col):
        s = self.state[face]
        return [s[col], s[col + 3], s[col + 6]]

    def _set_col(self, face, col, values):
        s = self.state[face]
        s[col], s[col + 3], s[col + 6] = values[0], values[1], values[2]

    def _get_row(self, face, row):
        s = self.state[face]
        i = row * 3
        return [s[i], s[i + 1], s[i + 2]]

    def _set_row(self, face, row, values):
        s = self.state[face]
        i = row * 3
        s[i], s[i + 1], s[i + 2] = values[0], values[1], values[2]


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
        # Rotar cara D clockwise
        self.state["D"] = self._rotate_face_cw(self.state["D"])

        # Ciclo de bordes inferiores: F -> L -> B -> R -> F (fila inferior)
        # (equivalente a U pero en la parte de abajo, ojo con el sentido)
        F = self.state["F"]
        R = self.state["R"]
        B = self.state["B"]
        L = self.state["L"]

        f_bot = F[6:9]
        r_bot = R[6:9]
        b_bot = B[6:9]
        l_bot = L[6:9]

        # F bottom <- R bottom
        F[6:9] = r_bot
        # L bottom <- F bottom (old)
        L[6:9] = f_bot
        # B bottom <- L bottom (old)
        B[6:9] = l_bot
        # R bottom <- B bottom (old)
        R[6:9] = b_bot


    def _move_R(self):
        # Rotar cara R clockwise
        self.state["R"] = self._rotate_face_cw(self.state["R"])

        # Columnas afectadas:
        # U col 2, F col 2, D col 2, B col 0 (pero B va invertida)
        u = self._get_col("U", 2)
        f = self._get_col("F", 2)
        d = self._get_col("D", 2)
        b = self._get_col("B", 0)[::-1]  # invertir

        # Ciclo (convención estándar):
        # U <- F
        self._set_col("U", 2, f)
        # F <- D
        self._set_col("F", 2, d)
        # D <- B (invertido ya)
        self._set_col("D", 2, b)
        # B <- U (pero al guardar en B col 0, se invierte)
        self._set_col("B", 0, u[::-1])


    def _move_L(self):
        # Rotar cara L clockwise
        self.state["L"] = self._rotate_face_cw(self.state["L"])

        # U col 0, F col 0, D col 0, B col 2 (B invertida)
        u = self._get_col("U", 0)
        f = self._get_col("F", 0)
        d = self._get_col("D", 0)
        b = self._get_col("B", 2)[::-1]  # invertir

        # Ciclo:
        # U <- B (invertido)
        self._set_col("U", 0, b)
        # F <- U
        self._set_col("F", 0, u)
        # D <- F
        self._set_col("D", 0, f)
        # B <- D (invertir al guardar)
        self._set_col("B", 2, d[::-1])


    def _move_F(self):
        # Rotar cara F clockwise
        self.state["F"] = self._rotate_face_cw(self.state["F"])

        # Afecta: U fila 2, R col 0, D fila 0, L col 2
        u = self._get_row("U", 2)
        r = self._get_col("R", 0)
        d = self._get_row("D", 0)
        l = self._get_col("L", 2)

        # Convención estándar (con inversiones necesarias)
        # U row2 <- L col2 (reversa)
        self._set_row("U", 2, l[::-1])
        # R col0 <- U row2 (old)
        self._set_col("R", 0, u)
        # D row0 <- R col0 (old) (reversa)
        self._set_row("D", 0, r[::-1])
        # L col2 <- D row0 (old)
        self._set_col("L", 2, d)


    def _move_B(self):
        # Rotar cara B clockwise
        self.state["B"] = self._rotate_face_cw(self.state["B"])

        # Afecta: U fila 0, R col 2, D fila 2, L col 0
        u = self._get_row("U", 0)
        r = self._get_col("R", 2)
        d = self._get_row("D", 2)
        l = self._get_col("L", 0)

        # Convención estándar (con inversiones)
        # U row0 <- R col2
        self._set_row("U", 0, r)
        # L col0 <- U row0 (old) (reversa)
        self._set_col("L", 0, u[::-1])
        # D row2 <- L col0 (old)
        self._set_row("D", 2, l)
        # R col2 <- D row2 (old) (reversa)
        self._set_col("R", 2, d[::-1])


