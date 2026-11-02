import os, time, requests

# Default: Instagram API with Instagram Login (no Facebook Page needed). For the Facebook Login route set
# IG_GRAPH_BASE=https://graph.facebook.com/v26.0
GRAPH = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com/v26.0")


def _call(method, path, **p):
    p["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{GRAPH}/{path}",
                         params=p if method == "GET" else None,
                         data=p if method == "POST" else None, timeout=60)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text}")
    return r.json()


def _wait(cid, tries=40):
    for _ in range(tries):
        s = _call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} status {s}")
        time.sleep(15)
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
    p = dict(media_type="REELS", video_url=video_url, caption=caption, share_to_feed="true")
    if cover_url:
        p["cover_url"] = cover_url
    cid = _call("POST", f"{os.environ['IG_USER_ID']}/media", **p)["id"]
    return _publish(cid)
