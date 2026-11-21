# Design taste: theme, elements, motion, colour, rhythm

# by Alucard0x1

What a directed frame looks like in this renderer: element budget, personality sliders, palettes, contrast curves.

Part of the `pulupulu-motion` skill. The entry point and the gate table live in `SKILL.md`.

## 3e. Design taste: theme, elements, motion

Taste is not decoration, it is a series of defensible defaults. Decide these before the first frame and write them into `treatment.md`.

### Ground: dark or light

| The film is about | Ground | Why |
|---|---|---|
| infrastructure, servers, terminals, security, night, uptime, gaming, music, a launch at night | **dark** | the subject *is* the dark; status colours glow, codes read as light |
| data reports, editorial, teaching, health, daylight service, documents, a light product UI | **light** | matches the artifact, reads faster at a glance, prints well |
| an emotional or cinematic story | **dark, desaturated** | falls back, lets one accent carry feeling |
| a product whose own UI is light | **light** | the screen must match the product, never invert it |

Rules: dark ground = one luminous accent + a 3-step value ramp, never `#000`; light ground = a warm or cool off-white, never `#fff`, with an ink accent. **Flip the ground at most once per film**, and only on a story beat (a flood, a verdict, the drop).

### Element budget (what may exist in a frame)

- **Three zones, one each:** headline, artifact (diagram / chart / object / UI), caption. Nothing else competes.
- **Colour:** 3 hues + a neutral ramp; accent ≤ 5% of pixels; state colours are reserved (red = failure, amber = warning, green = healthy) and never reused decoratively.
- **Type:** at most 2 families (display + text), scale contrast ≥ 3× between the largest and the body, captions ≥ 56 px at 1080 wide, contrast ≥ 4.5:1.
- **A hero label sitting on a prop takes that prop's contrast, not the act's ground colour.** `color: ink` is right for a label on the background and invisible for the same label on a light sheet inside a dark act — a price stamp on paper, a caption over a cream card. Pass an explicit colour when the label's backdrop is an object; `om check` reports `low-contrast … 1.2:1` and the words simply are not there.
- **Nothing without a job.** A border, glow, rule or icon that carries no meaning gets deleted. Density is a genre decision: explainer = dense cards, launch = one hero object, data story = chart + one number, kinetic = type only.

### Motion register (match the subject, not your mood)

| Subject | Motion |
|---|---|
| systems, infra, code | snap into a grid, `expo.out`, hard cuts, terminals typing |
| data, numbers | count-up, bars from zero, draw-on, one turning point |
| hardware, objects | camera in space, rack focus, one slow orbit |
| human, emotion | long eases, small moves, no bounce |
| lists, chapters | one-word-at-a-time type, wipe, chapter counter |

One move per beat; exits faster than entrances; never drift every element at once. A reading hold still gets a 1–3% push so the frame is never a freeze.

### Composition of a flat scene (no depth to hide behind)

Drawn-vector scenes fail in three ways no checker sees:

- **Seat every object on its surface, arithmetically.** A subject placed by eye (a train at `y: 600` over rails at `y: 886`) floats or sinks. Compute `top = surfaceY - objectHeight` from the same constant the surface uses, and keep one `HORIZON`/`BED` constant per film so all scenes share one geometry.
- **A generated scene is drawn in the frame's coordinates, not the frame's size.** Scene helpers authored around a comfortable `y 600–1300` band leave a 1080×1920 frame two-thirds empty, and `om qa` reads the result as a still film. Rather than re-lay out every scene, put a static CSS scale on the scene wrapper — `.art { transform: scale(1.5–1.8); transform-origin: 50% 40% }` — then re-open the widest and tallest scenes to check nothing crops. Keep that transform static: animating it is the full-frame-tween render trap in the field notes below.
- **The bottom quarter is where flat films look cheap.** A backdrop helper that stops at `y ≈ 800` leaves 40% of a 1920 frame as a single value. Carry the ground texture (scatter, ballast, stones) to the frame edge and add two or three foreground shapes; empty ground under a caption reads as unfinished.
- **A caption over mid-value ground needs a scrim — and the scrim belongs inside the shot, not above it.** White text plus a black outline still vanishes over a brown or grey field at partial opacity, so put a `linear-gradient` behind the caption band and keep the caption topmost *within the beat*. A single global scrim `<div>` placed after the beats paints over every caption, because `z-index` on the caption only ranks it inside its own parent's stacking context: `om check` then reports `text-covered` once per caption and the render shows the words at ~15% opacity. One scrim per beat, between the art and the `.capbox`.

### Taste checks before a render

Squint test at 25% scale (hierarchy must survive) · greyscale test (value, not hue, must carry the hierarchy) · phone test at 1080 width · count the colours, fonts and accents out loud · "could this frame be about a different subject?" — if yes, it is a template; change the ground or the type rather than the easing.

## 4. Director System: Shape, Personality & Taste Rules

### Message Shape → Motion Language
| Shape | Sounds like | Natural languages | Avoid |
|---|---|---|---|
| **Claim / feeling** | "Introducing X." | `kinetic-type`, `generative-field`, `3d-object`, brand ident | UI tour |
| **Workflow** | "Type this, get that." | `cursor-demo`, `continuous-morph` | abstract shapes, no product |
| **Mechanism** | "Here is why it works." | `mechanism`, `system-diagram`, `flat-world` | fast cut reel |
| **Evidence** | "Signups doubled." | `data-story`, `editorial-collage` | unreadable flashing numbers |
| **List** | "Five new things." | `kinetic-type` chapters, `modular-grid`, `card-montage`, `continuous-morph` | five equal slides |
| **Transformation** | "Before / after." | `continuous-morph`, `data-story`, split compare | hard cut between two stills |
| **Story** | "An agent wakes up…" | `talking-head`, `photo-led`, `character`, `flat-world`, `hand-drawn` | bullet points |
| **Showcase** | "Look what it can do." | one deep artifact (`mechanism`, `3d-object`), `showreel`, `art-styles` | feature list |

### Five Personality Sliders (-2 to +2)
Score from product evidence (site type, copy, UI) and summarize in one sentence (e.g., *"Precise, calm, premium, technical, new — Linear-like"*):
- **precise ↔ playful**: easing (hard `expo.out`/linear → `OM.spring` with overshoot) & shape (grids → blobs).
- **calm ↔ energetic**: tempo (80–100 → 125–150 BPM), shot length, cut density. *(Note: Launch films default to energetic 100–125 BPM with 15–33 cuts/min and a 5–8 cut burst even for calm brands; brand calm sets palette/type/eases, not energy, unless user asks for calm or it's an ambient loop.)*
- **premium ↔ accessible**: negative space, type scale contrast, colour count, screen density.
- **technical ↔ human**: monospace/code/diagrams vs photos/faces/hand-drawn warmth.
- **established ↔ new**: restraint & continuity vs bold, surprising, meme-literate.

### Film-Wide Taste Rules (Defaults)
1. **Start moving.** Frame 0 has the subject in it and is already moving or unresolved. Never open on a blank card or lone glowing dot on black.
2. **Choose the route intentionally.** Continuous (0–2 cuts, UI recordings), Montage (beat-locked cuts), or Hybrid (continuous spine + montage bursts — best for tech launches).
3. **Energy has a shape.** Hook ≤ 3 s, climb in steps, burst at 30–60%, hero on the drop, resolve on the mark.
4. **Real product.** Rebuilt UI or real captures/recordings. Never grey boxes, invented UI, or panned static screenshots.
5. **Craft shows at rest.** Every hold is a poster: real font (`om fonts`), weight contrast, tabular numerals (`font-variant-numeric: tabular-nums`), clean alignment.
6. **Sound matches format.** Short UI films/loops (< 20 s) must read muted; > 30 s or with people are sound-led.
7. **End right.** Launches end on the mark (URL optional); showcases/lists/loops return to frame 0.
8. **Give something to take.** Saves come from reusable artifacts (prompts on screen, named lists, labelled specs).
9. **Not a template.** The product's own colours, shapes, and vocabulary must generate the motion.

---

## 5. Colour System

**Find colours before inventing any** (document source in `Palette: ... — from: <source>`):
1. **Brand's own values:** site CSS custom properties, `theme-color`, logo SVG, app icon.
2. **Product itself:** sample real UI screenshots, hardware finish, or product outputs.
3. **Material world of the idea:** sample real photography of the physical domain (paper, clay, phosphor, anodized metal).
4. **Invention (last resort):** label `"invented: no brand colours found"`.

**System roles:** `ground` (most of frame) · `surface` (~20%, 1–2 steps off ground) · `ink` & `muted ink` (neutral white/black, ≥ 4.5:1 contrast for small text) · `accent` (~1–5%, marks only the active/new thing) · `flood` (optional full-screen accent on a beat).
- **Value first:** Desaturate a still — hierarchy must still read in greyscale.
- **Light is part of colour:** Subtle vignette, falloff, or seeded grain (3–6% opacity); flat hex fills read as slides.
- **Avoid the AI house-look** (unless the brand itself actually uses these exact hexes):
  - Dark ground + warm accent (terracotta/amber/vermilion) + bone/cream type.
  - Warm off-white/cream ground + serif/giant grotesk + terracotta accent.
  - Near-black + acid lime/green; purple-to-blue gradients; neon on GitHub-dark.

---

## 6. Rhythm & Contrast

Boring = 1 event every 4–5 s, same move every scene, 0.6–0.8 s soft eases everywhere, flat pad music.

| Stretch | Bars | Energy (0–10) | Events / bar (4 beats) | Shot / move length |
|---|---|---|---|---|
| **Hook** | 1–2 | 6–7 | 2–4 | 0.25–0.5 s moves; onset ≤ 3 s |
| **Build** | 3–6 | 5 → 7 | 2–4, rising | 1–2 beats per move |
| **Stop** (optional) | 1 | 1 | 0–1 | hold 1–2 beats (0.5–1.6 s) |
| **Peak / Montage** | 4–8 | 9–10 | 4–8 (5–8 cuts in ~5 s at 30–60%) | ½–1 beat per shot |
| **Resolve / Mark** | 2 | 4 | 1–2 | hold ≥ 1.5 s on mark (with 3–6% linear drift) |

**Fixed rule:** No stretch > ~2 bars without a new event (outside a planned stop).
**Contrast schedule:** Change **≥ 2** of these at every section boundary (and all at the drop):
- **Shot scale** (ECU detail ↔ wide system) · **Speed** (0.25 s snap ↔ 2 s glide, speed ramps) · **Ease family** (`expo.out` tech ↔ `OM.spring` physical) · **Camera** (still ↔ drift ↔ whip) · **Density** (1 object ↔ 3×3 grid) · **Colour/ground** (flip or flood) · **Music texture** (half-time ↔ full beat ↔ stop ↔ drop).

**Beat-locked montage pattern:**
```js
OM.music({ bpm: 128 });
const B = (n) => OM.beat(n);
const shots = gsap.utils.toArray('.shot');
const beats = [2, 2, 1, 1, 1, 1, 0.5, 0.5, 0.5, 0.5]; // accelerate into stop
let t = B(32);
tl.addLabel('scene:montage', t);
shots.forEach((el, i) => {
  const cutT = (Math.floor(t * 30) + 0.5) / 30; // half-frame in for --blur
  tl.set(el, { autoAlpha: 1 }, cutT);
  if (i) tl.set(shots[i - 1], { autoAlpha: 0 }, cutT);
  tl.fromTo(el, { scale: 1.12 }, { scale: 1, duration: B(beats[i]), ease: 'none', immediateRender: false }, cutT);
  OM.sfx('hit', cutT, { gain: 0.45, pitch: 1 + i * 0.04 });
  t += B(beats[i]);
});
```

---
