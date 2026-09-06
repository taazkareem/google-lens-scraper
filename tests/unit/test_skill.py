"""Unit tests for the Google Lens Agent Skill and CLI installer."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from google_lens_pro.cli import cli, get_skill_source_path


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Simple parser for YAML frontmatter in SKILL.md."""
    if not content.startswith("---"):
        raise ValueError("SKILL.md must start with YAML frontmatter delimiters (---)")
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md frontmatter must be closed with (---)")
    raw_yaml = parts[1]
    body = parts[2]

    meta: dict[str, str] = {}
    current_key: str | None = None
    for line in raw_yaml.splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith("#"):
            continue
        if ":" in line_s and not line.startswith(" "):
            k, v = line_s.split(":", 1)
            current_key = k.strip()
            meta[current_key] = v.strip()
        elif current_key and line.startswith(" "):
            # indented continuation
            meta[current_key] += " " + line_s
    return meta, body


class TestSkillSpecCompliance:
    """Validates that SKILL.md adheres 100% to https://agentskills.io/specification."""

    @classmethod
    def setup_class(cls) -> None:
        source_dir = get_skill_source_path()
        cls.skill_dir = source_dir
        cls.skill_file = source_dir / "SKILL.md"
        assert cls.skill_file.exists(), f"SKILL.md not found in {source_dir}"
        cls.raw_content = cls.skill_file.read_text(encoding="utf-8")
        cls.frontmatter, cls.body = parse_frontmatter(cls.raw_content)

    def test_name_format_and_folder_match(self) -> None:
        name = self.frontmatter.get("name")
        assert name is not None, "Frontmatter missing required 'name' field"
        assert 1 <= len(name) <= 64, (
            f"Name length ({len(name)}) must be between 1 and 64 characters"
        )
        assert re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name), (
            f"Name '{name}' violates constraints (lowercase alphanumeric and single hyphens only)"
        )
        assert name == self.skill_dir.name, (
            f"Skill name '{name}' must match parent directory name '{self.skill_dir.name}'"
        )

    def test_description_format(self) -> None:
        desc = self.frontmatter.get("description")
        assert desc is not None, "Frontmatter missing required 'description' field"
        assert 1 <= len(desc) <= 1024, (
            f"Description length ({len(desc)}) must be between 1 and 1024 characters"
        )
        # Verify trigger keywords are present
        assert "Google Lens" in desc or "google lens" in desc.lower()
        assert "reverse image search" in desc.lower()

    def test_compatibility_and_license_fields(self) -> None:
        license_field = self.frontmatter.get("license")
        assert license_field == "MIT"

        compat = self.frontmatter.get("compatibility")
        if compat:
            assert len(compat) <= 500

    def test_progressive_disclosure_line_limit(self) -> None:
        lines = self.raw_content.splitlines()
        assert len(lines) < 500, (
            f"SKILL.md has {len(lines)} lines; must be < 500 lines for progressive disclosure"
        )

    def test_referenced_files_exist(self) -> None:
        assert (self.skill_dir / "references" / "REFERENCE.md").exists()
        assert (self.skill_dir / "scripts" / "search_image.py").exists()
        assert (self.skill_dir / "scripts" / "batch_search.py").exists()

    def test_bundled_scripts_have_pep723_metadata(self) -> None:
        scripts = [
            self.skill_dir / "scripts" / "search_image.py",
            self.skill_dir / "scripts" / "batch_search.py",
        ]
        for s in scripts:
            code = s.read_text(encoding="utf-8")
            assert "# /// script" in code, f"{s.name} missing PEP 723 header"
            assert "# ///" in code, f"{s.name} missing PEP 723 closing tag"
            assert "google-lens-pro" in code, f"{s.name} missing dependency declaration"
            # Ensure valid python syntax
            compile(code, str(s), "exec")


class TestInstallSkillCLI:
    """Validates the 'google-lens install-skill' command."""

    def test_install_skill_custom_dest(self, tmp_path: Path) -> None:
        runner = CliRunner()
        target_dir = tmp_path / "custom_dir"

        result = runner.invoke(cli, ["install-skill", "--dest", str(target_dir)])
        assert result.exit_code == 0, result.output
        assert "Successfully installed google-lens-pro Agent Skill" in result.output

        installed_skill = target_dir / "google-lens-pro"
        assert (installed_skill / "SKILL.md").exists()
        assert (installed_skill / "references" / "REFERENCE.md").exists()
        assert (installed_skill / "scripts" / "search_image.py").exists()
        assert (installed_skill / "scripts" / "batch_search.py").exists()

    def test_install_skill_fails_without_force_when_exists(self, tmp_path: Path) -> None:
        runner = CliRunner()
        target_dir = tmp_path / "skills" / "google-lens-pro"
        target_dir.mkdir(parents=True)
        dummy_file = target_dir / "dummy.txt"
        dummy_file.write_text("existing", encoding="utf-8")

        # Re-installing without --force should exit with code 1
        result = runner.invoke(cli, ["install-skill", "--dest", str(tmp_path / "skills")])
        assert result.exit_code == 1
        assert "Target skill directory already exists" in result.output
        assert dummy_file.exists()

        # Re-installing with --force should succeed and overwrite
        force_result = runner.invoke(
            cli, ["install-skill", "--dest", str(tmp_path / "skills"), "--force"]
        )
        assert force_result.exit_code == 0
        assert (target_dir / "SKILL.md").exists()
        assert not dummy_file.exists()

    def test_install_skill_default_local_path(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = runner.invoke(cli, ["install-skill"])
            assert result.exit_code == 0
            expected = tmp_path / ".agents" / "skills" / "google-lens-pro"
            assert (expected / "SKILL.md").exists()

    def test_install_skill_claude_flag(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = runner.invoke(cli, ["install-skill", "--claude"])
            assert result.exit_code == 0
            expected = tmp_path / ".claude" / "skills" / "google-lens-pro"
            assert (expected / "SKILL.md").exists()

    def test_install_skill_global_flag(self, tmp_path: Path) -> None:
        runner = CliRunner()
        fake_home = tmp_path / "fake_home"
        with patch("pathlib.Path.home", return_value=fake_home):
            result = runner.invoke(cli, ["install-skill", "--global"])
            assert result.exit_code == 0
            expected = fake_home / ".agents" / "skills" / "google-lens-pro"
            assert (expected / "SKILL.md").exists()
