import os, time, requests

# Default: Instagram API with Instagram Login (no Facebook Page needed). For the Facebook Login route set
# IG_GRAPH_BASE=https://graph.facebook.com/v26.0
GRAPH = os.environ.get("IG_GRAPH_BASE") or "https://graph.instagram.com/v26.0"


def _call(method, path, **p):
    p["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{GRAPH}/{path}",
                         params=p if method == "GET" else None,
                         data=p if method == "POST" else None, timeout=60)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text}")
    return r.json()


def _wait(cid, tries=20):
    for _ in range(tries):
        s = _call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} status {s}")
        time.sleep(30)   # Meta suggests polling about once a minute
    raise TimeoutError(cid)


def _publish(cid):
    _wait(cid)
    return _call("POST", f"{os.environ['IG_USER_ID']}/media_publish", creation_id=cid)["id"]


def publish_carousel(urls, caption):
    uid = os.environ["IG_USER_ID"]
    kids = [_call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"] for u in urls]
    for k in kids:
        _wait(k)
    cid = _call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    return _publish(cid)


def publish_reel(video_url, caption, cover_url=None):
    p = dict(media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true",
             is_ai_generated="true")   # Instagram's own AI self-disclosure flag
    if cover_url:
        p["cover_url"] = cover_url
    cid = _call("POST", f"{os.environ['IG_USER_ID']}/media", **p)["id"]
    return _publish(cid)


def publish_reel_file(path, caption):
    """Upload the video file straight to Meta (resumable upload). Needs the Facebook Login route."""
    import requests
    if "graph.facebook.com" not in GRAPH:
        raise RuntimeError("Direct upload needs the Facebook Login route: set the repository variable "
                           "IG_GRAPH_BASE to https://graph.facebook.com/v26.0 and use a Facebook Page access token.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Video not found at {path}. The 07:00 draft job must finish first.")
    version = GRAPH.rstrip("/").split("/")[-1]
    cid = _call("POST", f"{os.environ['IG_USER_ID']}/media", media_type="REELS", upload_type="resumable",
                caption=caption, share_to_feed="true", is_ai_generated="true", thumb_offset="1500")["id"]
    with open(path, "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/ig-api-upload/{version}/{cid}",
                          headers={"Authorization": f"OAuth {os.environ['IG_ACCESS_TOKEN']}",
                                   "offset": "0", "file_size": str(os.path.getsize(path))},
                          data=f, timeout=900)
    if not r.ok or not r.json().get("success", False):
        raise RuntimeError(f"Upload failed: {r.status_code} {r.text[:300]}")
    return _publish(cid)
