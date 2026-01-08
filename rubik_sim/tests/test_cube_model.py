# rubik_sim/tests/test_cube_model.py
import unittest
from rubik_sim.core import CubeModel


class TestCubeModel(unittest.TestCase):
    def test_starts_solved(self):
        c = CubeModel()
        self.assertTrue(c.is_solved())

    def test_U_then_Uprime_returns(self):
        c = CubeModel()
        before = c.to_hashable()
        c.apply_move("U")
        c.apply_move("U'")
        self.assertEqual(before, c.to_hashable())

    def test_U2_equals_two_U(self):
        c1 = CubeModel()
        c2 = CubeModel()
        c1.apply_move("U2")
        c2.apply_move("U")
        c2.apply_move("U")
        self.assertEqual(c1.to_hashable(), c2.to_hashable())

    def test_D_then_Dprime_returns(self):
        c = CubeModel()
        before = c.to_hashable()
        c.apply_move("D")
        c.apply_move("D'")
        self.assertEqual(before, c.to_hashable())

    def test_D2_equals_two_D(self):
        c1 = CubeModel()
        c2 = CubeModel()
        c1.apply_move("D2")
        c2.apply_move("D")
        c2.apply_move("D")
        self.assertEqual(c1.to_hashable(), c2.to_hashable())
        
    def test_R_then_Rprime_returns(self):
        c = CubeModel()
        before = c.to_hashable()
        c.apply_move("R")
        c.apply_move("R'")
        self.assertEqual(before, c.to_hashable())

    def test_L_then_Lprime_returns(self):
        c = CubeModel()
        before = c.to_hashable()
        c.apply_move("L")
        c.apply_move("L'")
        self.assertEqual(before, c.to_hashable())
        
    def test_color_counts_remain_constant(self):
        c = CubeModel()
        # aplica varios movimientos
        c.apply_sequence("R U R' U' L D L' D' U2 R2")

        flat = []
        for face in c.FACES:
            flat.extend(c.state[face])

        # Cada color debe aparecer 9 veces
        for color in ["W", "Y", "O", "R", "G", "B"]:
            self.assertEqual(flat.count(color), 9)


if __name__ == "__main__":
    unittest.main()
