import hashlib
import hmac
import os
import subprocess
import tempfile


class Git:
    def __init__(self, cwd, env=None):
        self.cwd = str(cwd)
        self.env = os.environ.copy() if env is None else env.copy()
        self.env.setdefault('GIT_AUTHOR_NAME', 'Submodule Auto Sync')
        self.env.setdefault('GIT_AUTHOR_EMAIL', 'sync@localhost')
        self.env.setdefault('GIT_COMMITTER_NAME', self.env['GIT_AUTHOR_NAME'])
        self.env.setdefault('GIT_COMMITTER_EMAIL', self.env['GIT_AUTHOR_EMAIL'])

    def run(self, *args, data=None):
        result = subprocess.run(["git", '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', *args], cwd=self.cwd, env=self.env, input=data, text=True, capture_output=True, check=True, timeout=180)
        return result.stdout.strip()


def update_tree(git, commit, updates):
    with tempfile.TemporaryDirectory() as directory:
        isolated = Git(git.cwd, {**git.env, 'GIT_INDEX_FILE': directory + '/index'})
        isolated.run('read-tree', commit)
        for item in updates:
            isolated.run('update-index', '--add', '--cacheinfo', '160000', item['new'], item['path'])
        return isolated.run('write-tree')


def signed_commit(git, tree, parents, key):
    payload = tree + "\n" + "\n".join(parents)
    signature = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    args = ["commit-tree", tree]
    for parent in parents:
        args += ["-p", parent]
    return git.run(*args, data=f"chore: update submodule references\n\nSubmodule-Auto-Sync: true\nSync-Signature: {signature}\n")


def verify_robot(git, base, head, allowed_paths, key):
    commits = git.run("rev-list", f"{base}..{head}").splitlines()
    for commit in commits:
        message = git.run("show", "-s", "--format=%B", commit)
        if "Submodule-Auto-Sync: true" not in message:
            raise RuntimeError("robot branch contains an unsigned manual commit")
        signature = next((line.split(":", 1)[1].strip() for line in message.splitlines() if line.startswith("Sync-Signature:")), "")
        tree = git.run("show", "-s", "--format=%T", commit)
        parents = git.run("show", "-s", "--format=%P", commit).split()
        payload = tree + "\n" + "\n".join(parents)
        expected = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise RuntimeError("robot branch signature is invalid")
        if not parents:
            raise RuntimeError('robot commit lacks a trusted parent')
        # Two-parent updates carry target changes through the last parent.
        changes = git.run('diff', '--raw', '--no-abbrev', '--no-renames', '-z', parents[-1], commit).split('\0')
        for offset in range(0, len(changes) - 1, 2):
            modes, path = changes[offset], changes[offset + 1]
            if not modes:
                continue
            if path not in allowed_paths or modes.split()[0:2] not in ([':160000', '160000'], [':000000', '160000']):
                raise RuntimeError('robot branch modifies data outside configured gitlinks')
