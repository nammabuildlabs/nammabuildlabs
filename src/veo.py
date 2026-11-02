"""One 8-second talking clip of the host from Veo, via the Gemini API (needs GEMINI_API_KEY)."""
import os, time


def _prompt(cfg, action, line):
    return (f"{cfg['series']['host_prompt']} {action} She says in warm, upbeat Indian English: \"{line}\" "
            "Natural lip sync. No on-screen text, captions, logos or watermarks.")


def gen_clip(cfg, action, line, out_path):
    from google import genai
    from google.genai import types
    s = cfg["series"]
    client = genai.Client()
    ref = types.Image.from_file(location=s["reference_image"])
    base = dict(aspect_ratio="9:16", resolution="720p", duration_seconds=8,
                negative_prompt="text, captions, subtitles, logos, watermark")
    try:   # preferred: reference image keeps her face consistent across clips
        op = client.models.generate_videos(
            model=s["veo_model"], prompt=_prompt(cfg, action, line),
            config=types.GenerateVideosConfig(
                reference_images=[types.VideoGenerationReferenceImage(image=ref, reference_type="asset")], **base))
    except Exception as e:  # fallback: use her image as the first frame
        print("reference mode failed, using image-to-video:", str(e)[:200])
        op = client.models.generate_videos(
            model=s["veo_model"], prompt=_prompt(cfg, action, line), image=ref,
            config=types.GenerateVideosConfig(**base))
    t0 = time.time()
    while not op.done:
        if time.time() - t0 > 900:
            raise TimeoutError("Veo took longer than 15 minutes")
        time.sleep(10)
        op = client.operations.get(op)
    vid = op.response.generated_videos[0]
    client.files.download(file=vid.video)
    vid.video.save(out_path)
    return out_path
