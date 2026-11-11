import subprocess
import tempfile
import unittest
from pathlib import Path

from automation.git_sync import Git, signed_commit, verify_robot, update_tree
from automation.run_sync import is_forward


class GitSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '--bare', str(self.root)], capture_output=True, check=True)
        self.git = Git(self.root)
        self.empty = self.git.run('mktree', data='')
        self.base = self.git.run('commit-tree', self.empty, data='initial\n')
        self.key = 'test-key'

    def tearDown(self):
        self.tmp.cleanup()

    def test_signed_bot_commit_is_verifiable(self):
        tree = update_tree(self.git, self.base, [{'path': 'Resources/one', 'new': 'b' * 40}])
        head = signed_commit(self.git, tree, [self.base], self.key)
        verify_robot(self.git, self.base, head, ['Resources/one'], self.key)
        self.assertEqual(self.git.run('ls-tree', head, 'Resources/one'), '160000 commit ' + 'b' * 40 + '\tResources/one')

    def test_manual_commit_with_a_forged_marker_is_rejected(self):
        head = self.git.run('commit-tree', self.empty, '-p', self.base, data='chore: sync resource references\n\nSync-Signature: fake\n')
        with self.assertRaises(RuntimeError):
            verify_robot(self.git, self.base, head, ['Resources/one'], self.key)

    def test_signed_modification_outside_allowlist_is_rejected(self):
        tree = update_tree(self.git, self.base, [{'path': 'Libraries/other', 'new': 'b' * 40}])
        head = signed_commit(self.git, tree, [self.base], self.key)
        with self.assertRaises(RuntimeError):
            verify_robot(self.git, self.base, head, ['Resources/one'], self.key)

    def test_multiple_bot_updates_accumulate_only_gitlinks(self):
        tree = update_tree(self.git, self.base, [{'path': 'Resources/one', 'new': 'a' * 40}])
        first = signed_commit(self.git, tree, [self.base], self.key)
        tree2 = update_tree(self.git, first, [{'path': 'Resources/two', 'new': 'b' * 40}])
        second = signed_commit(self.git, tree2, [first], self.key)
        verify_robot(self.git, self.base, second, ['Resources/one', 'Resources/two'], self.key)
        self.assertEqual(len(self.git.run('ls-tree', '-r', second).splitlines()), 2)

    def test_forward_ancestry_uses_all_merge_parents(self):
        parents = {'c': ['a', 'b'], 'b': [], 'a': []}
        self.assertTrue(is_forward('b', 'c', lambda sha: parents[sha]))
        self.assertFalse(is_forward('c', 'b', lambda sha: parents[sha]))

    def test_new_target_commit_does_not_invalidate_signed_robot_history(self):
        tree = update_tree(self.git, self.base, [{'path': 'Resources/one', 'new': 'a' * 40}])
        bot = signed_commit(self.git, tree, [self.base], self.key)
        other = update_tree(self.git, self.base, [{'path': 'Libraries/other', 'new': 'b' * 40}])
        target = self.git.run('commit-tree', other, '-p', self.base, data='human target update\n')
        verify_robot(self.git, target, bot, ['Resources/one'], self.key)

    def test_failed_parent_lookup_does_not_approve_update(self):
        def fail(sha):
            raise RuntimeError('unavailable')
        with self.assertRaises(RuntimeError):
            is_forward('a', 'b', fail)


if __name__ == '__main__':
    unittest.main()
