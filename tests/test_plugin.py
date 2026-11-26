import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "scripts"))

import plugin  # noqa: E402


class PluginToolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp())
        self.root = self.workspace / "plugin"
        shutil.copytree(REPOSITORY, self.root, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def messages(self) -> list[str]:
        return [message for _, message in plugin.run_check(self.root, use_cli=False).findings]

    def edit_json(self, relative: str, change) -> None:
        path = self.root / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_repository_passes_the_check(self) -> None:
        self.assertEqual([], plugin.run_check(self.root, use_cli=False).findings)

    def test_build_writes_a_zip_with_a_named_root_folder(self) -> None:
        archive = plugin.run_build(self.root, use_cli=False)

        with zipfile.ZipFile(archive) as zip_file:
            entries = zip_file.namelist()
        self.assertEqual(f"m2immoneuf-{json.loads((self.root / plugin.CLAUDE_MANIFEST).read_text())['version']}.zip", archive.name)
        self.assertIn("m2immoneuf/plugin.json", entries)
        self.assertIn("m2immoneuf/mcp.json", entries)
        self.assertIn("m2immoneuf/assets/logo.png", entries)
        self.assertTrue(any(entry.startswith("m2immoneuf/skills/") and entry.endswith("SKILL.md") for entry in entries))
        self.assertFalse(any("README" in entry or ".claude-plugin" in entry or "scripts" in entry for entry in entries))

    def test_bump_updates_both_manifests(self) -> None:
        archive = plugin.run_build(self.root, bump="minor", use_cli=False)

        versions = {
            json.loads((self.root / relative).read_text())["version"]
            for relative in (plugin.CLAUDE_MANIFEST, plugin.OPENAI_MANIFEST)
        }
        self.assertEqual(1, len(versions))
        self.assertIn(versions.pop(), archive.name)

    def test_existing_zip_needs_force(self) -> None:
        plugin.run_build(self.root, use_cli=False)

        with self.assertRaises(SystemExit):
            plugin.run_build(self.root, use_cli=False)
        plugin.run_build(self.root, force=True, use_cli=False)

    def test_versions_must_match_between_manifests(self) -> None:
        self.edit_json(plugin.OPENAI_MANIFEST, lambda data: data.update(version="9.9.9"))

        self.assertTrue(any("differs between" in message for message in self.messages()))

    def test_remote_mcp_server_needs_a_supported_type(self) -> None:
        self.edit_json(".mcp.json", lambda data: data["mcpServers"]["m2immoneuf"].update(type="streamable-http"))

        self.assertTrue(any("needs type http" in message for message in self.messages()))

    def test_remote_mcp_server_must_use_https(self) -> None:
        self.edit_json(".mcp.json", lambda data: data["mcpServers"]["m2immoneuf"].update(url="http://example.test/mcp"))

        self.assertTrue(any("https://" in message for message in self.messages()))

    def test_invalid_name_blocks(self) -> None:
        self.edit_json(plugin.CLAUDE_MANIFEST, lambda data: data.update(name="M2 Immoneuf"))

        self.assertTrue(any(message.startswith("name:") for message in self.messages()))

    def test_short_readme_blocks(self) -> None:
        (self.root / "README.md").write_text("Too short.", encoding="utf-8")

        self.assertTrue(any("README too short" in message for message in self.messages()))

    def test_missing_license_blocks(self) -> None:
        (self.root / "LICENSE").unlink()
        self.edit_json(plugin.CLAUDE_MANIFEST, lambda data: data.pop("license"))

        self.assertTrue(any("License missing" in message for message in self.messages()))

    def test_junk_file_and_symlink_block(self) -> None:
        (self.root / "assets" / ".DS_Store").write_text("junk", encoding="utf-8")
        (self.root / "assets" / "link.png").symlink_to(self.root / "assets" / "logo.png")

        messages = self.messages()
        self.assertTrue(any("junk file" in message for message in messages))
        self.assertTrue(any("symbolic link" in message for message in messages))

    def test_missing_logo_blocks(self) -> None:
        (self.root / "assets" / "logo.png").unlink()

        self.assertTrue(any("missing file" in message for message in self.messages()))

    def test_credential_blocks(self) -> None:
        (self.root / "skills" / "leak.txt").write_text('{"api_key": "abcdefghijklmnop1234"}', encoding="utf-8")

        self.assertTrue(any("credential" in message for message in self.messages()))

    def test_skill_without_description_warns(self) -> None:
        skill = self.root / "skills" / "consulter-le-catalogue" / "SKILL.md"
        skill.write_text("---\nname: consulter-le-catalogue\n---\n\nBody\n", encoding="utf-8")

        self.assertTrue(any("description missing" in message for message in self.messages()))


if __name__ == "__main__":
    unittest.main()
