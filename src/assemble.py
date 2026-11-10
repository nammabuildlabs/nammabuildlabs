"""Join the clips, then add brand bar, episode chip and a caption panel inside Instagram's reel safe zone."""
import os, subprocess
from PIL import Image, ImageDraw
from .render import font, wrap, BOLD, REG


def _dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "default=nw=1:nk=1", p]))


def _has_audio(p):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
                                   "-of", "default=nw=1:nk=1", p])
    return bool(out.strip())


def _base(cfg, ep):
    col = cfg["brand"]["colors"]
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, logo = 90, cfg["series"].get("logo", "assets/logo-mark.png")
    if os.path.exists(logo):
        lg = Image.open(logo).convert("RGBA").resize((56, 56))
        im.paste(lg, (90, 236), lg)
        x = 160
    d.text((x, 252), cfg["brand"]["name"].upper(), font=font(BOLD, 26), fill="white", stroke_width=2, stroke_fill=(0, 0, 0, 170))
    chip = f"EP {ep['part']}/{ep['parts']}  {ep['level'].upper()}"
    cf = font(BOLD, 22)
    w = int(d.textlength(chip, font=cf)) + 36
    cx = 850 - w
    d.rounded_rectangle([cx, 244, 850, 288], radius=22, fill=col["accent"])
    d.text((cx + 18, 254), chip, font=cf, fill=col["bg"])
    return im


def _caption(cfg, title, line):
    col = cfg["brand"]["colors"]
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tf, lf = font(BOLD, 30), font(REG, 36)
    lines = wrap(d, line, lf, 730)[:4]
    h = 36 + 40 + 10 + len(lines) * 46 + 26
    top = 1420 - h
    d.rounded_rectangle([60, top, 850, 1420], radius=28, fill=(7, 10, 26, 185))
    d.text((90, top + 30), title[:44], font=tf, fill=col["accent"])
    y = top + 30 + 40 + 10
    for ln in lines:
        d.text((90, y), ln, font=lf, fill="white")
        y += 46
    return im


def assemble(cfg, ep, script, clips, outdir):
    n = len(clips)
    for c in clips:
        if not _has_audio(c):
            raise RuntimeError(f"{os.path.basename(c)} has no sound. Make the clip with the spoken line included.")
    durs = [_dur(c) for c in clips]
    total = sum(durs)
    base = os.path.join(outdir, "ov_base.png")
    _base(cfg, ep).save(base)
    title = f"{ep['title']}" + (f"  \u00b7  Part {ep['part']}" if ep["parts"] > 1 else "")
    caps = []
    for i in range(n):
        p = os.path.join(outdir, f"ov_cap{i + 1}.png")
        _caption(cfg, title, script["clips"][min(i, len(script["clips"]) - 1)]["line"]).save(p)
        caps.append(p)
    scale = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,fps=24"
    fc = ";".join(f"[{i}:v]{scale}[v{i}]" for i in range(n))
    fc += ";" + "".join(f"[v{i}][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    fc += f";[v][{n}:v]overlay=0:0[o0]"
    start = 0.0
    for i in range(n):
        end = start + durs[i]
        cond = f"between(t,{start:.2f},{end:.2f})" if i < n - 1 else f"gte(t,{start:.2f})"
        fc += f";[o{i}][{n + 1 + i}:v]overlay=0:0:enable='{cond}'[o{i + 1}]"
        start = end
    out = os.path.join(outdir, "reel.mp4")
    loop = ["-loop", "1", "-framerate", "24", "-t", f"{total + 1:.2f}"]
    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", c]
    cmd += [*loop, "-i", base]
    for p in caps:
        cmd += [*loop, "-i", p]
    cmd += ["-filter_complex", fc, "-map", f"[o{n}]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out]
    subprocess.run(cmd, check=True, capture_output=True)
    cover = os.path.join(outdir, "cover.jpg")
    subprocess.run(["ffmpeg", "-y", "-ss", "1.5", "-i", out, "-frames:v", "1", "-q:v", "3", cover],
                   check=True, capture_output=True)
    return out, cover
