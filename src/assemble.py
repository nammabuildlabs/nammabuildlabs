"""Join the clips, then add brand bar, episode chip and a caption panel inside Instagram's reel safe zone."""
import os, subprocess
from PIL import Image, ImageDraw
from .render import font, wrap, BOLD, REG


def _dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "default=nw=1:nk=1", p]))


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
    d1, d2 = _dur(clips[0]), _dur(clips[1])
    total = d1 + d2
    base, c1, c2 = (os.path.join(outdir, n) for n in ("ov_base.png", "ov_cap1.png", "ov_cap2.png"))
    _base(cfg, ep).save(base)
    title = f"{ep['title']}" + (f"  ·  Part {ep['part']}" if ep["parts"] > 1 else "")
    _caption(cfg, title, script["clips"][0]["line"]).save(c1)
    _caption(cfg, title, script["clips"][1]["line"]).save(c2)
    fc = ("[0:v]scale=1080:1920:flags=lanczos,setsar=1,fps=24[v0];[1:v]scale=1080:1920:flags=lanczos,setsar=1,fps=24[v1];"
          "[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a];"
          "[v][2:v]overlay=0:0[o1];"
          f"[o1][3:v]overlay=0:0:enable='between(t,0,{d1:.2f})'[o2];"
          f"[o2][4:v]overlay=0:0:enable='gte(t,{d1:.2f})'[vo]")
    out = os.path.join(outdir, "reel.mp4")
    loop = ["-loop", "1", "-framerate", "24", "-t", f"{total + 1:.2f}"]
    subprocess.run(["ffmpeg", "-y", "-i", clips[0], "-i", clips[1], *loop, "-i", base, *loop, "-i", c1, *loop, "-i", c2,
                    "-filter_complex", fc, "-map", "[vo]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out],
                   check=True, capture_output=True)
    cover = os.path.join(outdir, "cover.jpg")
    subprocess.run(["ffmpeg", "-y", "-ss", "1.5", "-i", out, "-frames:v", "1", "-q:v", "3", cover],
                   check=True, capture_output=True)
    return out, cover
