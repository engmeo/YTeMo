import unittest
from planning.hierarchy import Task, DecompositionMethod, decompose_tasks
from planning.temporal import TemporalConstraint, solve_temporal_network
from planning.constraints import BinaryConstraint, solve_constraints

class HTNTests(unittest.TestCase):
    def test_decomposes_to_primitive_tasks(self):
        result = decompose_tasks([Task("root", "mission")], [
            DecompositionMethod("m1", "mission", (Task("a", "sense", True), Task("b", "move", True)))
        ])
        self.assertEqual([t.task_id for t in result.primitive_tasks], ["a", "b"])
        self.assertEqual(result.applied_methods, ("m1",))
    def test_priority_is_deterministic(self):
        result = decompose_tasks([Task("root", "mission")], [
            DecompositionMethod("low", "mission", (Task("l", "low", True),), 1),
            DecompositionMethod("high", "mission", (Task("h", "high", True),), 2),
        ])
        self.assertEqual(result.primitive_tasks[0].task_id, "h")
    def test_missing_method_and_cycle_rejected(self):
        with self.assertRaises(ValueError):
            decompose_tasks([Task("x", "unknown")], [])
        with self.assertRaises(ValueError):
            decompose_tasks([Task("x", "loop")], [DecompositionMethod("loop-method", "loop", (Task("y", "loop"),))])
    def test_duplicate_primitive_ids_rejected(self):
        with self.assertRaises(ValueError):
            decompose_tasks([Task("x", "a", True), Task("x", "b", True)], [])

class TemporalTests(unittest.TestCase):
    def test_consistent_network(self):
        result = solve_temporal_network(["start", "finish"], [TemporalConstraint("finish", "start", -2), TemporalConstraint("start", "finish", 5)])
        self.assertTrue(result.consistent)
    def test_negative_cycle_detected(self):
        result = solve_temporal_network(["a", "b"], [TemporalConstraint("a", "b", 1), TemporalConstraint("b", "a", -2)])
        self.assertFalse(result.consistent)
    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            solve_temporal_network(["a"], [TemporalConstraint("a", "b", 1)])

class ConstraintTests(unittest.TestCase):
    def test_solves_binary_csp(self):
        result = solve_constraints({"a": [1, 2], "b": [1, 2]}, [BinaryConstraint("a", "b", lambda a, b: a != b)])
        self.assertTrue(result.solved)
        self.assertNotEqual(result.assignment["a"], result.assignment["b"])
    def test_unsatisfiable_csp(self):
        result = solve_constraints({"a": [1], "b": [1]}, [BinaryConstraint("a", "b", lambda a, b: a != b)])
        self.assertFalse(result.solved)
    def test_unknown_variable_rejected(self):
        with self.assertRaises(ValueError):
            solve_constraints({"a": [1]}, [BinaryConstraint("a", "b", lambda a, b: True)])

if __name__ == "__main__":
    unittest.main()
