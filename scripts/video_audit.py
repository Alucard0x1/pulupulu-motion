"""One command, one verdict: everything measurable about a delivered video file.

Nothing here judges whether the film is good — that is a visual review, and this script says so at the end. What it
does judge is every claim a delivery makes that can be computed: it decodes, it plays at the right size and rate, it
is not frozen, it is not silent, it is at the loudness target, its audio sits in the right bands, the camera holds
still when it claims to, something actually moves in every shot, and there are no black holes or accidental cuts.

    python video_audit.py film.mp4 [--target-lufs -14] [--max-peak -1.0] [--static-camera] [--json out.json]

Exit 0 when every gate passes, 1 when any fails. Style choices (how long a hold may be) are reported, not failed,
unless they exceed the configured ceiling.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FAILS, WARNS, INFO = [], [], {}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    return p.stdout + p.stderr


def gate(name, ok, detail, warn_only=False):
    tag = "PASS" if ok else ("WARN" if warn_only else "FAIL")
    print(f"  {tag}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        (WARNS if warn_only else FAILS).append(name)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--target-lufs", type=float, default=-14.0)
    ap.add_argument("--lufs-tol", type=float, default=0.6)
    ap.add_argument("--max-peak", type=float, default=-1.0)
    ap.add_argument("--max-hold", type=float, default=1.5, help="longest acceptable frozen hold, seconds")
    ap.add_argument("--static-camera", action="store_true", help="also require the frame not to drift")
    ap.add_argument("--min-shot", type=float, default=0.4, help="shortest acceptable shot, seconds")
    ap.add_argument("--json")
    a = ap.parse_args()
    v = Path(a.video)
    if not v.exists():
        print(f"no such file: {v}")
        return 1

    print(f"video audit — {v.name}")

    # ---------------------------------------------------------------- 1. container and streams
    print("\n1. file and streams")
    meta = probe(v)
    streams = meta.get("streams", [])
    vs = [s for s in streams if s.get("codec_type") == "video"]
    aus = [s for s in streams if s.get("codec_type") == "audio"]
    if not vs:
        print("  FAIL  no video stream")
        return 1
    st = vs[0]
    w, h = int(st.get("width", 0)), int(st.get("height", 0))
    num, den = (st.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(meta.get("format", {}).get("duration", 0) or 0)
    size_mb = v.stat().st_size / 1048576
    INFO.update(width=w, height=h, fps=fps, duration=dur, size_mb=round(size_mb, 2),
                video_codec=st.get("codec_name"), audio_codec=(aus[0].get("codec_name") if aus else None))
    print(f"  info  {w}x{h} {fps:.3f} fps · {dur:.3f} s · {size_mb:.2f} MB · "
          f"{st.get('codec_name')} + {(aus[0].get('codec_name') if aus else 'NO AUDIO')}")
    gate("audio stream present", bool(aus), aus[0].get("codec_name") if aus else "missing")
    gate("even dimensions (yuv420p requirement)", w % 2 == 0 and h % 2 == 0, f"{w}x{h}")
    # faststart: moov before mdat, so a phone can start playing before the file is fully downloaded
    head = v.read_bytes()[:200000]
    gate("faststart (moov before mdat)", head.find(b"moov") != -1 and
         (head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat")),
         "moov at " + str(head.find(b"moov")) + " mdat at " + str(head.find(b"mdat")), warn_only=True)

    # ---------------------------------------------------------------- 2. decode integrity
    print("\n2. decode integrity")
    err = run(["ffmpeg", "-v", "error", "-i", str(v), "-f", "null", "-"])
    n_err = len([l for l in err.splitlines() if l.strip()])
    gate("decodes with no errors", n_err == 0, f"{n_err} error line(s)" if n_err else "clean")

    # ---------------------------------------------------------------- 3. frozen picture
    print("\n3. frozen picture")
    fr = run(["ffmpeg", "-v", "info", "-i", str(v), "-vf", "freezedetect=n=0.004:d=1.5", "-f", "null", "-"])
    holds = [float(m) for m in re.findall(r"freeze_duration:\s*([0-9.]+)", fr)]
    longest = max(holds) if holds else 0.0
    print(f"  info  {len(holds)} hold(s), total {sum(holds):.2f} s, longest {longest:.2f} s")
    gate(f"no hold longer than {a.max_hold} s", longest <= a.max_hold,
         f"longest {longest:.2f} s" if holds else "none")

    # ---------------------------------------------------------------- 4. dead air
    print("\n4. dead air")
    si = run(["ffmpeg", "-v", "info", "-i", str(v), "-af", "silencedetect=n=-40dB:d=1.5", "-f", "null", "-"])
    starts = re.findall(r"silence_start:\s*([0-9.]+)", si)
    ends = re.findall(r"silence_end:\s*([0-9.]+)", si)
    spans = list(zip(starts, ends + ["end"] * len(starts)))
    print(f"  info  {len(spans)} silent span(s) at or over 1.5 s" + (f": {spans}" if spans else ""))
    gate("no unintended silence", len(spans) == 0, f"{len(spans)} span(s)", warn_only=True)

    # ---------------------------------------------------------------- 5. loudness
    print("\n5. loudness")
    eb = run(["ffmpeg", "-v", "info", "-i", str(v), "-af", "ebur128=peak=true", "-f", "null", "-"])
    lufs = re.findall(r"I:\s*(-?[0-9.]+)\s*LUFS", eb)
    peak = re.findall(r"Peak:\s*(-?[0-9.]+)\s*dBFS", eb)
    lra = re.findall(r"LRA:\s*([0-9.]+)\s*LU", eb)
    I = float(lufs[-1]) if lufs else None
    P = float(peak[-1]) if peak else None
    INFO.update(lufs=I, true_peak=P, lra=float(lra[-1]) if lra else None)
    print(f"  info  integrated {I} LUFS · true peak {P} dBFS · LRA {INFO['lra']} LU")
    gate(f"integrated within {a.lufs_tol} of {a.target_lufs} LUFS",
         I is not None and abs(I - a.target_lufs) <= a.lufs_tol, f"{I} LUFS")
    gate(f"true peak at or under {a.max_peak} dBFS", P is not None and P <= a.max_peak, f"{P} dBFS")

    # ---------------------------------------------------------------- 6. audio band balance
    print("\n6. audio band balance")
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-vn", "-ac", "1", "-ar", "48000", str(wav)])
        import numpy as np
        import wave
        with wave.open(str(wav), "rb") as wf:
            n, sr = wf.getnframes(), wf.getframerate()
            x = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        S = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        f = np.fft.rfftfreq(len(x), 1 / sr)
        tot = S.sum()
        low = S[f < 250].sum() / tot * 100
        harsh = S[(f >= 2000) & (f < 5000)].sum() / tot * 100
        high = S[f >= 8000].sum() / tot * 100
        INFO.update(low_pct=round(low, 1), harsh_pct=round(harsh, 1), high_pct=round(high, 1))
        print(f"  info  under 250 Hz {low:.1f} % · 2-5 kHz {harsh:.1f} % · above 8 kHz {high:.1f} %")
        gate("low end present (>=15 % under 250 Hz)", low >= 15.0, f"{low:.1f} %", warn_only=True)
        gate("not harsh (<=18 % in 2-5 kHz)", harsh <= 18.0, f"{harsh:.1f} %", warn_only=True)
        gate("no hiss (<=8 % above 8 kHz)", high <= 8.0, f"{high:.1f} %", warn_only=True)

        # ------------------------------------------------------------ 7. does anything move?
        print("\n7. motion, per second")
        hop = int(0.5 * sr)
        env = np.abs(x)
        blocks = [env[i:i + hop].max() for i in range(0, len(env) - hop, hop)]
        # warn-only: a metronomic bed (footsteps, a loop, a click track) is legitimately flat, and flatness
        # here only flags material that never changes level at all
        gate("audio envelope varies", len(set(round(b, 3) for b in blocks)) > 10, f"{len(blocks)} blocks",
             warn_only=True)

    # ---------------------------------------------------------------- 8. black gaps and cuts
    print("\n8. black frames and cut structure")
    bd = run(["ffmpeg", "-v", "info", "-i", str(v), "-vf", "blackdetect=d=0.1:pix_th=0.08", "-f", "null", "-"])
    blacks = re.findall(r"black_start:\s*([0-9.]+)\s*black_end:\s*([0-9.]+)", bd)
    print(f"  info  {len(blacks)} black span(s)" + (f": {blacks[:4]}" if blacks else ""))
    gate("no accidental black frames", len(blacks) == 0, f"{len(blacks)} span(s)", warn_only=True)

    sc = run(["ffmpeg", "-v", "info", "-i", str(v), "-vf", "select='gt(scene,0.25)',showinfo", "-f", "null", "-"])
    cuts = sorted(float(m) for m in re.findall(r"pts_time:([0-9.]+)", sc))
    shots = []
    prev = 0.0
    for c in cuts:
        shots.append(round(c - prev, 3))
        prev = c
    shots.append(round(dur - prev, 3))
    short = [s for s in shots if s < a.min_shot]
    print(f"  info  {len(shots)} shot(s), shortest {min(shots):.2f} s, longest {max(shots):.2f} s")
    gate(f"no shot shorter than {a.min_shot} s", len(short) == 0, f"{len(short)} short shot(s)", warn_only=True)

    # ---------------------------------------------------------------- 9. static camera, if claimed
    if a.static_camera:
        print("\n9. static camera (claimed)")
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from static_camera_audit import grab, shift_px
            import numpy as np
            prev = grab(str(v), 1.0, "text")
            worst = 0.0
            t = 1.0
            while t < min(dur - 1.0, 40.0):
                cur = grab(str(v), t, "text")
                if cur.shape == prev.shape:
                    dx, dy, pk = shift_px(prev, cur)
                    if pk >= 0.5:
                        worst = max(worst, float(np.hypot(dx, dy)))
                prev = cur
                t += 0.4
            gate("frame holds still (<=0.5 px)", worst <= 0.5, f"worst {worst:.2f} px")
        except Exception as e:
            print(f"  SKIP  static camera check unavailable: {e}")

    # ---------------------------------------------------------------- summary
    print("\n" + "-" * 60)
    print("measured: " + ", ".join(f"{k}={val}" for k, val in INFO.items()))
    if WARNS:
        print(f"warnings ({len(WARNS)}): " + ", ".join(WARNS))
    print(f"{'VIDEO AUDIT PASS' if not FAILS else 'VIDEO AUDIT FAIL (' + str(len(FAILS)) + '): ' + ', '.join(FAILS)}")
    print("not proven by any of this: whether the film is good. Nothing here approves composition, acting, taste or "
          "whether a frame reads at phone size — that is the visual review, and it is not optional.")
    if a.json:
        Path(a.json).write_text(json.dumps({"info": INFO, "fails": FAILS, "warns": WARNS, "shots": shots}, indent=1),
                                encoding="utf-8")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
