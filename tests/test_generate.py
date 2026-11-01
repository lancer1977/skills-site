"""Tests for the fail-closed publication classification in scripts/generate.py.

A skill is only published if it has an entry in categories.json. A skill with
no categories.json entry must be held back entirely -- no page, no index
card -- rather than defaulting to a public "Uncategorized" page.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE_PY = REPO_ROOT / "scripts" / "generate.py"


def _load_generate_module():
    """Import scripts/generate.py as a fresh module object per test."""
    spec = importlib.util.spec_from_file_location("generate_under_test", GENERATE_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_skill(skills_dir, name, description="A test skill.", body_extra=""):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n"
        f"Body content for {name}.{body_extra}\n"
    )


@pytest.fixture
def generate_env(tmp_path, monkeypatch):
    """Build an isolated scripts/ dir (categories.json, redacted.json, css) plus
    an isolated skills dir and out dir, and import generate.py pointed at it."""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "style.css.template").write_text("body { color: black; }")

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    out_dir = tmp_path / "site"

    module = _load_generate_module()
    monkeypatch.setattr(module, "SCRIPT_DIR", script_dir)

    def set_categories(categories):
        (script_dir / "categories.json").write_text(json.dumps(categories))

    def set_redacted(redacted):
        (script_dir / "redacted.json").write_text(json.dumps(redacted))

    set_categories({})
    set_redacted({})

    return {
        "module": module,
        "skills_dir": skills_dir,
        "out_dir": out_dir,
        "set_categories": set_categories,
        "set_redacted": set_redacted,
    }


def run_generate(env):
    sys.argv = [
        "generate.py",
        "--skills-dir", str(env["skills_dir"]),
        "--out", str(env["out_dir"]),
    ]
    env["module"].main()


def test_unclassified_skill_is_held_back(generate_env, capsys):
    _write_skill(generate_env["skills_dir"], "mystery-skill")
    # No categories.json / redacted.json entry for it.

    run_generate(generate_env)

    out_dir = generate_env["out_dir"]
    assert not (out_dir / "mystery-skill").exists()
    index_html = (out_dir / "index.html").read_text()
    assert "mystery-skill" not in index_html

    captured = capsys.readouterr()
    assert "SKIP mystery-skill" in captured.out
    assert "unclassified" in captured.out


def test_classified_public_skill_is_published_with_full_source(generate_env):
    _write_skill(
        generate_env["skills_dir"], "public-skill",
        body_extra=" SECRET_SOURCE_MARKER"
    )
    generate_env["set_categories"]({"public-skill": "Dev Tools"})

    run_generate(generate_env)

    page = generate_env["out_dir"] / "public-skill" / "index.html"
    assert page.exists()
    html = page.read_text()
    assert "SECRET_SOURCE_MARKER" in html
    assert "Full source" in html

    index_html = (generate_env["out_dir"] / "index.html").read_text()
    assert "public-skill" in index_html


def test_classified_restricted_skill_redacted(generate_env):
    _write_skill(
        generate_env["skills_dir"], "restricted-skill",
        body_extra=" SECRET_SOURCE_MARKER"
    )
    generate_env["set_categories"]({"restricted-skill": "Homelab Infra"})
    generate_env["set_redacted"]({
        "restricted-skill": {
            "description": "A generic redacted description.",
            "when": ["Some generic situation"],
        }
    })

    run_generate(generate_env)

    page = generate_env["out_dir"] / "restricted-skill" / "index.html"
    assert page.exists()
    html = page.read_text()
    assert "SECRET_SOURCE_MARKER" not in html
    assert "Homelab-internal" in html
    assert "A generic redacted description." in html


def test_unclassified_skill_does_not_block_other_valid_skills(generate_env):
    _write_skill(generate_env["skills_dir"], "mystery-skill")
    _write_skill(generate_env["skills_dir"], "public-skill")
    generate_env["set_categories"]({"public-skill": "Dev Tools"})

    run_generate(generate_env)

    out_dir = generate_env["out_dir"]
    assert not (out_dir / "mystery-skill").exists()
    assert (out_dir / "public-skill" / "index.html").exists()


def test_restricted_without_category_entry_is_still_held_back(generate_env):
    """A redacted.json entry alone is not a classification -- categories.json
    is the publication allowlist, so a skill missing from it stays held back
    even if someone already flagged it as sensitive."""
    _write_skill(generate_env["skills_dir"], "half-classified-skill")
    generate_env["set_redacted"]({
        "half-classified-skill": {
            "description": "desc",
            "when": ["x"],
        }
    })

    run_generate(generate_env)

    out_dir = generate_env["out_dir"]
    assert not (out_dir / "half-classified-skill").exists()
