import os, requests


def notify(text):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print(text)
        return
    requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                  data={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": "true"}, timeout=30)


def notify_video(path, caption):
    """Send the finished video to Telegram so you can preview it without any public link."""
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("[video preview]", path, caption)
        return
    with open(path, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{tok}/sendVideo",
                      data={"chat_id": chat, "caption": caption[:1000], "supports_streaming": "true"},
                      files={"video": f}, timeout=300)
