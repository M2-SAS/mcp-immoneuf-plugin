#!/usr/bin/env python3
"""Pre-submission check and ZIP builder for the M2Immoneuf plugin (standard library only).

    python3 scripts/plugin.py check
    python3 scripts/plugin.py build [--bump patch|minor|major] [--force] [--output dist]

`check` mirrors https://claude.com/docs/plugins/pre-submission-checklist.
`build` runs `check`, then writes <name>-<version>.zip for the OpenAI platform:
a <name>/ root folder with plugin.json, mcp.json, assets/ and skills/.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent
ROOT = REPOSITORY / "plugin"

CLAUDE_MANIFEST = ".claude-plugin/plugin.json"
OPENAI_MANIFEST = "openai/plugin.json"
OPENAI_MCP = "openai/mcp.json"

SKIPPED_DIRS = {".git", "dist", "__pycache__", "node_modules"}
JUNK_FILES = {".ds_store", "thumbs.db", "desktop.ini", "__macosx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
FONT_EXTENSIONS = {".woff", ".woff2", ".ttf", ".otf"}
RESERVED_NAMES = {"claude", "anthropic", "official", "plugin", "mcp", "test"}
WINDOWS_DEVICES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\"?\s*[:=]\s*\"[^\"\s${][^\"\s]{11,}\""),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


class Report:
    """Collects findings using the checklist vocabulary: blocks, held, warning."""

    def __init__(self) -> None:
        self.findings: list[tuple[str, str]] = []

    def block(self, message: str) -> None:
        self.findings.append(("BLOCKS", message))

    def hold(self, message: str) -> None:
        self.findings.append(("HELD", message))

    def warn(self, message: str) -> None:
        self.findings.append(("WARNING", message))

    @property
    def blocked(self) -> bool:
        return any(level == "BLOCKS" for level, _ in self.findings)

    def print(self) -> None:
        for level, message in self.findings:
            print(f"  [{level}] {message}")


def load_json(path: Path, report: Report, label: str) -> dict | None:
    if not path.is_file():
        report.block(f"{label}: file missing ({path.relative_to(ROOT)})")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        report.block(f"{label}: invalid JSON ({error})")
        return None
    if not isinstance(data, dict):
        report.block(f"{label}: expected a JSON object")
        return None
    return data


def project_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIPPED_DIRS for part in relative.parts):
            continue
        if path.is_symlink() or path.is_file():
            files.append(path)
    return files


def check_manifest(root: Path, report: Report) -> dict | None:
    manifest = load_json(root / CLAUDE_MANIFEST, report, "No plugin.json")
    if manifest is None:
        return None

    name = manifest.get("name", "")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?", name):
        report.block("name: lowercase letters, digits and hyphens only, up to 64 characters, starting and ending with a letter or digit")
    elif name in RESERVED_NAMES:
        report.block(f"name: '{name}' is a reserved word")
    elif re.search(r"claude|anthropic|official", name):
        report.hold("name: must not imply official status")

    for key in ("description", "author", "version"):
        if not manifest.get(key):
            report.warn(f"plugin.json: '{key}' is missing")
    for key in ("displayName",):
        value = manifest.get(key, "")
        if value and not value.isascii() and not value.isprintable():
            report.block(f"{key}: invisible or look-alike characters")
    if not isinstance(manifest.get("author", {}), dict) or not manifest.get("author", {}).get("name"):
        report.warn("author.name is missing")
    if "hooks" in manifest and manifest["hooks"] == "./hooks/hooks.json":
        report.warn("do not list hooks/hooks.json in plugin.json")
    if re.search(r"\bTODO\b", json.dumps(manifest)):
        report.block("plugin.json: TODO placeholder left")
    return manifest


def check_readme_and_license(root: Path, manifest: dict | None, report: Report) -> None:
    readme = next((d / "README.md" for d in (root, root.parent) if (d / "README.md").is_file()), root / "README.md")
    if not readme.is_file():
        report.block("README missing")
    else:
        text = re.sub(r"```.*?```", "", readme.read_text(encoding="utf-8"), flags=re.S)
        if len(re.findall(r"\S+", text)) < 40:
            report.block("README too short (at least 40 words outside code blocks)")

    has_license_file = any((d / name).is_file() for d in (root, root.parent) for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    if not has_license_file and not (manifest or {}).get("license"):
        report.block("License missing (LICENSE file or 'license' in plugin.json)")


def check_mcp(root: Path, report: Report) -> None:
    mcp = load_json(root / ".mcp.json", report, ".mcp.json")
    if mcp is None:
        return
    servers = mcp.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        report.block(".mcp.json: 'mcpServers' must be a non-empty object")
        return
    for name, server in servers.items():
        if not isinstance(server, dict):
            report.block(f".mcp.json: server '{name}' must be an object")
            continue
        if "url" in server:
            url = str(server["url"])
            if server.get("type") not in {"http", "sse", "ws"}:
                report.block(f".mcp.json: server '{name}' needs type http, sse or ws")
            if not (url.startswith(("https://", "wss://")) or url.startswith("${user_config.") or url == ""):
                report.block(f".mcp.json: server '{name}' url must be https:// or wss://")
            if re.search(r"\bTODO\b", url):
                report.block(f".mcp.json: server '{name}' url contains a TODO placeholder")
        elif "command" in server:
            report.hold(f".mcp.json: server '{name}' runs a local command; reviewer will read it")
        else:
            report.block(f".mcp.json: server '{name}' needs 'url' or 'command'")
        if "headers" in server and re.search(r"(?i)bearer\s+[A-Za-z0-9]", json.dumps(server["headers"])):
            report.block(f".mcp.json: server '{name}' has a credential in headers; use userConfig")


def check_files(root: Path, report: Report) -> None:
    files = project_files(root)
    seen: dict[str, str] = {}
    total = 0
    countable = 0

    for path in files:
        relative = path.relative_to(root)
        shown = str(relative)

        if any(part.lower() in JUNK_FILES for part in relative.parts):
            report.block(f"{shown}: junk file, remove it")
        if path.is_symlink():
            report.block(f"{shown}: symbolic link")
            continue

        for part in relative.parts:
            stem = part.split(".")[0].lower()
            if ":" in part or part.endswith((".", " ")) or stem in WINDOWS_DEVICES:
                report.block(f"{shown}: name not valid on Windows")
                break
        for directory in relative.parts[:-1]:
            if not re.fullmatch(r"[A-Za-z0-9._-]+", directory):
                report.block(f"{shown}: folder name may only use letters, digits, dots, hyphens and underscores")
                break
        key = str(relative).lower()
        if key in seen and seen[key] != shown:
            report.block(f"{shown}: differs only by case from {seen[key]}")
        seen[key] = shown

        size = path.stat().st_size
        total += size
        suffix = path.suffix.lower()
        is_media = suffix in IMAGE_EXTENSIONS or suffix in FONT_EXTENSIONS or suffix == ".svg"
        if size > 5 * 1024 * 1024:
            report.block(f"{shown}: file over 5 MiB")
        if relative.parts[0] not in {"scripts", "tests"}:
            countable += 1
            if not is_media and size > 256 * 1024:
                report.hold(f"{shown}: non-image file over 256 KiB")
            if not is_media:
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    report.hold(f"{shown}: binary file other than image or font")
                    continue
                for pattern in SECRET_PATTERNS:
                    if pattern.search(content):
                        report.block(f"{shown}: looks like a real credential")
                        break

        if path.name == ".gitattributes":
            attributes = path.read_text(encoding="utf-8")
            if re.search(r"export-ignore|export-subst|\bfilter=", attributes):
                report.block(f"{shown}: export-ignore, export-subst or filter attributes are not allowed")
        if path.name in {".npmrc", "bunfig.toml", "uv.toml"}:
            report.block(f"{shown}: package-manager config is not allowed")
        if path.name == ".gitmodules":
            report.block("Git submodules are not allowed")

    if countable > 512:
        report.hold(f"{countable} files in the plugin folder (limit 512)")
    if total > 50 * 1024 * 1024:
        report.block("repository over 50 MiB")


def check_skills(root: Path, report: Report) -> None:
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if not skills:
        report.warn("no skill found (expected skills/<name>/SKILL.md)")
    for skill in skills:
        label = f"skills/{skill.parent.name}/SKILL.md"
        match = re.match(r"---\r?\n(.*?)\r?\n---", skill.read_text(encoding="utf-8"), re.S)
        if match is None:
            report.warn(f"{label}: front matter missing")
            continue
        front = match.group(1)
        description = re.search(r"^description:\s*(\S.*)$", front, re.M)
        if description is None:
            report.warn(f"{label}: description missing")
        elif description.group(1).lstrip().startswith(("[", "{", "|", ">")):
            report.block(f"{label}: description must be a single text value")
        if not re.search(r"^name:\s*\S+", front, re.M):
            report.warn(f"{label}: name missing")


def check_assets(root: Path, report: Report) -> None:
    # Logo paths are relative to the plugin root, which is also the ZIP root: ./assets/logo.png
    manifest = json.loads((root / OPENAI_MANIFEST).read_text(encoding="utf-8")) if (root / OPENAI_MANIFEST).is_file() else {}
    interface = manifest.get("extensions", {}).get("com.openai", {}).get("interface", {})
    for key in ("logo", "composerIcon"):
        reference = interface.get(key)
        if reference and not (root / reference).resolve().is_file():
            report.block(f"{OPENAI_MANIFEST}: {key} points to a missing file ({reference})")


def check_openai(root: Path, claude: dict | None, report: Report) -> None:
    openai = load_json(root / OPENAI_MANIFEST, report, OPENAI_MANIFEST)
    load_json(root / OPENAI_MCP, report, OPENAI_MCP)
    if openai is None or claude is None:
        return
    for key in ("name", "version"):
        if openai.get(key) != claude.get(key):
            report.block(f"{key} differs between {CLAUDE_MANIFEST} ({claude.get(key)}) and {OPENAI_MANIFEST} ({openai.get(key)})")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(openai.get("version", ""))):
        report.block(f"{OPENAI_MANIFEST}: version must be semver (e.g. 0.1.0)")
    for relative in (OPENAI_MANIFEST, OPENAI_MCP):
        path = root / relative
        if path.is_file() and re.search(r"\bTODO\b", path.read_text(encoding="utf-8")):
            report.block(f"{relative}: TODO placeholder left")


def run_check(root: Path = ROOT, use_cli: bool = True) -> Report:
    report = Report()
    manifest = check_manifest(root, report)
    check_readme_and_license(root, manifest, report)
    check_mcp(root, report)
    check_files(root, report)
    check_skills(root, report)
    check_openai(root, manifest, report)
    check_assets(root, report)

    if use_cli and shutil.which("claude"):
        result = subprocess.run(["claude", "plugin", "validate", str(root)], capture_output=True, text=True)
        if result.returncode != 0:
            report.block("claude plugin validate failed: " + (result.stdout + result.stderr).strip().replace("\n", " | "))
    return report


def bump_version(version: str, level: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def write_version(path: Path, old: str, new: str) -> None:
    """Replace only the version value so the file formatting is kept."""
    content = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r'("version"\s*:\s*")' + re.escape(old) + '"', r"\g<1>" + new + '"', content, count=1), encoding="utf-8")


def archive_entries(root: Path) -> list[tuple[Path, str]]:
    entries = [(root / OPENAI_MANIFEST, "plugin.json"), (root / OPENAI_MCP, "mcp.json")]
    for folder in ("assets", "skills"):
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and path.name.lower() not in JUNK_FILES:
                entries.append((path, str(path.relative_to(root))))
    return sorted(entries, key=lambda entry: entry[1])


def run_build(root: Path = ROOT, output: Path | None = None, bump: str | None = None, force: bool = False, use_cli: bool = True) -> Path:
    report = run_check(root, use_cli)
    report.print()
    if report.blocked:
        raise SystemExit("Blocked: fix the findings above before building.")

    claude_path = root / CLAUDE_MANIFEST
    manifest = json.loads(claude_path.read_text(encoding="utf-8"))
    name, version = manifest["name"], manifest["version"]
    new_version = bump_version(version, bump) if bump else version
    output = output or root / "dist"
    archive = output / f"{name}-{new_version}.zip"

    if archive.exists() and not force:
        raise SystemExit(f"{archive} already exists: use --force or --bump.")
    if new_version != version:
        write_version(claude_path, version, new_version)
        write_version(root / OPENAI_MANIFEST, version, new_version)

    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for source, arcname in archive_entries(root):
            info = zipfile.ZipInfo(f"{name}/{arcname}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zip_file.writestr(info, source.read_bytes())
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "build"):
        sub = commands.add_parser(command)
        sub.add_argument("--no-cli", action="store_true", help="skip `claude plugin validate`")
        if command == "build":
            sub.add_argument("--bump", choices=["major", "minor", "patch"])
            sub.add_argument("--force", action="store_true")
            sub.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.command == "check":
        report = run_check(use_cli=not args.no_cli)
        report.print()
        print("Blocked." if report.blocked else ("Passed with findings." if report.findings else "Passed."))
        return 1 if report.blocked else 0

    archive = run_build(output=args.output, bump=args.bump, force=args.force, use_cli=not args.no_cli)
    with zipfile.ZipFile(archive) as zip_file:
        for entry in zip_file.namelist():
            print(f"  {entry}")
    print(f"{archive} ({archive.stat().st_size / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
