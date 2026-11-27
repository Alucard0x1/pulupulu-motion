"""Build tiny test videos, each broken in exactly one way, to prove the video gates discriminate.

A gate that never fails is decoration. These fixtures are deliberately bad in one measurable property each, plus one
clean control that must pass. They are 320x180 and about 2 seconds, so the whole set builds in seconds.

    python video_fixtures.py --out <dir>
    # then: python video_audit.py <dir>/clean.mp4     -> must PASS
    #       python video_audit.py <dir>/frozen.mp4    -> must FAIL on the freeze gate

Fixtures:
    clean.mp4       a moving pattern and a dynamic audio bed at -14 LUFS   -> PASS
    frozen.mp4      one still frame held for the whole duration           -> FAIL freeze
    silent.mp4      picture with a digitally silent track                 -> FAIL silence
    clipped.mp4     loud, peak-limited-to-0 dB audio                      -> FAIL true peak
    hissy.mp4       white-noise bed with almost no low end                -> WARN bands
    black.mp4       two seconds of black with a quiet tone                -> WARN black frames
    drift.mp4       a locked composition that translates 40 px over time  -> FAIL static camera
"""
import argparse
import pathlib
import subprocess
import tempfile

W, H, DUR, FPS = 320, 180, 2.0, 30


def ff(args, **kw):
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + args, check=True, **kw)


def still(path, text="TEST", bg=(24, 24, 28), fg=(230, 230, 225)):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 34)
    except Exception:
        f = ImageFont.load_default()
    d.text((16, 16), text, font=f, fill=fg)
    d.rectangle([16, H - 60, W - 16, H - 20], outline=fg, width=2)
    im.save(path)
    return path


def build(out: pathlib.Path):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        # ---- clean: a pattern that actually changes every frame, plus a bed with dynamics
        base = still(td / "b.png", "CLEAN")
        ff(["-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate={FPS}:duration={DUR}",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={DUR}",
            "-filter_complex",
            "[1:a]volume='0.25*(0.5+0.5*sin(2*PI*t*3))':eval=frame,volume=1.0[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(out / "clean.mp4")])

        # ---- frozen: one still held
        ff(["-loop", "1", "-i", str(base), "-t", str(DUR), "-r", str(FPS),
            "-f", "lavfi", "-i", f"sine=frequency=300:duration={DUR}",
            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
            "-shortest", str(out / "frozen.mp4")])

        # ---- silent: moving picture, digitally silent audio
        ff(["-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate={FPS}:duration={DUR}",
            "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={DUR}",
            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(out / "silent.mp4")])

        # ---- clipped: loud, slammed against 0 dBFS
        ff(["-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate={FPS}:duration={DUR}",
            "-f", "lavfi", "-i", f"sine=frequency=180:duration={DUR}",
            "-af", "volume=12dB,alimiter=limit=0.999:level=0", "-c:v", "libx264", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out / "clipped.mp4")])

        # ---- hissy: white noise, high-passed so there is no low end at all
        ff(["-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate={FPS}:duration={DUR}",
            "-f", "lavfi", "-i", f"anoisesrc=d={DUR}:c=white:a=0.3",
            "-af", "highpass=f=800", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(out / "hissy.mp4")])

        # ---- black: black picture
        ff(["-f", "lavfi", "-i", f"color=c=black:size={W}x{H}:rate={FPS}:duration={DUR}",
            "-f", "lavfi", "-i", f"sine=frequency=240:duration={DUR}",
            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(out / "black.mp4")])

        # ---- drift: text that translates across the frame (a camera that moves when it claimed not to)
        for i in range(int(DUR * 12)):
            from PIL import Image
            im = Image.open(base).copy()
            shifted = Image.new("RGB", (W, H), (24, 24, 28))
            shifted.paste(im, (int(-40 + 80 * i / (DUR * 12 - 1)), 0))
            shifted.save(td / f"d{i:03d}.png")
        ff(["-framerate", "12", "-i", str(td / "d%03d.png"), "-f", "lavfi",
            "-i", f"sine=frequency=300:duration={DUR}", "-c:v", "libx264", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out / "drift.mp4")])

    names = sorted(p.name for p in out.glob("*.mp4"))
    print(f"built {len(names)} fixture(s) in {out}: " + ", ".join(names))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    build(pathlib.Path(a.out))


if __name__ == "__main__":
    main()
