"""Upload a Short to YouTube with the Data API (OAuth refresh token; needs YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN).
Note: videos uploaded by a Google Cloud project that has not passed YouTube's API audit are locked to private."""
import os
import requests


def configured():
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _access_token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"})
    if not r.ok:
        raise RuntimeError(f"YouTube sign-in failed ({r.status_code}): {r.text[:200]}")
    return r.json()["access_token"]


def upload_short(path, title, description, privacy="private"):
    token = _access_token()
    meta = {"snippet": {"title": title[:100], "description": description[:4900], "categoryId": "27"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    size = os.path.getsize(path)
    start = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                                   "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                          json=meta, timeout=60)
    if not start.ok:
        raise RuntimeError(f"YouTube refused the upload ({start.status_code}): {start.text[:250]}")
    with open(path, "rb") as f:
        up = requests.put(start.headers["Location"], data=f, headers={"Content-Type": "video/mp4"}, timeout=900)
    if not up.ok:
        raise RuntimeError(f"YouTube upload failed ({up.status_code}): {up.text[:250]}")
    return f"https://youtube.com/shorts/{up.json()['id']}"
