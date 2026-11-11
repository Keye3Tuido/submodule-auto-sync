import unittest

from automation.reconcile import parse_gitmodules, build_update_plan


class ReconcileTests(unittest.TestCase):
    def test_only_explicit_branch_entries_are_candidates(self):
        text = """[submodule \"one\"]
    path = Resources/one
    url = https://gitee.com/a/one.git
    branch = release/v1
[submodule \"two\"]
    path = Resources/two
    url = https://gitee.com/a/two.git
"""
        entries = parse_gitmodules(text)
        self.assertEqual(entries[0]["branch"], "release/v1")
        self.assertEqual(entries[1]["branch"], "")

    def test_plan_contains_only_changed_allowed_gitlinks(self):
        entries = [{
            "path": "Resources/one",
            "url": "https://gitee.com/a/one.git",
            "branch": "release/v1",
        }]
        plan = build_update_plan(entries, {"Resources/one": "a" * 40}, {"Resources/one": "b" * 40})
        self.assertEqual(plan, [{"path": "Resources/one", "old": "a" * 40, "new": "b" * 40, "branch": "release/v1"}])

    def test_plan_rejects_unknown_path(self):
        entries = [{"path": "Resources/one", "url": "u", "branch": "release/v1"}]
        with self.assertRaises(ValueError):
            build_update_plan(entries, {"Resources/one": "a" * 40}, {"Resources/other": "b" * 40})


if __name__ == "__main__":
    unittest.main()
