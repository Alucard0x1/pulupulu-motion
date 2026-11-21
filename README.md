<!-- by Alucard0x1 -->
# pulupulu-motion

An agent skill for making **motion-graphics films, explainers and data stories** — vertical or 16:9 — as editable HTML + GSAP, rendered frame-accurately in your own Chrome, with local music, sound effects and synthesised narration.

It is three layers in one skill:

| Layer | What it answers | Where |
|---|---|---|
| **Film pipeline** | How to structure, time, score and render a film; CLI reference; determinism rules; QA gates | `SKILL.md` §1–§12 |
| **Art direction** | Which style, which camera move, how detailed a character may be; 57 style recipes, 8 executable explainer grammars (9th documented, not registered), shot-list linter | `references/art-motion/` |
| **Feel & timing** | How long a move takes, which curve carries which emotion, choreography, quality checklist | `references/ui-motion/` |

Plus the piece most narrated films get wrong: **narration is authored on a clock, not a guess.** The `tts-intonation` companion skill (shipped here as `references/narration/`) splits a script into phrases, plans the pauses, shapes each phrase, measures the result, and hands the film a `timeline.json` so caption, picture and voice cannot drift apart.

---

## What it produces

- 1080×1920 (9:16), 1920×1080, or any size the brief needs — H.264 + AAC via `ffmpeg`
- Chiptune / synthwave / cinematic / lo-fi / orchestral scores generated locally in ABC notation
- Indonesian and English narration (DeepSeek TTS), numbers spoken as words while the screen keeps digits (`502` → *five oh two*)
- A shot list and a storyboard table that are the same document the film was built from

## Requirements

- Node ≥ 22, Google Chrome, FFmpeg on `PATH`
- Python 3.9+ for the generator/narration scripts (`uv` optional)

## Install as an agent skill

Copy or symlink this directory into your agent's skills folder:

```sh
# Hermes Agent (Windows example)
%LOCALAPPDATA%\hermes\skills\media\pulupulu-motion
# Claude Code / other SKILL.md agents
~/.claude/skills/pulupulu-motion
```

The skill entry point is `SKILL.md`. Everything else is reference material it routes to.

## The CLI

The renderer is the `pulupulu` CLI (MIT). Two ways to run it:

```sh
# local, rebranded build (what this skill assumes — no npm fetch per command)
pulupulu check .
pulupulu sound .
pulupulu render . --format mp4 --fps 30

# or straight from npm, if you have not built the fork
npx --no-install pulupulu-motion check .
```

The build is intentionally minimal (package name, help header, a second bin alias); every flag and template works as documented in `SKILL.md`.

## The narration pipeline

```sh
# 1. one beat = one spoken phrase = one caption = one picture
python references/narration/scripts/tts-prosody.py beats.json assets/voice.wav \
    --voice tide --timeline assets/timeline.json   # assets/ is your project dir; tts-prosody.py writes it --expand id

# 2. the film is generated from the MEASURED timeline, never from a guessed number
python build.py                     # beats.json + timeline.json -> film/index.html

# 3. render, then mux with an explicit map or the narrator disappears
pulupulu render . --format mp4 --fps 30
ffmpeg -i out/film-vN.mp4 -i assets/mix.wav -map 0:v:0 -map 1:a:0 \
       -c:v copy -c:a aac -b:a 192k -shortest out/final.mp4
```

## Repository map

```
SKILL.md                        the router (~2k tokens): may I do this job, what to run first,
                                what has to pass, which page has the detail
references/cli.md               commands, page contract, install
references/workflow.md          the nine steps, project contract, mux recipe
references/narration-and-captions.md   interval model, storyboard, captions, one-language gate
references/design-taste.md      palettes, element budget, personality sliders, rhythm
references/motion-library.md    twenty motion languages, techniques, 3D layer
references/workflows-specialized.md   punch-up, product demo, talking head, grammars
references/audio-and-music.md   musical worlds, composer mode, sfx, narration synthesis
references/render-traps.md      every failure that produced a black frame or a stall
references/verification.md      what to check, in what order, and what no gate proves
references/art-extension.md     how the merged art-direction library is laid out
references/publishing-skills.md one commit, forced push, version frozen at 1.0
references/_history/            the pre-router SKILL.md, kept for reference only
scripts/doctor.py               read-only preflight (node, ffmpeg, CLI, key, disk, page contract)
scripts/deliver_check.py        mux with explicit mapping, then validate the delivered file
scripts/deepseek_voice.py       DeepSeek speech toolkit: probe, speak, cost, lay, beats, asr, gate
scripts/deepseek-tts.py         LEGACY line-by-line TTS with per-line start times
scripts/lang-audit.py           fails the build when text in the wrong language survives,
                                including string literals inside <script>
scripts/art-motion/             shot-list linter, clip/film/sub-zone gates, QA, delivery gate
scripts/art-motion/engine/      Playwright render engine for style-recipe scenes
references/art-motion/          57 style recipes, 9 grammar cards, 8 executable, camera language
references/ui-motion/           timing/easing tables, emotion mapping, choreography, checklist
references/narration/           tts-intonation skill + tts-prosody.py
```

## Hard-won rules baked into the skill

- **Caption = the spoken sentence.** The only licensed difference is notation (`502` on screen, *five oh two* in the voice).
- **Measure the audio before building the picture.** A timeline guessed in advance drifts within three beats.
- **Never compress speech to hit a round number.** Duration negotiates; screen format does not.
- **Mux with `-map 0:v:0 -map 1:a:0`.** `pulupulu render` embeds the score, so a bare `-shortest` keeps the music and drops the narrator.
- **Check the language mechanically.** Art templates leak; `scripts/lang-audit.py` is the gate.
- **A huge animated SVG re-rastered every frame stalls the renderer.** Move small props, not a 4400 px strip; no webfont `<text>` inside SVG.

## Licence

MIT — see `LICENSE`. Portions of this skill derive from MIT-licensed work; the
required copyright notices travel with the licence. The rebranding, the narration
pipeline, the language audit and the field notes are original to this repository.
