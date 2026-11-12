# skills-site

Static site generator for [skills.polyhydra.app](https://skills.polyhydra.app) — a
public catalog of the [Claude Code](https://claude.com/product/claude-code) skills I
actually use, each rendered as a copy-paste-able page like
`skills.polyhydra.app/<skill-name>/`.

## How it works

`scripts/generate.py` reads every `~/.claude/skills/<name>/SKILL.md` on the machine it
runs on, and renders:

- `site/<name>/index.html` — one page per skill, with an install snippet and the full
  `SKILL.md` source in a copy-paste block.
- `site/index.html` — a searchable catalog grouped by category.

Publication is **fail closed**: a skill must have an entry in `scripts/categories.json`
before it is published at all. A skill with no `categories.json` entry is skipped
entirely — no page, no index card — rather than defaulting to a public page. Some
published skills also talk to my own homelab infrastructure (internal hosts, deploy
topology, credentials) and are additionally listed in `scripts/redacted.json`; those
get a generic description and a "when to use it" list instead of the real source. See
`scripts/categories.json` to classify/group a skill for publication, and
`scripts/redacted.json` to mark a classified skill as restricted.

## Regenerating

```sh
python3 -m venv .venv && . .venv/bin/activate && pip install pyyaml
python3 scripts/generate.py
```

Output goes to `site/`, which is what gets served (plain `nginx:alpine`, no build step
on the server side — see the `skills-site` stack in `homelab-gitops`).

If any `SKILL.md` cannot be parsed (missing frontmatter, invalid YAML, no `name`), the
generator lists every malformed path and its error on stderr and exits non-zero without
writing the catalog index. There is no skip-and-continue mode; fix or remove the source
and re-run. Tests: `python3 -m unittest discover -s scripts -p 'test_*.py'`.

## Adding a skill

Add/edit the `SKILL.md` under `~/.claude/skills/`, then add an entry to
`scripts/categories.json` — **required**, or the skill is held back and not
published at all — and (if it references internal infrastructure) an entry in
`scripts/redacted.json`. Re-run the generator and redeploy.
