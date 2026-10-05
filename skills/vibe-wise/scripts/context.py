"""Locate project learning notes without writing or loading their contents."""

import argparse

import json
from pathlib import Path
import re
import sys


# Find the installed plugin from this script, not from the user's project folder.
SKILL_ROOT = Path(__file__).resolve().parents[1]


def profile_is_active(path):
    """Check activation without copying learner notes into hook output."""
    # A linked profile could point outside the selected project's learning notes.
    if path.is_symlink() or not path.is_file():
        return False
    has_content = False
    try:
        with path.open(encoding="utf-8") as stream:
            # Scan the whole file: a paused marker can appear after a long profile.
            # Reading line by line avoids loading all its contents into memory.
            for line in stream:
                has_content = has_content or bool(line.strip())
                if re.fullmatch(r"Learning mode:\s*paused\s*", line, re.IGNORECASE):
                    return False
    except (OSError, UnicodeError):
        # Missing, unreadable, or invalid text isn't evidence of active learning.
        return False
    # Older profiles may lack an explicit mode. Preserve their restoration behavior.
    return has_content


def state_directory(cwd):
    """Find the nearest notes directory without crossing a Git project boundary."""
    # Starting in a source subdirectory should still find the project's notes.
    for directory in (cwd, *cwd.parents):
        # Prefer the new name at the nearest location; keep legacy notes in place.
        for name in (".vibe-wise", ".sensible-vibes"):
            state = directory / name
            if state.exists() or state.is_symlink():
                # Stop even if this candidate is invalid. Falling back to a parent
                # could silently load a different project's learner profile.
                return state if state.is_dir() and not state.is_symlink() else None
        # A .git file is a worktree boundary too. Never borrow another repo's state.
        if (directory / ".git").exists():
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
        for directory in (path, *path.parents):
            for name in (".vibe-wise", ".sensible-vibes"):
                candidate = directory / name
                if candidate.exists() or candidate.is_symlink():
                    raise ValueError("Learning state must be a real directory: " + str(candidate))
            if (directory / ".git").exists():
                break
        return {"status": "no_notes", "cwd": str(path)}
    for name in ("profile.md", "progress.md", "project-map.md"):
        note = state / name
        if note.is_symlink() or (note.exists() and not note.is_file()):
            raise ValueError("Learning note must be a regular file: " + str(note))
    profile = state / "profile.md"
    if profile.exists():
        # Surface invalid encoding and I/O failures instead of calling corrupt state paused.
        with profile.open(encoding="utf-8") as stream:
            for _ in stream:
                pass
    return {
        "status": "active" if profile_is_active(profile) else "inactive",
        "state": str(state),
        "guide": str(SKILL_ROOT / "SKILL.md"),
        "files": [name for name in ("profile.md", "progress.md", "project-map.md")
                  if (state / name).is_file()],
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
