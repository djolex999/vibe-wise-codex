"""Locate project learning notes without writing or emitting their contents."""

import argparse
import json
from pathlib import Path
import re
import stat
import sys


# Find the installed plugin from this script, not from the user's project folder.
SKILL_ROOT = Path(__file__).resolve().parents[1]


def profile_is_active(path):
    """Scan a validated profile without copying learner notes into the output."""
    has_content = False
    paused = False
    with path.open(encoding="utf-8") as stream:
        # Finish scanning even when paused so corrupt or unreadable state is reported.
        for line in stream:
            has_content = has_content or bool(line.strip())
            if re.fullmatch(r"Learning mode:\s*paused\s*", line, re.IGNORECASE):
                paused = True
    # Older profiles may lack an explicit mode. Preserve their restoration behavior.
    return has_content and not paused


def state_directory(cwd):
    """Find the nearest notes directory without crossing a Git project boundary."""
    # Starting in a source subdirectory should still find the project's notes.
    for directory in (cwd, *cwd.parents):
        # Prefer the new name at the nearest location; keep legacy notes in place.
        for name in (".vibe-wise", ".sensible-vibes"):
            state = directory / name
            try:
                mode = state.lstat().st_mode
            except FileNotFoundError:
                continue
            # Never hide invalid or inaccessible state and borrow a parent's notes.
            if not stat.S_ISDIR(mode):
                raise ValueError("Learning state must be a real directory: " + str(state))
            return state
        # A .git file is a worktree boundary too. Never borrow another repo's state.
        try:
            (directory / ".git").lstat()
        except FileNotFoundError:
            continue
        else:
            break
    return None


def inspect(cwd):
    """Return state metadata; missing notes never activate learning implicitly."""
    path = Path(cwd)
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("Use an existing absolute project working directory.")
    path = path.resolve()
    state = state_directory(path)
    if state is None:
        return {"status": "no_notes", "cwd": str(path)}
    files = []
    for name in ("profile.md", "progress.md", "project-map.md"):
        note = state / name
        try:
            mode = note.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(mode):
            raise ValueError("Learning note must be a regular file: " + str(note))
        files.append(name)
    active = "profile.md" in files and profile_is_active(state / "profile.md")
    return {
        "status": "active" if active else "inactive",
        "state": str(state),
        "guide": str(SKILL_ROOT / "SKILL.md"),
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.cwd)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "message": str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
