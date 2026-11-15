"""Exercise the opt-in plugin SessionStart hook as a standalone command."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
HOOKS_CONFIG = ROOT / "hooks" / "hooks.json"
SOURCES = ("startup", "resume", "clear", "compact")


class SessionStartHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vibe-wise-hook-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.state = self.project / ".vibe-wise"
        self.plugin_root = self.root / "plugin installation"
        self.plugin_root.mkdir()
        shutil.copytree(ROOT / "skills", self.plugin_root / "skills")
        shutil.copytree(ROOT / "hooks", self.plugin_root / "hooks")
        self.hook_script = self.plugin_root / "hooks" / "session_start.py"

    def make_notes(self, mode="active"):
        self.state.mkdir(exist_ok=True)
        (self.state / "profile.md").write_text(
            f"Learning mode: {mode}\nprivate-profile-body-marker\n", encoding="utf-8"
        )
        (self.state / "progress.md").write_text(
            "private-progress-body-marker\n", encoding="utf-8"
        )
        (self.state / "project-map.md").write_text(
            "private-project-map-body-marker\n", encoding="utf-8"
        )

    def event(self, source="startup", **extra):
        return {
            "hook_event_name": "SessionStart",
            "source": source,
            "cwd": str(self.project),
            **extra,
        }

    def run_hook(self, payload, *, raw=None, env=None):
        environment = os.environ.copy()
        environment["PLUGIN_ROOT"] = str(self.plugin_root)
        if env:
            environment.update(env)
        if raw is None:
            raw = json.dumps(payload).encode("utf-8")
        result = subprocess.run(
            [sys.executable, str(self.hook_script)], input=raw,
            capture_output=True, cwd=self.root, env=environment, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(result.stderr, b"")
        return result.stdout.decode("utf-8")

    def project_snapshot(self):
        snapshot = {}
        for path in self.project.rglob("*"):
            relative = path.relative_to(self.project)
            if path.is_dir():
                snapshot[relative] = ("directory", path.stat().st_mtime_ns)
            elif path.is_file():
                snapshot[relative] = (
                    "file", path.read_bytes(), path.stat().st_mtime_ns
                )
            else:
                snapshot[relative] = ("other", path.lstat().st_mode)
        return snapshot

    def test_plugin_registers_only_the_supported_session_start_sources(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        config = json.loads(HOOKS_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(manifest["hooks"], "./hooks/hooks.json")
        self.assertEqual(set(config["hooks"]), {"SessionStart"})
        groups = config["hooks"]["SessionStart"]
        self.assertEqual(len(groups), 1)
        group = groups[0]
        matcher = re.compile(group["matcher"])
        self.assertEqual({source for source in SOURCES if matcher.fullmatch(source)}, set(SOURCES))
        self.assertIsNone(matcher.fullmatch("fork"))
        self.assertEqual(len(group["hooks"]), 1)
        handler = group["hooks"][0]
        self.assertEqual(handler["type"], "command")
        self.assertIn('python3 "${PLUGIN_ROOT}/hooks/session_start.py"', handler["command"])
        self.assertIn('py -3 "${PLUGIN_ROOT}/hooks/session_start.py"', handler["commandWindows"])
        self.assertNotIn("statusMessage", handler)

    def test_active_state_restores_for_each_registered_source(self):
        self.make_notes()
        for source in SOURCES:
            with self.subTest(source=source):
                output = self.run_hook(self.event(source))
                parsed = json.loads(output)
                context = parsed["hookSpecificOutput"]["additionalContext"]
                self.assertEqual(parsed["hookSpecificOutput"]["hookEventName"], "SessionStart")
                self.assertIn(str(self.plugin_root / "skills/vibe-wise/SKILL.md"), context)
                self.assertIn(str(self.state), context)
                self.assertIn("profile.md, progress.md, project-map.md", context)
                self.assertIn("never approves pending work", context)

    def test_paused_and_missing_state_are_silent(self):
        self.assertEqual(self.run_hook(self.event()), "")
        self.assertFalse(self.state.exists())
        self.make_notes(mode="paused")
        self.assertEqual(self.run_hook(self.event("resume")), "")

    def test_malformed_unsupported_and_oversized_events_are_silent(self):
        self.make_notes()
        malformed_events = (
            self.event("fork"),
            self.event("unexpected"),
            {**self.event(), "hook_event_name": "SessionEnd"},
            {"hook_event_name": "SessionStart", "source": "startup"},
            {**self.event(), "cwd": 42},
            {**self.event(), "cwd": "relative/project"},
        )
        for payload in malformed_events:
            with self.subTest(payload=payload):
                self.assertEqual(self.run_hook(payload), "")
        for raw in (b"{", b"[]", b"\xff", b'{"source":NaN}'):
            with self.subTest(raw=raw):
                self.assertEqual(self.run_hook(None, raw=raw), "")
        self.assertEqual(self.run_hook(None, raw=b" " * (64 * 1024 + 1)), "")

    def test_invalid_state_fails_open_without_context(self):
        self.make_notes()
        (self.state / "profile.md").write_bytes(b"\xff malformed profile\n")
        self.assertEqual(self.run_hook(self.event()), "")

    def test_output_has_only_instructions_and_paths_and_state_is_unchanged(self):
        self.make_notes()
        before = self.project_snapshot()
        transcript = self.root / "transcript.jsonl"
        transcript.write_text("private-transcript-body-marker\n", encoding="utf-8")
        output = self.run_hook(
            self.event(transcript_path=str(transcript)),
        )
        self.assertTrue(output)
        for marker in (
            "private-profile-body-marker",
            "private-progress-body-marker",
            "private-project-map-body-marker",
            "private-transcript-body-marker",
        ):
            self.assertNotIn(marker, output)
        self.assertEqual(before, self.project_snapshot())
        self.assertFalse(list(self.plugin_root.rglob("__pycache__")))

    def test_helper_import_does_not_write_plugin_bytecode(self):
        self.make_notes()
        self.run_hook(self.event())
        self.assertFalse(list(self.plugin_root.rglob("__pycache__")))

    def test_missing_plugin_root_is_silent(self):
        self.make_notes()
        self.assertEqual(self.run_hook(self.event(), env={"PLUGIN_ROOT": ""}), "")


if __name__ == "__main__":
    unittest.main()
