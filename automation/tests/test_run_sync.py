import os
import unittest

from automation.run_sync import load_config, plan_from_gitmodules, build_pr_body, pr_head


class RunSyncTests(unittest.TestCase):
    def test_config_requires_target_and_robot_branches(self):
        old = os.environ.pop("SYNC_CONFIG", None)
        try:
            with self.assertRaises(RuntimeError):
                load_config()
        finally:
            if old is not None:
                os.environ["SYNC_CONFIG"] = old

    def test_plan_filters_to_configured_paths(self):
        text = """[submodule \"one\"]
    path = Resources/one
    url = https://example.invalid/one.git
    branch = release/v1
[submodule \"two\"]
    path = Resources/two
    url = https://example.invalid/two.git
    branch = release/v1
"""
        plan = plan_from_gitmodules(text, {"Resources/one": "a" * 40}, {"Resources/one": "b" * 40}, {"allowed_paths": ["Resources/one"]})
        self.assertEqual([item["path"] for item in plan], ["Resources/one"])

    def test_pr_head_uses_owner_and_robot_branch(self):
        self.assertEqual(pr_head({"main_owner": "owner", "robot_branch": "bot/sync"}), "owner:bot/sync")

    def test_pr_body_contains_sha_mapping_without_urls(self):
        body = build_pr_body([{"path": "Resources/one", "old": "a" * 40, "new": "b" * 40, "branch": "release/v1"}])
        self.assertIn("Resources/one", body)
        self.assertIn("release/v1", body)
        self.assertIn("a" * 40, body)
        self.assertNotIn("http", body)


if __name__ == "__main__":
    unittest.main()
