# Self-healing: making the asset a shot needs

A review that ends with "the explosion does not read" is a **missing-asset** problem as often as a
**missing-tween** problem. The skill has to be able to author that asset, validate it, wire it in and prove it,
without asking a human to draw anything.

## Decide first: regenerate, cut, or composite

| the frame is wrong because… | do this |
|---|---|
| the subject is absent (no fissure on the cone, no rock chunks, no foam) | **generate** one cut-out with `scripts/asset_gen.py` |
| the subject exists but is the wrong size, the wrong part, or needs a mirrored copy | **cut** it out of the existing plate with PIL — cheaper and guaranteed on-style |
| the subject exists and the motion is wrong (a circle where an ellipse belongs, a blob where rock belongs) | **composite**: geometry shader/primitive plus the existing texture. This is a code fix, not an asset fix |
| the palette fights the film | recolour the existing asset; a new generation will drift further |

Generating a replacement for an asset that already works is the most common wasted hour: the new art will not
match the line weight of the rest of the film, and every other shot will look like a different illustrator drew
it. Generate for **additions**, cut for **variations**, code for **behaviour**.

## The brief is a contract, not a description

`scripts/asset_gen.py` takes a JSON list of briefs and runs each through the image model, then validates the
result. A brief that omits any of these comes back unusable:

```json
{
  "name": "s6_ember_vent",
  "kind": "cutout",
  "size": [512, 512],
  "min_alpha": 0.55,
  "palette": ["#14120f", "#c8452a"],
  "prompt": "…"
}
```

Rules that every prompt must carry, because generators default to the opposite of each:

- **Name the palette in hex**, and say which colour is the outline, which is the fill, which is the highlight.
- **"NO background, NO paper card, NO rectangle, NO vignette, NO shadow under the object — everything outside
the silhouette is fully transparent (alpha 0)."** Without this sentence you get a white square with a drop
  shadow, which is the single most common reason a cut-out cannot be used.
- **State the style anchor**: "flat paper-theatre cut-out, thick ink outline, flat fills, no gradients, no
  photorealism", plus the line weight relation to the rest of the film ("the same line weight as a linocut").
- **State the size it must read at**, in output pixels: "must read clearly at 120 px wide". A generator asked for
  a 512 px asset draws detail that turns to mush at the size the film actually uses it.
- **For a sprite sheet**: one horizontal row, N equal cells, WxH each, "a 6 pixel empty margin on every side of
  every cell so they can be sliced apart", and "NO numbers, NO labels, NO grid lines".
- **Say what it will be composited onto.** "It will be overlaid on a mountain to show it splitting open" gets a
  silhouette with a clear bottom edge; without it you get a floating object.

## Validation gates (what the script refuses)

`asset_gen.py --check` re-runs only the checks, no generation:

- **alpha fraction** — a cut-out with less than `min_alpha` transparent pixels is a picture, not a cut-out.
- **corner opacity** — all four corners opaque means a background card was drawn.
- **palette presence** — every hex in `palette` must appear within a tolerance of 26 per channel. This is what
  catches "the ember is now orange-red instead of `#c8452a`", which is invisible until it sits next to the rest
  of the film.
- **size** — a mismatch is a warning in the log, not an automatic resize: downscaling a card-backed image does
  not remove the card.

A failing asset is **never** wired into a timeline. Report the failure and fix the brief.

## The loop

1. **Measure the deficiency in the frame**, not in your head: render the exact second, look at it, and name what
   is missing in the picture ("the cone has no fissure at the moment of rupture").
2. **Choose regenerate / cut / composite** from the table above.
3. **Write the brief** with every clause from the list above.
4. **Generate and validate**: `python scripts/asset_gen.py briefs.json`. Read the log; a `FAIL` line is the
   brief's fault, not the model's.
5. **Slice before the GPU** if it is a sheet — cells to separate PNGs at display size, with the alpha bbox
   trimmed (`_tight.png`), because that is what the texture budget is set against.
6. **Wire it into the timeline** with a `spriteSheet`/`layer` call, sized relative to the *subject* (a rock chunk
   on a 3.2-unit island is 0.2 units, not 0.9), and give every cell its own velocity if it is a burst.
7. **Render one still at the event's second and look at it.** The still is the only proof.
8. **Record the lesson** in this file only if it generalises; otherwise it belongs in the project's notes.

## When a new asset is the wrong answer

The complaint "it does not feel alive" is usually **not** an asset problem. Before generating anything, check
whether the existing assets already move:

- a wash over the whole frame at impact (a full-frame white quad) makes the paper look grey — that is a code
  bug and no new asset fixes it;
- a shockwave drawn as a perfect circle around a mountain reads as a hoop; the fix is an ellipse in perspective
  anchored at the waterline, again a code fix;
- a static composition gives motion nowhere to read, whatever is generated for it.

If the frame is already full of correctly-drawn assets and still feels dead, the fix is timing and staging.
Generating more art makes the diagnosis harder, not easier.

## Model-call mechanics that waste a whole attempt

- `codex exec` reads its prompt from **stdin**; `-i` is variadic and will swallow an inline prompt ("No prompt
  provided via stdin"). Put the save path in the prompt text and let the agent write the file.
- Pass the working directory as a **native** path (`C:/…`, forward slashes). An MSYS path like `/c/…` fails with
  `The system cannot find the file specified` because the binary is not an MSYS program.
- The model reports success in prose whether or not it wrote the file. Only `os.path.exists` plus the validation
  gates count.
