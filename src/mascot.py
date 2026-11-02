"""Illustrated mascot host. Same face every video, mouth driven by the narration audio."""
import asyncio, math, os, subprocess
from array import array
from PIL import Image, ImageChops, ImageColor, ImageDraw
from .reel import _tts, _dur
from .render import font, wrap, BOLD, REG

S = 2  # supersampling for smooth edges
SKIN, SKIN_D, HAIR = "#c98f63", "#b27a52", "#1c1a2b"
MOUTH_DARK, LIP, TONGUE = "#5a1f24", "#b0524f", "#d6706f"


def _dark(hex_color, k):
    r, g, b = ImageColor.getrgb(hex_color)
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def sprite(cfg, mouth, blink):
    """Return a 640x640 RGBA circular portrait. mouth 0-3 (closed..wide), blink 0/1."""
    col = cfg["brand"]["colors"]
    hoodie = _dark(col["accent"], 0.62)
    W = 640 * S
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def E(cx, cy, rx, ry, fill=None, outline=None, width=0):
        d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S],
                  fill=fill, outline=outline, width=width * S)

    def R(x0, y0, x1, y1, r, fill):
        d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill)

    def L(x0, y0, x1, y1, fill, w):
        d.line([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill, width=w * S)

    def A(box, a0, a1, fill, w):
        d.arc([box[0] * S, box[1] * S, box[2] * S, box[3] * S], a0, a1, fill=fill, width=w * S)

    E(320, 320, 316, 316, "#183029")                      # backdrop
    E(320, 260, 150, 185, HAIR)                           # back hair
    R(165, 250, 475, 560, 90, HAIR)
    R(80, 455, 560, 760, 130, hoodie)                     # hoodie
    R(285, 360, 355, 470, 20, SKIN_D)                     # neck
    E(320, 452, 52, 30, SKIN_D)
    L(296, 490, 294, 560, "#e8f1ed", 5); L(344, 490, 346, 560, "#e8f1ed", 5)
    E(320, 255, 112, 138, SKIN)                           # face
    E(208, 268, 14, 22, SKIN); E(432, 268, 14, 22, SKIN)  # ears
    E(208, 294, 7, 7, "#e3b341"); E(432, 294, 7, 7, "#e3b341")
    d.pieslice([208 * S, 112 * S, 432 * S, 398 * S], 180, 360, fill=HAIR)   # hair cap
    E(320, 236, 80, 62, SKIN)                             # forehead
    E(200, 385, 27, 150, HAIR); E(440, 385, 27, 150, HAIR)  # front locks
    for ex in (270, 370):                                 # eyes, glasses, brows
        if blink:
            L(ex - 22, 264, ex + 22, 264, "#2a1a12", 5)
        else:
            E(ex, 262, 25, 18, "white"); E(ex, 262, 12, 12, "#3b2417"); E(ex + 4, 258, 4, 4, "white")
            A((ex - 26, 244, ex + 26, 280), 200, 340, "#2a1a12", 4)
        E(ex, 262, 38, 34, None, "#0f2b27", 5)
        A((ex - 28, 214, ex + 28, 240), 200, 340, HAIR, 6)
    L(308, 258, 332, 258, "#0f2b27", 5)
    L(232, 256, 214, 252, "#0f2b27", 4); L(408, 256, 426, 252, "#0f2b27", 4)
    E(236, 322, 18, 10, "#d9876a"); E(404, 322, 18, 10, "#d9876a")   # blush
    A((306, 294, 334, 318), 20, 160, SKIN_D, 4)           # nose
    if mouth == 0:
        A((296, 338, 344, 368), 15, 165, LIP, 6)
    elif mouth == 1:
        E(320, 354, 14, 8, MOUTH_DARK, LIP, 3)
    elif mouth == 2:
        E(320, 356, 20, 14, MOUTH_DARK, LIP, 4); E(320, 364, 11, 5, TONGUE)
    else:
        E(320, 358, 24, 20, MOUTH_DARK, LIP, 4)
        R(304, 340, 336, 349, 3, "white"); E(320, 370, 14, 7, TONGUE)
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).ellipse([4 * S, 4 * S, 636 * S, 636 * S], fill=255)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), mask))
    ImageDraw.Draw(im).ellipse([4 * S, 4 * S, 636 * S, 636 * S], outline=col["accent"], width=8 * S)
    return im.resize((640, 640), Image.LANCZOS)


def scene_bg(cfg, title, caption, kind):
    """1080x1920 frame, text kept inside Instagram's reel safe zone."""
    c, col = cfg["brand"], cfg["brand"]["colors"]
    img = Image.new("RGB", (1080, 1920), col["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1080, 14], fill=col["accent"])
    d.text((90, 250), c["name"].upper(), font=font(BOLD, 32), fill=col["accent"])
    tf, bf = font(BOLD, 64), font(REG, 36)
    y = 1000
    for ln in wrap(d, title, tf, 760):
        d.text((90, y), ln, font=tf, fill=col["fg"]); y += 78
    y += 24
    if kind == "cta":
        label = c["cta"]
        bw = d.textlength(label, font=font(BOLD, 40)) + 80
        d.rounded_rectangle([90, y, 90 + bw, y + 96], radius=48, fill=col["accent"])
        d.text((130, y + 24), label, font=font(BOLD, 40), fill=col["bg"])
    else:
        for ln in wrap(d, caption, bf, 760)[:4]:
            d.text((90, y), ln, font=bf, fill=col["muted"]); y += 48
    d.text((90, 1395), c["handle"], font=font(REG, 32), fill=col["muted"])
    return img


def _levels(audio, fps):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"])
    s = array("h"); s.frombytes(raw)
    win = 16000 // fps
    rms = []
    for k in range(0, len(s), win):
        chunk = s[k:k + win]
        rms.append((sum(x * x for x in chunk) / max(1, len(chunk))) ** 0.5)
    ref = sorted(rms)[max(0, int(len(rms) * 0.95) - 1)] or 1.0
    out, prev = [], 0.0
    for r in rms:  # light smoothing so the mouth doesn't flutter
        prev = 0.6 * min(1.0, r / ref) + 0.4 * prev
        out.append(prev)
    return out


def _mouth(v):
    return 0 if v < 0.10 else 1 if v < 0.35 else 2 if v < 0.70 else 3


def build_reel(cfg, reel, outdir, fps=24):
    os.makedirs(outdir, exist_ok=True)
    sprites = {(m, b): sprite(cfg, m, b) for m in range(4) for b in (0, 1)}
    scenes, lines = reel["scenes"], []
    X, Y = 150, 300  # circle centred at x=470 inside the safe zone
    for i, sc in enumerate(scenes):
        a, v = os.path.join(outdir, f"s{i}.mp3"), os.path.join(outdir, f"s{i}.mp4")
        asyncio.run(_tts(sc["narration"], cfg["voice"], a))
        kind = "cta" if i == len(scenes) - 1 else "body"
        bg = scene_bg(cfg, sc["onscreen"], sc["narration"], kind)
        lv = _levels(a, fps)
        n = int((_dur(a) + 0.4) * fps) + 1
        p = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                              "-r", str(fps), "-i", "-", "-i", a, "-af", "apad", "-c:v", "libx264",
                              "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
                              "-ac", "2", "-shortest", v], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        for f in range(n):
            t = f / fps + i * 1.3
            amp = lv[f] if f < len(lv) else 0.0
            blink = 1 if (t % 3.6) < 0.14 and t > 0.5 else 0
            dy = round(5 * math.sin(2 * math.pi * t / 2.4) + 6 * amp)
            frame = bg.copy()
            sp = sprites[(_mouth(amp), blink)]
            frame.paste(sp, (X, Y + dy), sp)
            p.stdin.write(frame.tobytes())
        p.stdin.close(); p.wait()
        lines.append(f"file 's{i}.mp4'")
    with open(os.path.join(outdir, "list.txt"), "w") as fh:
        fh.write("\n".join(lines))
    out = os.path.join(outdir, "reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(outdir, "list.txt"),
                    "-c", "copy", out], check=True, capture_output=True)
    cover = os.path.join(outdir, "cover.jpg")
    c0 = scene_bg(cfg, scenes[0]["onscreen"], scenes[0]["narration"], "body")
    c0.paste(sprites[(1, 0)], (X, Y), sprites[(1, 0)])
    c0.save(cover, quality=92)
    return out, cover
