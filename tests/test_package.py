"""Validate that the distributed skill works outside its source repository."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/vibe-wise"


class PackageTests(unittest.TestCase):
    def test_manifest_resolves_skill_and_license_is_preserved(self):
        manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "vibe-wise-codex")
        self.assertEqual(manifest["license"], "MIT")
        skill_path = manifest["skills"]
        self.assertTrue(skill_path.startswith("./"))
        self.assertNotIn("..", Path(skill_path).parts)
        self.assertTrue((ROOT / skill_path / "vibe-wise/SKILL.md").is_file())
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (SKILL / "LICENSE").read_bytes())
        self.assertIn("Copyright (c) 2026 Noah Kim", (SKILL / "LICENSE").read_text())
        self.assertFalse((ROOT / ".claude-plugin").exists())
        self.assertFalse((ROOT / "hooks").exists())

    def test_relative_instruction_links_exist(self):
        for path in (SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))):
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if not link.startswith("https://"):
                    target = (path.parent / link).resolve()
                    self.assertTrue(target.is_relative_to(SKILL.resolve()))
                    self.assertTrue(target.is_file(), str(target))

    def test_distribution_metadata_and_icons_are_complete(self):
        manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        interface = manifest["interface"]
        for field, limit in (("displayName", 30), ("shortDescription", 30),
                             ("longDescription", 4000), ("developerName", 80)):
            value = interface[field]
            self.assertIsInstance(value, str)
            self.assertTrue(value.strip())
            self.assertLessEqual(len(value), limit)
        self.assertEqual(interface["category"], "Productivity")
        self.assertIsInstance(interface["capabilities"], list)
        for field in ("logo", "composerIcon"):
            asset = interface[field]
            self.assertTrue(asset.startswith("./"))
            self.assertNotIn("..", Path(asset).parts)
            image = ROOT / asset
            self.assertTrue(image.is_file())
            data = image.read_bytes()
            self.assertLessEqual(len(data), 5 * 1024 * 1024)
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            self.assertEqual(width, height)
            self.assertGreaterEqual(width, 48)
            self.assertLessEqual(width, 4096)

    def test_independently_installed_skill_previews_and_resets_project_notes(self):
        with tempfile.TemporaryDirectory(prefix="vibe-wise-install-") as temp:
            base = Path(temp).resolve()
            install = base / "skill installation" / "vibe-wise"
            shutil.copytree(SKILL, install)
            project = base / "target project"
            project.mkdir()
            (project / ".git").write_text("gitdir: /other/repository/worktrees/example")
            state = project / ".vibe-wise"
            state.mkdir()
            originals = {
                "profile.md": b"Learning mode: active\nOnboarding: complete\n",
                "progress.md": b"## Pending decision\nAwaiting Design confirmation\n",
                "project-map.md": b"# Project Map\nVerified existing code\n",
            }
            for name, data in originals.items():
                (state / name).write_bytes(data)

            def run(script, *arguments):
                result = subprocess.run(
                    [sys.executable, "-B", str(install / "scripts" / script),
                     "--cwd", str(project), *arguments],
                    cwd=base, capture_output=True, text=True, check=True, timeout=5,
                )
                return json.loads(result.stdout)

            context = run("context.py")
            self.assertEqual(context["status"], "active")
            self.assertEqual(context["guide"], str(install / "SKILL.md"))
            preview = run("reset.py")
            self.assertEqual(preview["status"], "preview")
            reset = run("reset.py", "--confirm", preview["confirmation"])
            self.assertEqual(reset["status"], "reset")
            backup = Path(reset["backup"])
            self.assertEqual(originals, {name: (backup / name).read_bytes() for name in originals})
            self.assertIn("Onboarding: incomplete", (state / "profile.md").read_text())
            self.assertFalse((install / ".vibe-wise").exists())
            self.assertEqual(run("context.py")["status"], "active")


if __name__ == "__main__":
    unittest.main()
