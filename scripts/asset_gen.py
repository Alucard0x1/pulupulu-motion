#!/usr/bin/env python3
# by Alucard0x1
"""Generate and validate a plate or cut-out asset for a film, from a written brief.

A film that needs a better explosion, a truer ship or a missing cut-out must be able to make that asset and
prove it is usable, without a human in the loop. This script is that loop:

    brief (JSON)  ->  image model  ->  validation against the film's own rules  ->  manifest entry

Validation is the part that matters. A generator will happily return a JPEG-looking PNG with no alpha, a
white card behind the subject, or a palette that fights the film. Those are checked here, and a failing asset
is reported as a failure instead of being wired into a timeline where it is impossible to diagnose later.

Usage:
    python asset_gen.py briefs.json            # run every entry
    python asset_gen.py briefs.json --only s6  # one entry
    python asset_gen.py briefs.json --check    # validate existing files, generate nothing

Brief entry:
    {
      "name": "s6_ember_vent",
      "kind": "cutout" | "plate",
      "size": [512, 512],                # required for cutout; ignored for plate
      "min_alpha": 0.35,                 # cutout: fraction of pixels that must be transparent
      "palette": ["#14120f", "#c8452a"],  # every one of these must appear within tolerance
      "prompt": "…the full visual brief for the model…"
    }
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TOLERANCE = 26  # per-channel distance accepted when checking palette presence


def run_model(prompt, out_path, workdir):
    """One image-generation call. codex takes the prompt on stdin; -i would swallow it."""
    # on Windows the CLI is a .cmd shim: subprocess with shell=False will not find a bare "codex"
    exe = None
    for candidate in ("codex", "codex.cmd", "codex.exe"):
        exe = shutil.which(candidate)
        if exe:
            break
    if not exe:
        return 127, "codex CLI not found on PATH"
    cmd = [exe, "exec", "--skip-git-repo-check", "-m", "gpt-6.2-sol",
           "-c", "model_reasoning_effort=medium", "--add-dir", workdir.replace("\\", "/")]
    # the prompt must end with the flat instruction to save, because the agent has a filesystem
    text = (prompt.strip() + "\n\n"
            "Save the result as exactly this path, overwriting if present:\n"
            f"{out_path}\n"
            "Do not create any other file. Do not describe the image back to me; just generate and save it.\n")
    proc = subprocess.run(cmd, input=text.encode("utf-8"), cwd=workdir,
                          capture_output=True, timeout=900)
    return proc.returncode, proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def validate(path, entry):
    """Return a list of problems. Empty list means the asset may be used."""
    problems = []
    if not os.path.exists(path):
        return [f"file was not created: {path}"]
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    width, height = img.size

    if entry.get("kind") == "cutout":
        alpha = img.split()[3]
        transparent = sum(1 for v in alpha.getdata() if v < 8) / (width * height)
        if transparent < entry.get("min_alpha", 0.3):
            problems.append(f"only {transparent:.1%} of the pixels are transparent — this is not a cut-out")
        # a card or a frame shows up as fully opaque rows or columns at the edges
        corners = [alpha.getpixel(p) for p in
                   ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))]
        if all(c > 240 for c in corners):
            problems.append("all four corners are opaque — the generator drew a background card")
        want = entry.get("size")
        if want and (width, height) != tuple(want):
            problems.append(f"size {width}x{height} != requested {want[0]}x{want[1]} (resize only if the art allows it)")

    for colour in entry.get("palette", []):
        target = hex_to_rgb(colour)
        pixels = img.convert("RGB").getdata()
        step = max(1, len(pixels) // 40000)
        found = False
        for index, pixel in enumerate(pixels):
            if index % step:
                continue
            if all(abs(pixel[i] - target[i]) <= TOLERANCE for i in range(3)):
                found = True
                break
        if not found:
            problems.append(f"palette colour {colour} is missing from the image")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("brief")
    parser.add_argument("--only", help="run one entry by name")
    parser.add_argument("--check", action="store_true", help="validate existing files only")
    parser.add_argument("--outdir", default=os.getcwd())
    args = parser.parse_args()

    entries = json.load(open(args.brief, encoding="utf-8"))
    if isinstance(entries, dict):
        entries = entries["assets"]

    failures = 0
    for entry in entries:
        if args.only and entry["name"] != args.only:
            continue
        path = os.path.join(args.outdir, entry["name"] + ".png")
        print(f"== {entry['name']} ({entry.get('kind', 'cutout')})")
        if not args.check:
            code, log = run_model(entry["prompt"], path, args.outdir)
            if code != 0:
                print(f"   model exited {code}")
                print("   " + "\n   ".join(log.strip().splitlines()[-6:]))
        problems = validate(path, entry)
        if problems:
            failures += 1
            for problem in problems:
                print(f"   FAIL {problem}")
        else:
            size = Image.open(path).size
            print(f"   ok  {path}  {size[0]}x{size[1]}")

    print(f"\n{failures} asset(s) failed validation")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
