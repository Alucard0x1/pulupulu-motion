<!-- by Alucard0x1 -->
# Publishing this skill as a GitHub repo

The skill directory **is** the repository. This is the procedure for putting it on GitHub, and for
re-publishing it after a rebrand without leaking anything that should not be public.

## 1. Repo shape

```
SKILL.md          the entry point an agent loads
README.md         what it is, three layers, requirements, quick start, repo map
LICENSE           MIT text, one copyright line per rights holder
NOTICE.md         provenance of merged work (only if the rights holders must be named)
.gitignore        heavy sample media, render output, TTS cache
references/       topical depth (art-motion, ui-motion, narration, 2d-vector-motion, …)
scripts/          runnable helpers (tts-prosody, lang-audit, art-motion gates + engine)
```

`.gitignore` essentials — a skill repo should clone in seconds:

```gitignore
.om/
out/
assets/mix.wav
assets/voice.wav
.tts-cache/
__pycache__/
*.mp4
*.mov
*.webm

# sample films: keep the code, drop the heavy media
scripts/art-motion/engine/demos/**/*.png
scripts/art-motion/engine/demos/**/*.jpg
scripts/art-motion/engine/demos/**/*.wav
scripts/art-motion/engine/reference_films/**/*.png
scripts/art-motion/engine/reference_films/**/*.jpg
scripts/art-motion/engine/reference_films/**/*.wav
```

Keep `engine/lib/` (the vendored JS the style recipes render with) and keep the *code* inside `demos/`
and `reference_films/` — the reference documents cite files there (`demos/long_scroll/lib/acts.js`,
`reference_films/<name>/render.py`), so a directory-wide ignore publishes a repo whose docs point at
nothing. Sample *media* is what gets cut, not directories:

## 1b. One credit line per file, one language for the prose

**Every source and document in a repo this user owns carries the credit mark.** Their words: a watermark
comment on all of it. Placement is dictated by the file type, because the mark must never break a parser:

| File | Mark | Goes |
|---|---|---|
| `.py`, `.sh`, `.yml` | `# by <owner>` | line 2 when line 1 is a shebang, otherwise line 1 |
| `.js`, `.mjs` | `// by <owner>` | line 1, after a shebang if there is one |
| `.css` | `/* by <owner> */` | line 1 |
| `.html` | `<!-- by <owner> -->` | after `<!doctype>`, never before it |
| `.md` | `<!-- by <owner> -->` | after the closing `---` of YAML frontmatter; line 1 when there is no frontmatter |
| `.json` | **none** | JSON has no comments — adding one breaks every consumer; say so instead of forcing it |

Run it with `scripts/stamp_credit.py <root> --owner <name>` rather than by hand: it is idempotent, skips
files that already carry the mark, refuses to touch JSON, and prints `N/N files` so the claim is measured.
After stamping, re-prove the tree still parses — `python -m compileall -q scripts references`,
`node --check` on every `.js`, `json.load` on every `.json` — because a mark in the wrong place on a
frontmatter file silently unregisters the skill.

**Prose is English; only a tool's data may stay in the target language.** An Indonesian film is not an
Indonesian repository: examples, beat tables, post-mortem quotes and UI sample copy in the docs all get
rewritten in English, describing the incident instead of quoting it. What legitimately remains is the
*data a tool needs in order to work* — a stopword list inside a language detector, a spoken-digit table
inside a TTS expander, a `{lang: "oh" | "kosong"}` mapping. Two consequences:

1. Give each such block a comment that says what it is and why it must stay, or a later "clean the
   language" pass deletes the detector and the tool fails silently on the next film.
2. Grep for a short list of unmistakable function words rather than trusting your ear — sweep `.md .py
   .js .sh .html .css` for whole-word matches, then read every hit: quoted foreign copy is a real hit and
   needs rewriting, while `film`, `video`, `data` and a person named `Dan` are false positives that must
   survive the sweep.

## 2. Publish

```sh
cd <skill dir>
git init -b main
git add -A
git commit -m "pulupulu-motion 1.0"
gh repo create <name> --public --source=. --remote=origin --push \
  --description "one line that matches README's first sentence"

git tag -a v1.0 -m "<name> 1.0" && git push origin v1.0
gh release create v1.0 --title "<name> 1.0" --notes "what is in the release"
```

Verify from a **fresh clone**, never from the working tree: `git ls-files | wc -l`, and open one file
that matters (`SKILL.md`, `LICENSE`) to confirm the content that landed is the content you wrote.

Before cloning, prove `.gitignore` is not eating referenced files — compare the working tree with the
index, per extension:

```sh
for ext in py md js json; do
  echo "$ext: worktree $(find . -name "*.$ext" -not -path './.git/*' | wc -l) tracked $(git ls-files | grep -c "\.$ext$")"
done
```

A gap with zero untracked files means the ignore rules took them; `git check-ignore -v <file>` names the
rule. And when you `cd` into the clone inside a compound command, that `cd` can fail quietly and leave the
next checks running against the source tree — `cd` as its own step and print `pwd` before trusting the
numbers.

## 2b. Every update: one commit, rewritten (standing rule)

History in this repo is **always a single commit**. Each update re-states the whole tree as the first
commit and force-pushes it — no "Add …" follow-ups, no merge commits, no tags left on dead commits.
Publishing is part of the edit, not a follow-up request: after changing `SKILL.md` or a reference,
commit and push in the same turn without being asked.

**Version and tag never move.** This repo is always `version: "1.0"` / tag `v1.0` / release "1.0" — do
not bump the number on updates. A new update rewrites the commit, re-points the same `v1.0` tag at it,
and **edits** the existing release; the number only changes if the user asks for it.

Recipe — scripted, `scripts/publish-squash.sh <skill-dir> <message-file>` (tag defaults to `v1.0`):

```sh
cd <skill dir>
git checkout --orphan single          # keeps the index, drops the parents
git add -A
git commit -F <message-file>          # message describes the STATE of the skill, not a delta
git branch -M single main
git push -f origin main

git tag -d v1.0 2>/dev/null; git tag -a v1.0 -m "pulupulu-motion 1.0"
git push -f origin v1.0
gh release edit v1.0 --notes "<updated notes>"    # edit, never create a new release
```

Then verify — a force push that printed no error can still leave the repo wrong:

```sh
git ls-remote origin refs/heads/main | cut -f1      # must equal git rev-parse HEAD
git ls-remote --tags origin                        # ONLY the current tag, plus its ^{} line
gh api repos/<owner>/<repo>/commits --jq 'length'  # must print 1
gh release list                                    # old releases gone, current one Latest
```

What actually goes wrong here:

- **A stale tag keeps an old commit alive and visible.** Deleting the branch ref is not enough —
  enumerate remote tags, delete each one explicitly (`git push origin --delete <tag>`), then re-run
  `git ls-remote --tags`. A batched delete can drop one silently (its stderr was swallowed), and the
  surviving tag drags the pre-rewrite commit back into view.
- **Delete the releases too:** `gh release delete <old-tag> --yes` for every release whose commit no
  longer exists, otherwise the Releases page keeps advertising the old history.
- **Force push rewrites every SHA.** Anyone who cloned must `git fetch && git reset --hard origin/main`.
  State that in the reply instead of presenting the history as merely "updated".
- **Old commits remain reachable by SHA until GitHub's GC runs** — same caveat as §3.4. Do not claim a wipe.
- **Never let the tag and the frontmatter drift.** Frontmatter stays `version: "1.0"` and the tag stays
  `v1.0` forever; if you see `v1.0.3` anywhere, it is a leftover from before this rule.
- **Align the frontmatter version with the tag in the same commit.** A tag reading v1.0.3 over a
  `metadata.version: 1.0.2` is a half-finished publish.

## 3. Removing third-party footprints (rebranding for publication)

When the user wants no trace of the projects a skill was assembled from, scrub in this order. Do the
whole pass in one script so nothing is caught by hand-editing fatigue:

1. **Delete credit-only files:** provenance/NOTICE documents, author bios, per-directory copies of the
   upstream licence.
2. **Rename assets and namespaces that carry a name:** `lib/rig_<vendor>.js` → `scripts/art-motion/engine/lib/rig_legacy.js`,
   `<VENDOR>_CONFIG_HOME` → `<SKILL>_CONFIG_HOME`, config dirs, demo folder defaults. Then update every
   reference to them (`engine/index.html`, docs) — a renamed file with stale references is a broken skill.
3. **Mass-substitute the remaining prose** across `.md .py .js .json .txt .html .css`: project names →
   your skill name, repo URLs → your repo URL, author names → neutral wording. Then **read the result**:
   substitution leaves garbage like "merged from `<own name>` 1.3.1" or "the author / the author", and
   those sentences must be rewritten by hand, not patched again.
4. **Scrub the history, not only the tree.** A clean tree with a dirty log still publishes the names:
   ```sh
   git checkout --orphan clean
   git add -A && git commit -m "<name> v1.0.0"
   git branch -D main && git branch -m main
   git push -f origin main
   git tag -d v1.0.0 && git push origin :refs/tags/v1.0.0
   gh release delete v1.0.0 --yes        # then recreate tag + release on the new commit
   ```
   Note: old commits stay reachable by SHA on GitHub until its garbage collection runs — force-push
   removes them from the branch, not from existence. Say that plainly instead of claiming a wipe.
5. **Verify:** fresh clone, then `grep -ril -E '<terms>' . --exclude-dir=.git | wc -l` must be the
   count you intend (usually 0).

### The licence line you do not remove

MIT requires the copyright notice and permission text to travel with copies and substantial portions.
So: scrub every *name, URL and marketing mention*, and keep **one** copyright line per rights holder
in `LICENSE` (the file nobody reads for branding). Say why, in one sentence, and offer the only
option that removes it entirely: drop the merged directories so the repo contains only your own work.
Stripping the notice while keeping the code is a licence violation, not a rebrand — do not do it
because a user asked for "zero footprint".

## 4. Pitfalls

- **`git tag -d` has no `-q`.** `git tag -d v1.0.0 -q` fails and, inside a `&&` chain, silently skips
  the re-tag — you then push the old tag back and wonder why the release points at the dirty commit.
- **Do not `rm -rf` a directory the shell is currently inside** on Windows: the shell's cwd holds a
  lock and the delete fails with `Device or resource busy`. `cd` out first, or clone the verification
  copy under a fresh name.
- **Git's `LF will be replaced by CRLF` warnings are noise.** They flood the output of a large commit
  and hide the one line that matters; read the last lines, not the middle.
- **A first `gh repo create --source=. --push` also sets upstream tracking.** After a force-push rewrite,
  `git log --oneline origin/main` still shows one clean commit — check that, not `git log` alone.
- **Never publish renders.** `*.mp4` belongs in `.gitignore`; sample films go out as release assets or
  not at all.
- **`git branch -M <name>` force-renames over the existing branch, which is what the orphan rewrite needs;**
  deleting the old branch first is what loses the ref if the push then fails.
- **After a squash publish, compare `git ls-files | wc -l` with the count before it.** `--orphan` keeps the
  index, so `git add -A` re-stages the whole tree; a `.gitignore` that grew since the last publish silently
  drops files from the new single commit.

<!-- related-skills -->

---

**Where this fits** — part of the **`pulupulu-motion`** skill.
[Skill index](../SKILL.md) · [Art library index](art-motion/INDEX.md)

Handoffs and neighbouring skills (narration timing, merging another library, rights review, sourcing a reference video, 3D or footage shots, type-first films): `references/art-motion/INDEX.md`.
