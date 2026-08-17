#!/usr/bin/env python3
"""Generate skills.polyhydra.app static site from ~/.claude/skills/*/SKILL.md.

Usage: python3 generate.py [--skills-dir DIR] [--out DIR]
"""
import argparse
import html
import json
import shutil
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
SITE_TITLE = "Polyhydra Skills"
SITE_DOMAIN = "skills.polyhydra.app"


def load_json(name):
    with open(SCRIPT_DIR / name) as f:
        return json.load(f)


def parse_skill_md(path):
    text = path.read_text()
    if not text.startswith("---"):
        raise ValueError(f"{path} has no frontmatter")
    _, fm_text, body = text.split("---", 2)
    fm = yaml.safe_load(fm_text)
    return fm["name"], fm.get("description", "").strip(), body.strip()


def esc(s):
    return html.escape(s, quote=True)


def install_block(name, source_text):
    return (
        '<div class="install">\n'
        f"    <p>Drop this in — save the block below as <code>~/.claude/skills/{esc(name)}/SKILL.md</code>, "
        "or run:</p>\n"
        "    <pre>mkdir -p ~/.claude/skills/"
        f"{esc(name)}\n"
        f"cat &gt; ~/.claude/skills/{esc(name)}/SKILL.md &lt;&lt;'EOF'\n"
        "# (paste the full source block below into this file)\n"
        "EOF</pre>\n"
        "  </div>"
    )


def render_skill_page(name, description, body, category, sensitive, redacted):
    eyebrow = f'<a href="/">{esc(SITE_TITLE)}</a> &nbsp;/&nbsp; {esc(category)}'
    badges = f'<span class="badge">{esc(category)}</span>'
    if sensitive:
        badges += '<span class="badge restricted">Homelab-internal</span>'

    if sensitive:
        tagline = esc(redacted["description"])
        when_items = "\n".join(f"      <li>{esc(w)}</li>" for w in redacted["when"])
        body_section = f"""
  <section>
    <h2>When to use it</h2>
    <ul>
{when_items}
    </ul>
  </section>

  <div class="notice">
    <strong>Homelab-internal.</strong> This skill talks to infrastructure specific to my own
    self-hosted setup (internal hosts, credentials, deploy topology). The description above
    reflects the general pattern — the implementation itself isn't published here.
  </div>
"""
        main = f"""<div class="page">

  <p class="eyebrow">{eyebrow}</p>
  <h1>{esc(name)}</h1>
  <p class="tagline">{tagline}</p>
  <div class="badges">{badges}</div>
  <hr class="rule" />
{body_section}
  <footer>
    Part of the <a href="/">{esc(SITE_TITLE)}</a> catalog. Requires
    <a href="https://claude.com/product/claude-code">Claude Code</a>.
  </footer>

</div>"""
    else:
        install = install_block(name, body)
        main = f"""<div class="page">

  <p class="eyebrow">{eyebrow}</p>
  <h1>{esc(name)}</h1>
  <p class="tagline">{esc(description)}</p>
  <div class="badges">{badges}</div>
  <hr class="rule" />

  {install}

  <section>
    <h2>Full source</h2>
    <details>
      <summary>SKILL.md — copy everything inside</summary>
      <pre>{esc(body)}</pre>
    </details>
  </section>

  <footer>
    Part of the <a href="/">{esc(SITE_TITLE)}</a> catalog. Requires
    <a href="https://claude.com/product/claude-code">Claude Code</a>.
  </footer>

</div>"""

    meta_desc = redacted["description"] if sensitive else description

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)} — {esc(SITE_TITLE)}</title>
<meta name="description" content="{esc(meta_desc[:200])}">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
{main}
</body>
</html>
"""


def render_index(skills_by_category, total, restricted_count):
    groups_html = []
    all_cards_html = []
    for category in sorted(skills_by_category):
        cards = []
        for s in sorted(skills_by_category[category], key=lambda x: x["name"]):
            cls = "skill-card restricted" if s["sensitive"] else "skill-card"
            desc = esc(s["redacted_desc"] if s["sensitive"] else s["description"])
            card = (
                f'<a class="{cls}" href="/{esc(s["name"])}/" '
                f'data-name="{esc(s["name"].lower())}" data-desc="{esc(desc.lower())}">\n'
                f'          <div class="name">{esc(s["name"])}</div>\n'
                f'          <div class="desc">{desc}</div>\n'
                "        </a>"
            )
            cards.append(card)
            all_cards_html.append(card)
        groups_html.append(
            f'    <div class="group">\n'
            f"      <h2>{esc(category)}</h2>\n"
            f'      <div class="grid">\n        ' + "\n        ".join(cards) + "\n      </div>\n    </div>"
        )

    groups = "\n\n".join(groups_html)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(SITE_TITLE)}</title>
<meta name="description" content="Claude Code skills I actually use, packaged as copy-paste SKILL.md files.">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<div class="page wide">

  <div class="hero">
    <p class="eyebrow">skills.polyhydra.app</p>
    <h1>{esc(SITE_TITLE)}</h1>
    <p class="tagline">Claude Code skills I actually use day to day, packaged as copy-paste
    <code>SKILL.md</code> files. {total} skills, {restricted_count} of them homelab-internal
    (pattern only, no implementation).</p>
  </div>

  <div class="search-wrap">
    <input id="search" type="search" placeholder="Search skills…" autocomplete="off">
    <p class="count" id="count"></p>
  </div>

{groups}

  <footer>
    Generated from a personal Claude Code skill library. Requires
    <a href="https://claude.com/product/claude-code">Claude Code</a> to use.
  </footer>

</div>
<script>
(function() {{
  var input = document.getElementById('search');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.skill-card'));
  var groups = Array.prototype.slice.call(document.querySelectorAll('.group'));
  var count = document.getElementById('count');
  function apply() {{
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function(c) {{
      var match = !q || c.dataset.name.indexOf(q) !== -1 || c.dataset.desc.indexOf(q) !== -1;
      c.classList.toggle('hidden', !match);
      if (match) shown++;
    }});
    groups.forEach(function(g) {{
      var anyShown = g.querySelectorAll('.skill-card:not(.hidden)').length > 0;
      g.style.display = anyShown ? '' : 'none';
    }});
    count.textContent = q ? (shown + ' of {total} skills') : '';
  }}
  input.addEventListener('input', apply);
}})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default=str(Path.home() / ".claude" / "skills"))
    ap.add_argument("--out", default=str(SCRIPT_DIR.parent / "site"))
    args = ap.parse_args()

    skills_dir = Path(args.skills_dir)
    out_dir = Path(args.out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "assets").mkdir()
    shutil.copy(SCRIPT_DIR / "style.css.template", out_dir / "assets" / "style.css")

    categories = load_json("categories.json")
    redacted = load_json("redacted.json")

    skills_by_category = {}
    total = 0
    restricted_count = 0

    for d in sorted(skills_dir.iterdir()):
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            name, description, body = parse_skill_md(skill_md)
        except Exception as e:
            print(f"SKIP {d.name}: {e}")
            continue

        category = categories.get(name, "Uncategorized")
        sensitive = name in redacted
        if sensitive:
            restricted_count += 1
        total += 1

        page_dir = out_dir / name
        page_dir.mkdir(parents=True, exist_ok=True)
        page_html = render_skill_page(
            name, description, body, category, sensitive,
            redacted.get(name),
        )
        (page_dir / "index.html").write_text(page_html)

        skills_by_category.setdefault(category, []).append({
            "name": name,
            "description": description,
            "sensitive": sensitive,
            "redacted_desc": redacted.get(name, {}).get("description", ""),
        })

    (out_dir / "index.html").write_text(
        render_index(skills_by_category, total, restricted_count)
    )

    print(f"Generated {total} skill pages ({restricted_count} restricted) into {out_dir}")


if __name__ == "__main__":
    main()
