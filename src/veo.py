"""One short talking clip of the host from Gemini Omni Flash, via the Interactions API (needs GEMINI_API_KEY).
(Veo 3.1 Preview was shut down on 2026-10-22; the file name is kept so the rest of the engine is unchanged.)"""
import base64, mimetypes, time
from .deadline import call_with_deadline


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
    if code is None:   # dropped connection: no status code
        return type(e).__name__, True
    return code, code in (429, 500, 502, 503, 504)


def _log(label, msg):
    print(f"[{time.strftime('%H:%M:%S')}] {label}: {msg}", flush=True)


def _create(client, kwargs, label, limit):
    """Start the video in the background (returns an id at once, so a stuck request can be polled, logged and
    cancelled instead of hanging). If the API refuses background mode for this model, fall back to one blocking call."""
    try:
        it = client.interactions.create(background=True, **kwargs)
        _log(label, f"started in background, id={it.id}, status={it.status}")
    except Exception as e:   # noqa: BLE001 - only a clear 400 about background switches to the blocking call
        if getattr(e, "status_code", None) != 400:
            raise
        _log(label, f"background mode refused ({str(e)[:200]}); using one blocking call instead")
        return call_with_deadline(lambda: client.interactions.create(**kwargs), limit, "video request")
    t0, last = time.time(), None
    while it.status in ("queued", "in_progress"):
        if time.time() - t0 > limit:
            try:
                client.interactions.cancel(it.id)
                _log(label, "cancelled the request on Google's side")
            except Exception as e:   # noqa: BLE001
                _log(label, f"could not cancel ({type(e).__name__}); check usage in AI Studio")
            raise RuntimeError(f"The video was still '{it.status}' after {max(1, limit // 60)} min, so it was cancelled.")
        time.sleep(10)
        try:
            it = client.interactions.get(id=it.id)
        except Exception as e:   # noqa: BLE001 - a failed poll is not a failed video; try again
            _log(label, f"status check failed ({type(e).__name__}), will retry")
            continue
        if it.status != last or int(time.time() - t0) % 60 < 10:
            _log(label, f"status {it.status} after {int(time.time() - t0)}s")
        last = it.status
    return it


def gen_clip(cfg, action, line, out_path, label="clip"):
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
    limit = s.get("video_timeout_s", 12 * 60)   # hard stop per request
    it = None
    for i in range(2):   # retry only quick temporary errors (429, 5xx, dropped connection)
        t0 = time.time()
        _log(label, f"asking Gemini for the video (attempt {i + 1}/2, waits up to {max(1, limit // 60)} min)...")
        try:
            it = _create(client, kwargs, label, limit)
            _log(label, f"finished with status {it.status} after {int(time.time() - t0)}s")
            break
        except TimeoutError as e:
            # Not retried: Google may still finish this request and bill it, and a retry would pay twice.
            raise RuntimeError(f"{e} Not retrying, because Google may still finish and bill it. "
                               "Check usage in AI Studio before running again.") from e
        except httpx.TimeoutException as e:
            raise RuntimeError(f"The video connection timed out ({type(e).__name__}). Not retrying, to avoid being billed "
                               "twice. Check usage in AI Studio before running again.") from e
        except (errors.APIError, compat_errors.APIError, httpx.TransportError) as e:
            code, retry = _temporary(e)
            _log(label, f"Gemini returned {code} after {int(time.time() - t0)}s")
            if not retry or i == 1:
                raise
            time.sleep(30)
    if it is None or it.status != "completed":
        raise RuntimeError(f"Video not completed: status {getattr(it, 'status', '?')}, errors {getattr(it, 'errors', None)}")
    if it.output_video is None or not it.output_video.data:
        raise RuntimeError(f"No video data returned (status {it.status}).")
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(it.output_video.data))
    _log(label, f"saved {out_path}")
    return out_path
