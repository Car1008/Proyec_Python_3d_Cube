import unittest
from rubik_sim.core.cube_model import CubeModel
from rubik_sim.solve.iddfs_solver import iddfs_solve

class TestSolver(unittest.TestCase):
    def test_solver_small_scramble(self):
        c = CubeModel()
        c.apply_sequence("R U R' U'")
        sol = iddfs_solve(c, max_depth=6)
        self.assertIsNotNone(sol)
        c.apply_sequence(" ".join(sol))
        self.assertTrue(c.is_solved())

if __name__ == "__main__":
    unittest.main()
