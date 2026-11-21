# Publishing this skill

# by Alucard0x1

One commit, forced push, version frozen at 1.0, and release notes that describe the state rather than a delta.

Part of the `pulupulu-motion` skill. The entry point and the gate table live in `SKILL.md`.

## 15. Publishing this skill

This directory is also the public repo. Repo shape, the `.gitignore` that keeps heavy sample media out, the publish/tag/release commands, the footprint-scrub procedure (including the orphan-branch history rewrite) and the one licence line that must stay: `references/publishing.md`.

**Only when the user asks to publish.** History is always ONE commit, rewritten on every update (`references/publishing.md` §2b) — the version stays `1.0` and the tag stays `v1.0`, then `scripts/publish-squash.sh <skill dir> <message file>`, then prove it: remote SHA equals local HEAD and `gh api repos/<owner>/<repo>/commits --jq 'length'` prints 1.

**The message argument is a FILE, and passing it inline strands the repo.** The script checks out a commitless orphan branch (`__single`) first, so when the second argument is a string instead of a path, `git commit -F "<that string>"` fails on a too-long filename and leaves the working tree on `__single` with **zero commits** — `git checkout main` then aborts on the dirty tree and nothing is pushed. The script now validates the file before it touches the branch; if you inherit the broken state, recover with `git add -A && git commit -F <msgfile> && git branch -M main && git push -f origin main`, then re-tag: `git tag -fa v1.0 -m "…" && git push -f origin v1.0`. Do the work in the same turn as the edit once publishing is wanted; say that the force push invalidates existing clones, and that old commits stay reachable by SHA until GitHub's GC runs.

**Every file carries the credit mark, and the repo prose is English-only** (`references/publishing.md` §1b) — `scripts/stamp_credit.py <root> --owner <name>` stamps all 364-odd files idempotently, after frontmatter, after shebang, after doctype, never into JSON; re-run `compileall` / `node --check` / `json.load` afterwards. Foreign-language words survive only as a tool's own data (a detector's stopword list, an expander's spoken-digit table), and every such block needs a comment saying so. When the user says the repo must contain no foreign language, they mean the prose — rewrite quoted examples in English and describe the incident instead of repeating the quote.

**Merging another library in, or translating this one, is a procedure — follow it from the sourcing skill.** `agent-skill-sourcing` §6 plus its `agent-skill-sourcing:references/rebrand-and-translate.md` — in that skill's tree, not this repo — carry the order (namespace each source, write the routing index yourself, neutralise vendor upsells, rebrand minimally, scrub prose but keep the copyright notice, rewrite history, verify from a fresh clone) and the bulk-translation wave recipe (measure the volume, ~10 subagents one directory each with a numeric-token diff, then one parent-owned rename-and-relink pass, then `node --check` / `ast.parse` / `json.load` over the whole tree). Two failures from doing it casually: a blind token replacement turned an identifier into a syntax error, and a renamed asset left a dangling `src`.
