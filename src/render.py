from PIL import Image, ImageDraw, ImageFont

BOLD = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]
REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"]


def font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def slide(cfg, title, body, idx, total, size=(1080, 1350), counter=True, kind="body"):
    """kind: cover (big hook), body (bar + text), cta (button)."""
    c, b = cfg["brand"]["colors"], cfg["brand"]
    W, H = size
    img = Image.new("RGB", size, c["bg"])
    d = ImageDraw.Draw(img)
    pad = 90
    reel = H >= 1900  # Instagram UI covers top 230px, bottom 480px and right 230px of a reel
    maxw = (W - 230 - pad) if reel else (W - 2 * pad)
    tsize = {"cover": 100, "body": 76, "cta": 84}[kind]
    tf, bf = font(BOLD, tsize), font(REG, 42)
    lh = int(tsize * 1.22)
    tl = wrap(d, title, tf, maxw)
    bl = wrap(d, body, bf, maxw) if body else []
    block = 40 + len(tl) * lh + (44 + len(bl) * 62 if bl else 0) + (150 if kind == "cta" else 0)
    y = max(200, (H - block) // 2 - 30)
    if reel:
        y = max(300, min((H - block) // 2 - 30, 1440 - block))
    top_y, foot_y = (250, 1370) if reel else (70, H - 110)
    d.rectangle([0, 0, W, 14], fill=c["accent"])
    d.text((pad, top_y), b["name"].upper(), font=font(BOLD, 32), fill=c["accent"])
    d.rectangle([pad, y, pad + 130, y + 12], fill=c["accent"])
    y += 52
    for line in tl:
        d.text((pad, y), line, font=tf, fill=c["fg"])
        y += lh
    y += 44
    for line in bl:
        d.text((pad, y), line, font=bf, fill=c["muted"])
        y += 62
    if kind == "cta":
        y += 40
        label = b["cta"]
        bw = d.textlength(label, font=font(BOLD, 44)) + 90
        d.rounded_rectangle([pad, y, pad + bw, y + 104], radius=52, fill=c["accent"])
        d.text((pad + 45, y + 26), label, font=font(BOLD, 44), fill=c["bg"])
    if kind == "cover" and not reel:
        d.text((W - pad - 210, H - 110), "SWIPE \u2192", font=font(BOLD, 34), fill=c["accent"])
    d.text((pad, foot_y), b["handle"], font=font(REG, 32), fill=c["muted"])
    if counter and total > 1 and kind != "cover":
        t = f"{idx}/{total}"
        d.text((W - pad - d.textlength(t, font=font(BOLD, 32)), H - 110), t, font=font(BOLD, 32), fill=c["accent"])
    return img
