"""Public hosting so Instagram can fetch the video.
Default: a free public GitHub repo served by GitHub Pages (set MEDIA_REPO, MEDIA_TOKEN, PUBLIC_BASE).
Optional: any S3-compatible bucket such as Cloudflare R2 (set R2_ENDPOINT, R2_BUCKET, R2_KEY, R2_SECRET, PUBLIC_BASE)."""
import base64, mimetypes, os
from datetime import date, timedelta


def _gh_headers():
    return {"Authorization": f"Bearer {os.environ['MEDIA_TOKEN']}", "Accept": "application/vnd.github+json"}


def _github(path, key):
    import requests
    url = f"https://api.github.com/repos/{os.environ['MEDIA_REPO']}/contents/{key}"
    h = _gh_headers()
    body = {"message": f"add {key}", "branch": "main",
            "content": base64.b64encode(open(path, "rb").read()).decode()}
    old = requests.get(url, headers=h, timeout=60)
    if old.ok:
        body["sha"] = old.json()["sha"]
    requests.put(url, headers=h, json=body, timeout=300).raise_for_status()
    return os.environ["PUBLIC_BASE"].rstrip("/") + "/" + key


def upload(path, key):
    if os.environ.get("MEDIA_REPO"):
        return _github(path, key)
    import boto3
    s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"],
                      aws_access_key_id=os.environ["R2_KEY"],
                      aws_secret_access_key=os.environ["R2_SECRET"], region_name="auto")
    ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
    s3.upload_file(path, os.environ["R2_BUCKET"], key, ExtraArgs={"ContentType": ct})
    return os.environ["PUBLIC_BASE"].rstrip("/") + "/" + key


def cleanup(keep_days=21):
    """Delete dated folders (YYYY-MM-DD) older than keep_days from the media repo."""
    import requests
    if not os.environ.get("MEDIA_REPO"):
        print("No MEDIA_REPO set; nothing to clean.")
        return
    h = _gh_headers()
    cutoff = date.today() - timedelta(days=keep_days)
    root = requests.get(f"https://api.github.com/repos/{os.environ['MEDIA_REPO']}/contents", headers=h, timeout=60).json()
    for item in root:
        if item.get("type") != "dir":
            continue
        try:
            if date.fromisoformat(item["name"]) >= cutoff:
                continue
        except ValueError:
            continue
        for f in requests.get(item["url"], headers=h, timeout=60).json():
            requests.delete(f["url"], headers=h, json={"message": f"cleanup {item['name']}", "sha": f["sha"], "branch": "main"}, timeout=60)
        print("Deleted", item["name"])
