"""Exercise the installed context CLI without relying on lifecycle hooks."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/vibe-wise/scripts/context.py"
spec = importlib.util.spec_from_file_location("vibe_wise_context", SCRIPT)
context_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_module)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vibe-wise-context-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        (self.project / ".git").mkdir()

    def notes(self, project=None, mode="active", legacy=False):
        state = (project or self.project) / (".sensible-vibes" if legacy else ".vibe-wise")
        state.mkdir()
        (state / "profile.md").write_text(f"Learning mode: {mode}\nOnboarding: complete\n")
        (state / "progress.md").write_text("## Pending decision\nAwaiting implementation\n")
        (state / "project-map.md").write_text("# Map\nprivate learning content\n")
        return state

    def run_context(self, cwd=None, ok=True):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--cwd", str(cwd or self.project)],
            capture_output=True, text=True, cwd=self.root, timeout=5,
        )
        self.assertEqual(result.returncode, 0 if ok else 1, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_fresh_project_does_not_create_state(self):
        self.assertEqual(self.run_context()["status"], "no_notes")
        self.assertEqual(list(self.project.iterdir()), [self.project / ".git"])

    def test_active_nested_project_returns_paths_without_note_content_or_writes(self):
        state = self.notes()
        nested = self.project / "src"
        nested.mkdir()
        before = {p.name: p.read_bytes() for p in state.iterdir()}
        result = self.run_context(nested)
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["state"], str(state))
        self.assertTrue(Path(result["guide"]).is_file())
        self.assertEqual(set(result["files"]), set(before))
        self.assertNotIn("Awaiting implementation", json.dumps(result))
        self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})

    def test_no_git_and_legacy_notes_keep_their_location(self):
        project = self.root / "no git"
        project.mkdir()
        state = self.notes(project, legacy=True)
        self.assertEqual(self.run_context(project)["state"], str(state))
        self.assertFalse((project / ".vibe-wise").exists())

    def test_nearest_state_and_new_name_take_precedence(self):
        self.notes(legacy=True)
        state = self.notes(mode="paused")
        self.assertEqual(self.run_context()["status"], "inactive")
        child = self.project / "package"
        child.mkdir()
        nearest = self.notes(child, legacy=True)
        self.assertEqual(self.run_context(child)["state"], str(nearest))
        self.assertEqual(self.run_context()["state"], str(state))

    def test_git_directory_and_worktree_file_stop_parent_lookup(self):
        self.notes()
        for name, as_file in (("nested repo", False), ("worktree", True)):
            child = self.project / name
            child.mkdir()
            if as_file:
                (child / ".git").write_text("gitdir: /another/repo/.git/worktrees/test")
            else:
                (child / ".git").mkdir()
            self.assertEqual(self.run_context(child)["status"], "no_notes")

    def test_broken_git_symlink_stops_parent_lookup(self):
        state = self.notes()
        child = self.project / "broken worktree"
        child.mkdir()
        (child / ".git").symlink_to(self.root / "missing-gitdir")
        self.assertEqual(self.run_context(child)["status"], "no_notes")
        self.assertEqual(self.run_context()["state"], str(state))

    def test_missing_companion_files_do_not_disable_learning(self):
        state = self.notes()
        (state / "project-map.md").unlink()
        (state / "progress.md").unlink()
        result = self.run_context()
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["files"], ["profile.md"])

    def test_paused_marker_anywhere_in_large_profile_is_respected(self):
        state = self.notes()
        (state / "profile.md").write_text("Older preference\n" * 10000 + "Learning mode: paused\n")
        self.assertEqual(self.run_context()["status"], "inactive")

    def test_legacy_profile_without_status_still_activates(self):
        state = self.notes()
        (state / "profile.md").write_text("# Learner Profile\nExperience: Beginner\n")
        self.assertEqual(self.run_context()["status"], "active")

    def test_empty_profile_does_not_activate(self):
        state = self.notes()
        (state / "profile.md").write_text(" \n\t")
        self.assertEqual(self.run_context()["status"], "inactive")

    def test_invalid_cwd_and_invalid_encoding_report_errors(self):
        self.assertEqual(self.run_context("relative", ok=False)["status"], "error")
        self.assertEqual(self.run_context(self.root / "missing", ok=False)["status"], "error")
        state = self.notes()
        (state / "profile.md").write_bytes(b"\xff")
        self.assertEqual(self.run_context(ok=False)["status"], "error")

    def test_paused_profile_with_invalid_trailing_text_reports_error(self):
        state = self.notes(mode="paused")
        (state / "profile.md").write_bytes(b"Learning mode: paused\n" + b"older note\n" * 1000 + b"\xff")
        self.assertEqual(self.run_context(ok=False)["status"], "error")

    def test_profile_read_failure_is_not_treated_as_paused(self):
        state = self.notes()
        with patch.object(Path, "open", side_effect=PermissionError("profile unavailable")):
            with self.assertRaises(PermissionError):
                context_module.profile_is_active(state / "profile.md")

    def test_inaccessible_candidate_does_not_fall_back_to_parent_notes(self):
        self.notes()
        child = self.project / "restricted package"
        child.mkdir()
        lstat = Path.lstat

        def deny_child_state(path):
            if path == child / ".vibe-wise":
                raise PermissionError("state unavailable")
            return lstat(path)

        with patch.object(Path, "lstat", deny_child_state):
            with self.assertRaises(PermissionError):
                context_module.inspect(child)

    def test_linked_state_does_not_follow_or_fall_back(self):
        self.notes(legacy=True)
        (self.project / ".vibe-wise").symlink_to(self.root / "missing")
        self.assertEqual(self.run_context(ok=False)["status"], "error")

    def test_file_at_state_path_does_not_fall_back_to_legacy_notes(self):
        self.notes(legacy=True)
        (self.project / ".vibe-wise").write_text("invalid state path\n")
        self.assertEqual(self.run_context(ok=False)["status"], "error")

    def test_linked_and_non_regular_notes_report_errors(self):
        state = self.notes()
        for name in ("profile.md", "progress.md", "project-map.md"):
            original = (state / name).read_bytes()
            (state / name).unlink()
            (state / name).symlink_to(self.root / "missing")
            self.assertEqual(self.run_context(ok=False)["status"], "error")
            (state / name).unlink()
            (state / name).mkdir()
            self.assertEqual(self.run_context(ok=False)["status"], "error")
            (state / name).rmdir()
            (state / name).write_bytes(original)


if __name__ == "__main__":
    unittest.main()
