import unittest

from planning.hierarchy import Task, DecompositionMethod
from planning.hierarchical_engine import (
    HierarchicalMethod,
    HierarchicalPlanner,
    resolve_task_dependencies,
)


class HierarchicalEngineTests(unittest.TestCase):
    def test_records_parent_child_decomposition(self):
        result = HierarchicalPlanner().plan(
            [Task("root", "mission")],
            [
                DecompositionMethod(
                    "m1", "mission",
                    (Task("a", "sense", True), Task("b", "move", True)),
                )
            ],
        )
        self.assertEqual(result.ordered_task_ids, ("a", "b"))
        self.assertEqual(result.decomposition_trace[0].parent_task_id, "root")
        self.assertEqual(
            result.decomposition_trace[0].child_task_ids, ("a", "b")
        )

    def test_context_selects_applicable_method(self):
        methods = [
            HierarchicalMethod(
                DecompositionMethod("indoor", "navigate", (Task("i", "indoor", True),), 10),
                {"environment": "indoor"},
            ),
            HierarchicalMethod(
                DecompositionMethod("outdoor", "navigate", (Task("o", "outdoor", True),), 5),
                {"environment": "outdoor"},
            ),
        ]
        result = HierarchicalPlanner().plan(
            [Task("root", "navigate")],
            methods,
            context={"environment": "outdoor"},
        )
        self.assertEqual(result.ordered_task_ids, ("o",))

    def test_no_applicable_context_method_rejected(self):
        method = HierarchicalMethod(
            DecompositionMethod("indoor", "navigate", (Task("i", "indoor", True),)),
            {"environment": "indoor"},
        )
        with self.assertRaises(ValueError):
            HierarchicalPlanner().plan(
                [Task("root", "navigate")],
                [method],
                context={"environment": "outdoor"},
            )

    def test_dependency_order(self):
        tasks = [
            Task("a", "first", True),
            Task("b", "second", True),
            Task("c", "third", True),
        ]
        result = resolve_task_dependencies(
            tasks, {"c": ["a"], "b": ["a"]}
        )
        self.assertEqual(result[0], "a")
        self.assertEqual(set(result[1:]), {"b", "c"})

    def test_dependency_cycle_rejected(self):
        tasks = [Task("a", "A", True), Task("b", "B", True)]
        with self.assertRaises(ValueError):
            resolve_task_dependencies(tasks, {"a": ["b"], "b": ["a"]})

    def test_unknown_dependency_rejected(self):
        tasks = [Task("a", "A", True)]
        with self.assertRaises(ValueError):
            resolve_task_dependencies(tasks, {"a": ["missing"]})

    def test_node_limit_enforced(self):
        with self.assertRaises(ValueError):
            HierarchicalPlanner(max_nodes=1).plan(
                [Task("root", "mission")],
                [
                    DecompositionMethod(
                        "m1", "mission", (Task("a", "sense", True),)
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
