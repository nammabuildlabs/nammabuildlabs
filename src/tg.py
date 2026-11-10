"""Thin Telegram Bot API helpers (needs TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)."""
import json, os
import requests


def _base():
    return os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")


def chat_id():
    return str(os.environ["TELEGRAM_CHAT_ID"])


def api(method, files=None, http_timeout=60, **params):
    r = requests.post(f"{_base()}/bot{os.environ['TELEGRAM_TOKEN']}/{method}", data=params, files=files, timeout=http_timeout)
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"Telegram {method}: unexpected reply {r.status_code}")
    if not j.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {j.get('description', '')}")
    return j["result"]


def send(text, buttons=None):
    p = dict(chat_id=chat_id(), text=text[:4000], parse_mode="HTML", disable_web_page_preview="true")
    if buttons:
        p["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    return api("sendMessage", **p)


def send_photo(path, caption=""):
    with open(path, "rb") as f:
        return api("sendPhoto", files={"photo": f}, http_timeout=120, chat_id=chat_id(), caption=caption[:900], parse_mode="HTML")


def send_video(path, caption="", buttons=None, as_document=False):
    field, method = ("document", "sendDocument") if as_document else ("video", "sendVideo")
    p = dict(chat_id=chat_id(), caption=caption[:900], parse_mode="HTML")
    if not as_document:
        p["supports_streaming"] = "true"
    if buttons:
        p["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    with open(path, "rb") as f:
        return api(method, files={field: f}, http_timeout=300, **p)


def updates(offset, timeout=0):
    return api("getUpdates", http_timeout=timeout + 30, offset=offset, timeout=timeout,
               allowed_updates=json.dumps(["message", "callback_query"]))


def answer(callback_id, text=""):
    try:
        api("answerCallbackQuery", callback_query_id=callback_id, text=text[:150])
    except RuntimeError:
        pass


def clear_buttons(message_id):
    try:
        api("editMessageReplyMarkup", chat_id=chat_id(), message_id=message_id, reply_markup=json.dumps({"inline_keyboard": []}))
    except RuntimeError:
        pass


def download(file_id, dest):
    """Bots can download files up to 20 MB."""
    info = api("getFile", file_id=file_id)
    url = f"{_base()}/file/bot{os.environ['TELEGRAM_TOKEN']}/{info['file_path']}"
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    return dest
