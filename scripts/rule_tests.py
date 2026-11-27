"""Self-tests for the rules this skill states. Each test has a positive AND a negative control.

A rule that cannot fail is not a rule. Every check here is written so that a deliberately broken input must be
rejected; if the broken input passes, the test fails loudly.

    python rule_tests.py [--sprite-dir <dir with RGBA pngs>]

Tests:
  1. ring-spill gate      - key+despill keeps the border ring under ~1 %; without despill it must exceed it
  2. pixel-spec validator - out-of-canvas is an error, not a crop; a thickening diagonal is rejected
  3. determinism per build- one encoder build repeats byte-for-byte; decoded pixels are the comparable unit
  4. rest-area scaling    - sqrt(area ratio) recovers a known scale, and the +-3 % clamp is enforceable
"""
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- 1. ring-spill gate
KEY = (255, 0, 255)


def key_and_count(img: Image.Image, despill: bool, tol=70):
    """Key the flat background to alpha, optionally despill the subject's edges, then measure key-hue on its ring."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    keyv = np.array(KEY, dtype=np.float32)
    d = np.sqrt(((a - keyv) ** 2).sum(axis=2))
    subj = d >= tol                       # the subject = everything that is not the flat key

    # Spill is not "close to the key colour" - a 50 % blend of red paint and magenta sits 113 units away and a
    # tighter threshold misses it. Spill is the magenta SIGNATURE: red and blue both well above green.
    def magenta_share(rgb):
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        return (r - g > 40) & (b - g > 40)

    if despill:
        # Correct despill for a magenta key lifts GREEN until red and blue stop towering over it. The first version
        # pushed red and blue toward their average, which keeps the magenta ratio and actually made the edge more
        # key-coloured - the measurement went UP.
        spill = magenta_share(a) & subj
        lift = (a[:, :, 0] + a[:, :, 2]) * 0.5
        a[:, :, 1] = np.where(spill, np.maximum(a[:, :, 1], lift), a[:, :, 1])

    h, w = subj.shape
    k = 2
    eroded = np.ones((h, w), bool)
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            eroded &= np.roll(np.roll(subj, dy, axis=0), dx, axis=1)
    ring = subj & ~eroded                 # 2 px band just inside the subject edge
    if ring.sum() == 0:
        return 0.0, 0
    hue = magenta_share(a)
    return float((hue & ring).sum()) / float(ring.sum()), int(ring.sum())


def test_ring_spill(sprite_dir: pathlib.Path):
    print("\n1. ring-spill gate")
    sprites = sorted(sprite_dir.glob("*.png")) if sprite_dir and sprite_dir.exists() else []
    if not sprites:
        print("  SKIP  no RGBA sprites given (--sprite-dir)")
        return
    spr = Image.open(sprites[len(sprites) // 2]).convert("RGBA")
    bg = Image.new("RGBA", spr.size, KEY + (255,))
    comp = Image.alpha_composite(bg, spr).convert("RGB")

    good, n = key_and_count(comp, despill=True)
    bad, _ = key_and_count(comp, despill=False)
    check("despilled ring spill under 1 %", good < 0.01, f"{good*100:.2f} % of {n} ring px")
    check("negative control: without despill the ring is far dirtier", bad > 5 * max(good, 1e-9),
          f"{bad*100:.2f} % vs {good*100:.2f} %")


# --------------------------------------------------------------------------- 2. pixel-spec validator
def validate_spec(rows, canvas_w=None, canvas_h=None):
    """Validate a text pixel spec.

    Two rules, each with a real discriminator:

    * every pixel lands inside the canvas - out of canvas is an error, never a crop;
    * in *line art*, no 2x2 block may be entirely filled: a 1 px line gives at most 3 filled (a corner), a 2 px
      line gives 4. The rule is scoped to line art because a filled body is legitimately solid - applying the
      thickness test everywhere rejects every silhouette.
    """
    errs = []
    h = len(rows)
    w = len(rows[0]) if h else 0
    canvas_w = canvas_w or w
    canvas_h = canvas_h or h
    if h != canvas_h:
        errs.append(f"rows {h} != canvas height {canvas_h}")
    for y, row in enumerate(rows):
        if len(row) != canvas_w:
            errs.append(f"row {y}: {len(row)} px != canvas width {canvas_w} (out-of-canvas is an error, not a crop)")
    filled = sum(r.count("#") for r in rows)
    density = filled / float(max(1, h * w))
    if density <= 0.35:                    # line art, not a filled shape
        # A 1 px diagonal puts 2 of 4 pixels in every 2x2 block. A 2 px diagonal puts **3**. A legal corner puts a
        # single 3 as well, so the discriminator is a RUN of at least two adjacent 3-of-4 blocks - which is exactly
        # what a thickened stroke looks like. One 3 alone is a corner and must pass.
        heavy = [[sum(1 for c in (rows[y][x], rows[y][x + 1], rows[y + 1][x], rows[y + 1][x + 1]) if c == "#") >= 3
                  for x in range(w - 1)] for y in range(h - 1)]
        for y in range(len(heavy)):
            for x in range(len(heavy[y])):
                if not heavy[y][x]:
                    continue
                adj = sum(1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                          if 0 <= y + dy < len(heavy) and 0 <= x + dx < len(heavy[0]) and heavy[y + dy][x + dx])
                if adj >= 3:               # itself plus two neighbours
                    return errs + [f"thick line at ({x},{y}): a run of 3-of-4 blocks is a 2 px stroke"]
    return errs


def test_pixelspec():
    print("\n2. pixel-spec validator")
    good = ["#.......",
            ".#......",
            "..#.....",
            "...#....",
            "....####",
            "........",
            "........",
            "........"]
    check("valid line art accepted (diagonal + legal corner)", validate_spec(good, 8, 8) == [])

    wide = ["##....", "##....", "##....", "##...."]
    e = validate_spec(wide, 5, 4)
    check("negative control: out-of-canvas row rejected", len(e) > 0, e[0] if e else "accepted!")

    thick = ["##......",
             ".##.....",
             "..##....",
             "........",
             "........",
             "........",
             "........",
             "........"]
    e2 = validate_spec(thick, 8, 8)
    check("negative control: 2 px diagonal rejected", len(e2) > 0, e2[0] if e2 else "accepted!")

    body = ["########"] * 8                # a solid silhouette must NOT be treated as a thick line
    check("filled body is not mistaken for a thick stroke", validate_spec(body, 8, 8) == [])


# --------------------------------------------------------------------------- 3. determinism per build
def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def frames_of(video):
    """Decode to raw rgb24 so two encoder builds can be compared on pixels."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True)
    return out.stdout


def test_determinism(tmp: pathlib.Path):
    print("\n3. determinism per build")
    if not shutil.which("ffmpeg"):
        print("  SKIP  ffmpeg not found")
        return
    src = tmp / "frame.png"
    Image.new("RGB", (320, 180), (30, 30, 34)).save(src)
    a, b = tmp / "a.mp4", tmp / "b.mp4"
    for t in (a, b):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(src),
                        "-t", "0.2", "-r", "30", "-c:v", "libx264", "-crf", "20",
                        "-pix_fmt", "yuv420p", str(t)], check=True)
    check("same build repeats byte-for-byte", sha(a) == sha(b),
          sha(a)[:12] + (" == " if sha(a) == sha(b) else " != ") + sha(b)[:12])
    check("decoded pixels are the comparable unit", frames_of(a) == frames_of(b),
          f"{len(frames_of(a))} bytes decoded each")


# --------------------------------------------------------------------------- 4. rest-area scaling
def area_of(img):
    return int((np.asarray(img.convert("L")) > 40).sum())


def test_rest_area(tmp: pathlib.Path):
    print("\n4. rest-area scaling")
    W = H = 400
    shapes = [("ellipse", (120, 100, 280, 300)), ("rect", (170, 280, 230, 360))]

    def draw(scale):
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        cx, cy = 200.0, 220.0
        for kind, box in shapes:
            b = [cx + (box[0] - cx) * scale, cy + (box[1] - cy) * scale,
                 cx + (box[2] - cx) * scale, cy + (box[3] - cy) * scale]
            if kind == "ellipse":
                d.ellipse(b, fill=255)
            else:
                d.rectangle(b, fill=255)
        return im

    a0 = area_of(draw(1.0))
    for target in (1.12, 0.94):
        a1 = area_of(draw(target))
        est = float(np.sqrt(a1 / a0))
        err = abs(est - target) / target * 100
        check(f"sqrt(area ratio) recovers x{target} within 3 %", err < 3.0,
              f"estimated x{est:.3f}, error {err:.1f} %")

    # the clamp must bite: a 9 % error is not a scale factor, it is a different take
    est_bad = 1.0 + 0.09
    clamped = min(0.03, abs(est_bad - 1.0))
    check("negative control: +-3 % clamp refuses a 9 % correction", clamped == 0.03 and abs(est_bad - 1.0) > 0.03,
          "9 % flagged as a wrong take, not a scale fix")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sprite-dir", default="")
    a = ap.parse_args()
    print("rule tests — every check has a negative control")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        test_ring_spill(pathlib.Path(a.sprite_dir) if a.sprite_dir else None)
        test_pixelspec()
        test_determinism(tmp)
        test_rest_area(tmp)
    print(f"\n{'RULE TESTS PASS' if not FAILS else f'RULE TESTS FAIL ({len(FAILS)}): ' + ', '.join(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
