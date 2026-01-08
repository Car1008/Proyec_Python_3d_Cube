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
        after = c.to_hashable()
        self.assertEqual(before, after)

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


if __name__ == "__main__":
    unittest.main()
