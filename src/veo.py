"""One short talking clip of the host from Gemini Omni Flash, via the Interactions API (needs GEMINI_API_KEY).
(Veo 3.1 Preview was shut down on 2026-10-22; the file name is kept so the rest of the engine is unchanged.)"""
import base64, mimetypes, time


def _prompt(cfg, action, line):
    # <IMAGE_REF_0> is the host reference image, so the same face is used in every clip.
    return (f"A single continuous shot, no scene cuts. {cfg['series']['host_prompt']} The host Nammi is the person in "
            f"<IMAGE_REF_0>; use that image only as a reference for her look, not as a literal first frame. "
            f"{action} She speaks to the camera in warm, upbeat Indian English and says exactly: \"{line}\" "
            "Natural lip sync. No background music. No on-screen text, captions, subtitles, logos or watermarks.")


def _temporary(e):
    """Status code (or error name) and whether it is worth retrying. The Interactions API raises its own APIError
    classes (status_code attribute), different from the older models API (code attribute), so handle both."""
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    if code is None:   # dropped connection or timeout: no status code
        return type(e).__name__, True
    return code, code in (429, 500, 502, 503, 504)


def gen_clip(cfg, action, line, out_path):
    import httpx
    from google import genai
    from google.genai import errors
    from google.genai._gaos.lib import compat_errors
    s = cfg["series"]
    client = genai.Client()
    ref = s["reference_image"]
    mime = mimetypes.guess_type(ref)[0] or "image/png"
    image = {"type": "image", "mime_type": mime, "data": base64.b64encode(open(ref, "rb").read()).decode()}
    kwargs = dict(
        model=s.get("video_model", "gemini-omni-1.1-flash"),
        input=[image, {"type": "text", "text": _prompt(cfg, action, line)}],
        response_format={"type": "video", "aspect_ratio": "9:16", "resolution": "720p"})
    last = None
    for i in range(3):   # retry temporary errors (429, 5xx, dropped connection, timeout)
        try:
            it = client.interactions.create(**kwargs)
            break
        except (errors.APIError, compat_errors.APIError, httpx.TransportError) as e:
            last = e
            code, retry = _temporary(e)
            if not retry or i == 2:
                raise
            print(f"Video model: {code}, retrying in {30 * (i + 1)}s ({i + 1}/2)")
            time.sleep(30 * (i + 1))
    if it.output_video is None or not it.output_video.data:
        raise RuntimeError(f"No video returned (status {getattr(it, 'status', '?')}). Last error: {last}")
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(it.output_video.data))
    return out_path
