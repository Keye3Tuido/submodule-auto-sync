"""Pure planning helpers for gitlink reconciliation."""

import re


def parse_gitmodules(text):
    entries = []
    current = None
    for line in text.splitlines():
        section = re.match(r'^\s*\[submodule "([^"]+)"\]\s*$', line)
        if section:
            if current:
                entries.append(current)
            current = {"name": section.group(1), "path": "", "url": "", "branch": ""}
            continue
        match = re.match(r'^\s*(path|url|branch)\s*=\s*(.*?)\s*$', line)
        if current and match:
            current[match.group(1)] = match.group(2)
    if current:
        entries.append(current)
    return entries


def build_update_plan(entries, old_gitlinks, new_gitlinks):
    allowed = {entry["path"]: entry for entry in entries if entry.get("branch")}
    unknown = set(new_gitlinks) - set(allowed)
    if unknown:
        raise ValueError(f"unconfigured gitlink paths: {sorted(unknown)}")
    plan = []
    for path, new_sha in new_gitlinks.items():
        old_sha = old_gitlinks.get(path)
        if old_sha and old_sha != new_sha:
            plan.append({"path": path, "old": old_sha, "new": new_sha, "branch": allowed[path]["branch"]})
    return plan
