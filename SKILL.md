---
name: pulupulu-motion
description: >-
  Use when making a motion-graphics film, launch video, explainer, data story or
  talking-head package. Directs it as editable HTML + GSAP, with local narration and
  music, and renders frame-accurately in headless Chrome. Also punches up an
  existing film. Needs Node, ffmpeg and the self-hosted `pulupulu` CLI; say so
  up front if one is missing.
metadata:
  author: "Alucard0x1"
  homepage: "https://github.com/Alucard0x1/pulupulu-motion"
  repository: "https://github.com/Alucard0x1/pulupulu-motion"
  version: "1.0"
  license: "MIT"
---
<!-- by Alucard0x1 -->

# pulupulu-motion

A film here is a **timeline in HTML** that Chrome renders frame by frame. Nothing is a video editor: you
write a page, the CLI screenshots it at a fixed frame rate, ffmpeg muxes the sound.

This file is the router. It answers: may I do this job, what do I run first, what has to pass, and which
page has the detail. Load a reference page only for the part you are working on.

## 1. Before promising anything

```sh
python scripts/doctor.py                    # read-only: python, node, ffmpeg, the CLI, key, disk
python scripts/doctor.py --project film/    # also: the page contract is present
```

Exit 1 means a film cannot be made on this machine. Do not discover that after writing scenes. Never call
`npx` per command: a network round trip on every `check`, `still` and `render` is the most common
self-inflicted slowdown in this workflow.

**This tool is the wrong choice when** the story needs footage it does not have, a real person's face or
likeness, articulated human or animal anatomy, a physical action performed continuously, or lip-sync. It
renders flat vector geometry, type, charts, maps, icons and colour-coded objects well, and those other
things badly. Say so instead of producing a lookalike: a drawn stand-in for archival material is a
provenance problem, not a style choice.

## 2. The workflow, in order

One beat = one sentence = one shot. Timing comes from measured speech, never from invention.

1. **Brief.** Subject, audience, platform, language, whether there is narration. Ask for a missing subject;
   do not ask whether to narrate when a video was requested.
2. **Storyboard before HTML** — `references/narration-and-captions.md`. The caption is the verbatim spoken
   words, not a summary of them. For a history, company or invention film the through-line is **one person
   making decisions**, not a list of products and dates: one beat = one decision or one consequence. A
   timeline of launches reads as a slide deck however good the art is.
3. **Narrate and measure.** `python scripts/deepseek_voice.py beats beats.json film/assets/voice.wav
   --voice stella --timeline timeline.json`, then `gate` to check every phrase by ASR. Route, voices and
   limits: `references/narration/deepseek-tts.md`.
4. **Build the page** from `timeline.json`, not from the storyboard. Contract: `references/cli.md`.
   **Every visual asset is commissioned from the image-capable agent — never draw, trace or procedurally
   paint one yourself, not even a plain background plate.** Self-made stand-ins read as stickers and come
   back as a rejection; briefing, cropping and assembly are your job, the art is not. Method:
   `references/generated-assets.md`.
5. **Check, then look.** `pulupulu check .`, then `pulupulu still . --at 2,12,24 --out .om/stills` and open
   the stills. A page that passes `check` can still render blank.
6. **Render** — `pulupulu render . --format mp4 --fps 30`. Stalls, black frames and wrong lengths:
   `references/render-traps.md`.
7. **Mix and mux** with explicit stream mapping — `scripts/deliver_check.py --video out/film-vN.mp4
   --audio assets/mix.wav --out out/final.mp4` muxes *and* validates in one call. Manual recipe and the
   ducking chain: `references/workflow.md`.
8. **Validate the file you will deliver**, not the renderer's newest output:
   `python scripts/deliver_check.py out/film.mp4 --timeline timeline.json`.
9. **Deliver** with honest caveats: what is drawn rather than sourced, and what the QA note says.

## 3. Gates

Only these block. Everything else a tool prints is a reading note: answer it with an argument or fix it,
but never report it as passed when it was not.

| gate | command | what it proves | if it fails |
|---|---|---|---|
| preflight | `python scripts/doctor.py` | the machine can render | stop, report what is missing |
| composition | `pulupulu check .` | page contract, no missing file | fix before rendering |
| language | `python scripts/lang-audit.py film/index.html --lang en` | no text in the other language, **including string literals inside `<script>`** | translate the literal, re-run |
| speech | `python scripts/deepseek_voice.py gate beats.json --voice stella` | every phrase transcribes back to its own words | rewrite the phrase; never ship a fragment |
| file | `python scripts/deliver_check.py out/film.mp4 --timeline timeline.json` (or `--video/--audio/--out` to mux first) | frame size, frame rate, audio present and long enough, true peak, delivery size | re-mux or re-encode |
| pops | `pulupulu qa out/film.mp4` | `no single-frame pops` | find the one-frame element |

`pulupulu qa` also reports motion per second, `still for ≥ 1 s` and `flat opening`. Those are judgements
about pacing, measured on a 96×54 greyscale comparison, so a low-contrast slow move can read as still. Use
them as a reason to look, not as a verdict to obey.

**What no gate proves:** that the film is good, that ASR heard the right number (check digits and proper
nouns as tokens), or that a caption sits where a platform's UI will not cover it.

## 4. Traps that cost a render

Full detail and fixes in `references/render-traps.md`. The ones that stop a render dead:

- Raw `<g>`/`<rect>`/`<path>` written into a `<div>` renders nothing and warns nothing. Wrap every scene
  fragment in its own `<svg viewBox>`.
- A webfont inside inline SVG `<text>` re-rasterises that layer every frame. Put text in HTML, or draw it
  as shapes.
- `feTurbulence` as a per-frame filter — inline SVG *or* a CSS background — stalls the renderer. Bake the
  noise into a PNG tile once.
- A full-frame GSAP **scale** on an inline SVG re-rasterises the plate; translate composites fine, and a
  bitmap layer can be scaled. When a push is impossible, animate small inner groups.
- `repeat: -1` makes the timeline infinite: an 87 s film silently becomes 117 s. Compute finite laps.
- After a failed render, clear the stale `om-chrome-*` profiles in Temp — a few leftovers make **every**
  render time out on frame one, including the CLI's own blank template. Then kill only the **headless**
  Chrome left behind; `taskkill //IM chrome.exe` closes the user's own browser.
- Paint cost has a cliff around ~1000 px per full-alpha bitmap layer, and `drop-shadow` on a transforming
  layer costs the same as a filter per frame. Bake the shadow into the PNG, animate a wrapper `<div>`.
- **Stamp `data-om-signature="off"` on the film element.** Without it the renderer draws a `Made with …`
  mark into the last frame, and a client-facing deliverable carries no tool credit.

## 5. Where the detail lives

| working on | page |
|---|---|
| commands, page contract, install | `references/cli.md` |
| the nine steps, project contract, mux | `references/workflow.md` |
| storyboard, captions, one-language gate | `references/narration-and-captions.md` |
| palette, element budget, personality, rhythm | `references/design-taste.md` |
| motion languages, techniques, 3D layer | `references/motion-library.md` — §8 holds the paper-theatre recipe and `templates/paper-theatre.html` |
| GSAP plugins (all free), seek-safe triage, shake/debris/SplitText/DrawSVG recipes | `references/gsap-plugins.md` |
| a shot needs an asset that does not exist yet, or needs one repaired | `references/self-healing.md` + `scripts/asset_gen.py` |
| punch-up, product demo, talking head, grammars | `references/workflows-specialized.md` |
| music worlds, composer, sfx, narration synthesis | `references/audio-and-music.md`, `references/narration/deepseek-tts.md` |
| a blank, stalled or wrong-length render | `references/render-traps.md` |
| what to check, and in what order | `references/verification.md` |
| style recipes, camera language | `references/art-motion/INDEX.md` |
| sourcing icons and vectors, licences | `references/asset-sourcing.md` |
| art generated by an image model, cropping prints, mounting | `references/generated-assets.md` |
| flat-vector craft, scrolling worlds | `references/2d-vector-motion.md` |
| which subjects this renderer can carry | `references/topic-fit.md` |
| timing and easing at sub-second level | `references/ui-motion/` |
| publishing this skill (one commit, v1.0) | `references/publishing-skills.md`, `references/publishing.md` |

The style-recipe route (`scripts/art-motion/engine/`) is **20 MB of vendored runtime that is deliberately not
in this repository**: a skill should not make every agent fetch an engine it may never use, and a 37 MB tree
cannot be reviewed. It installs pinned and checksum-verified, onto the exact paths the pages above cite:

```sh
python scripts/install_art_motion.py --check                   # is it there?
python scripts/install_art_motion.py                           # core: lib + demos + scenes, 20 MB
python scripts/install_art_motion.py --with-reference-films    # + study material, 14 MB more
```

Everything else — the Python gates, the clip specs, the documentation — is in the repository and needs no
install. Never commit the fetched tree back: `.gitignore` already covers it.

## 6. Scripts

| script | does |
|---|---|
| `scripts/doctor.py` | preflight, read-only |
| `scripts/deepseek_voice.py` | `probe · speak · cost · lay · beats · asr · gate` — narration and its measured timeline |
| `scripts/deliver_check.py` | validates the delivered file: size, rate, audio, peak, duration against the timeline |
| `scripts/lang-audit.py` | one-language gate over markup **and** script literals |
| `scripts/art-motion/icon_audit.py` | icon families, colour count, contact sheet |
| `scripts/art-motion/qa.py` | pacing and pop heuristics on a rendered file |
| `scripts/stamp_credit.py` | adds the `by Alucard0x1` line to text files |

## 7. Working with a person

Show frames, not adjectives. One hero frame per act kills a week of wrong work. When they correct you, put
the correction into this skill rather than into a chat reply.

Handoffs: narration timing and prosody → skill **`tts-intonation`** · merging or translating another
library → skill **`agent-skill-sourcing`** · rights and likeness before publishing → skill
**`media-content-safety`** · sourcing a reference video → skill **`streaming-mirror-extraction`** ·
3D or footage-based shots → skills **`headless-three-video-render`** and **`cinetic`** · type-first films
→ skill **`kinetic-typography`**.
