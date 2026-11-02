import asyncio, os, subprocess
from .render import slide


def _dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path])
    return float(out)


async def _tts(text, voice, path):
    import edge_tts
    await edge_tts.Communicate(text, voice).save(path)


def build_reel(cfg, reel, outdir):
    os.makedirs(outdir, exist_ok=True)
    scenes = reel["scenes"]
    lines = []
    for i, s in enumerate(scenes):
        a, f, v = (os.path.join(outdir, x) for x in (f"s{i}.mp3", f"s{i}.png", f"s{i}.mp4"))
        asyncio.run(_tts(s["narration"], cfg["voice"], a))
        kind = "cover" if i == 0 else ("cta" if i == len(scenes) - 1 else "body")
        slide(cfg, s["onscreen"], s["narration"], i + 1, len(scenes), size=(1080, 1920), counter=False, kind=kind).save(f)
        d = _dur(a) + 0.4
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", f, "-i", a,
                        "-t", f"{d:.2f}", "-af", "apad", "-c:v", "libx264", "-tune", "stillimage",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", v],
                       check=True, capture_output=True)
        lines.append(f"file 's{i}.mp4'")
    with open(os.path.join(outdir, "list.txt"), "w") as fh:
        fh.write("\n".join(lines))
    out = os.path.join(outdir, "reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(outdir, "list.txt"),
                    "-c", "copy", out], check=True, capture_output=True)
    from PIL import Image
    cover = os.path.join(outdir, "cover.jpg")
    Image.open(os.path.join(outdir, "s0.png")).convert("RGB").save(cover, quality=92)
    return out, cover
