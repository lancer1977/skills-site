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

Some skills talk to my own homelab infrastructure (internal hosts, deploy topology,
credentials) and are listed in `scripts/redacted.json`. Those get a generic
description and a "when to use it" list instead of the real source — see that file to
add/adjust which skills are treated this way, and `scripts/categories.json` for the
catalog grouping.

## Regenerating

```sh
python3 -m venv .venv && . .venv/bin/activate && pip install pyyaml
python3 scripts/generate.py
```

Output goes to `site/`, which is what gets served (plain `nginx:alpine`, no build step
on the server side — see the `skills-site` stack in `homelab-gitops`).

## Adding a skill

Just add/edit the `SKILL.md` under `~/.claude/skills/`, add an entry to
`scripts/categories.json`, and (if it references internal infrastructure) an entry in
`scripts/redacted.json`. Re-run the generator and redeploy.
