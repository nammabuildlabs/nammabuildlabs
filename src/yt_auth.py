"""Run once on your own computer to get a YouTube refresh token:
   YT_CLIENT_ID=... YT_CLIENT_SECRET=... python run.py yt-auth"""
import http.server, os, urllib.parse
import requests

PORT = 8765


def main():
    cid, secret = os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"]
    redirect = f"http://127.0.0.1:{PORT}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "access_type": "offline",
        "prompt": "consent", "scope": "https://www.googleapis.com/auth/youtube.upload"})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            got["code"] = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and return to the terminal.")

        def log_message(self, *a):
            pass

    print("Open this address in your browser and allow access:\n\n" + url + "\n")
    http.server.HTTPServer(("127.0.0.1", PORT), H).handle_request()
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "code": got.get("code", ""), "client_id": cid, "client_secret": secret,
        "redirect_uri": redirect, "grant_type": "authorization_code"})
    if not r.ok or "refresh_token" not in r.json():
        raise SystemExit(f"Could not get a refresh token: {r.text[:300]}")
    print("\nYour refresh token (keep it private, add it as the secret YT_REFRESH_TOKEN):\n\n" + r.json()["refresh_token"])
