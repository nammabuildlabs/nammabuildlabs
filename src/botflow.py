"""Telegram-driven daily flow.
 1. send_daily(): the bot sends today's script, a ready-to-paste Gemini prompt per clip, and the caption.
 2. You make the clips in the Gemini app and send them back to the bot.
 3. poll_once(): the bot joins the clips, adds captions, and sends a preview with buttons.
 4. On approval it uploads to Instagram and YouTube (whichever are set up), or hands you the file to post by hand."""
import html, json, os, tempfile
from datetime import date, datetime
from zoneinfo import ZoneInfo
from . import tg


def _esc(s):
    return html.escape(str(s), quote=False)


def _path():
    return os.environ.get("STATE_PATH", "tg_state.json")


def load():
    try:
        return json.load(open(_path()))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offset": 0, "status": "idle"}


def save(st):
    json.dump(st, open(_path(), "w"), indent=1, ensure_ascii=False)


def _today(cfg):
    return datetime.now(ZoneInfo(cfg["timezone"])).date()


def _episode(cfg, d):
    from .series import queue
    n = (d - date.fromisoformat(cfg["start_date"])).days
    if n < 0:
        raise SystemExit("Today is before start_date in config.yaml.")
    q = queue(cfg)
    return n + 1, q[n % len(q)]


def _caption(script):
    tags = " ".join("#" + t.lstrip("#") for t in script.get("hashtags", [])[:5])
    return f"{script['caption'].strip()}\n\n{tags}\n\nHosted by Nammi, our AI virtual host."


def _pre(text):
    return "<pre>" + _esc(text) + "</pre>"


def _send_script(cfg, st):
    from .prompts import app_prompt
    ep, script = st["episode"], st["script"]
    n = len(script["clips"])
    tg.send(f"<b>Good morning! Episode {st['day_no']}: {_esc(ep['title'])}</b>\n"
            f"Part {ep['part']} of {ep['parts']}, {ep['level']} level.\n\n"
            f"<b>Your job today ({n} clips, about 5 minutes):</b>\n"
            "1. Open the Gemini app, choose Create video.\n"
            "2. Paste the prompt for each clip below, exactly as it is. (If you attached a reference photo for your first video, attach the same one.)\n"
            "3. Download each clip and send it to me here, clip 1 first.\n"
            "I will join them, add captions and show you a preview.")
    if cfg.get("telegram_flow", {}).get("send_reference", True) and not st.get("ref_sent"):
        ref = cfg["series"]["reference_image"]
        if os.path.exists(ref):
            tg.send_photo(ref, "Nammi reference photo: use it in the Gemini app if you used a reference photo for her first video.")
            st["ref_sent"] = True
    for i, c in enumerate(script["clips"], 1):
        tg.send(f"<b>Clip {i} of {n}</b> (she says: <i>{_esc(c['line'])}</i>)\n" + _pre(app_prompt(cfg, c["action"], c["line"])))
    if script.get("claims_to_verify"):
        tg.send("<b>Please check before posting:</b>\n- " + "\n- ".join(_esc(x) for x in script["claims_to_verify"]))
    tg.send("<b>Caption (for Instagram and YouTube)</b>\n" + _pre(_caption(script)) +
            "\nSend each clip as a <b>file</b> if you can, for the best quality. Commands: /script /status /redo /done /new /help")
    save(st)


def send_daily(cfg, d=None, force=False):
    from .generate import episode_script
    d = d or _today(cfg)
    st = load()
    if st.get("day") == str(d) and st.get("status") not in (None, "idle") and not force:
        print("Already sent today. Use force to send again.")
        return
    day_no, ep = _episode(cfg, d)
    script = episode_script(cfg, ep)
    st.update(day=str(d), day_no=day_no, episode=ep, script=script, clips=[], seen=[], final=None, status="waiting_clips")
    save(st)
    _send_script(cfg, st)


def _buttons():
    return [[{"text": "Post to Instagram and YouTube", "callback_data": "approve"}],
            [{"text": "I will post by hand (send me the file)", "callback_data": "manual"}],
            [{"text": "Redo the clips", "callback_data": "redo"}, {"text": "Skip today", "callback_data": "skip"}]]


def _finalize(cfg, st):
    from .assemble import assemble
    work = tempfile.mkdtemp()
    paths = []
    for i, c in enumerate(sorted(st["clips"], key=lambda c: c["msg"]), 1):
        paths.append(tg.download(c["file_id"], os.path.join(work, f"clip{i}.mp4")))
    tg.send(f"Joining {len(paths)} clip(s) and adding captions. One moment...")
    video, _ = assemble(cfg, st["episode"], st["script"], paths, work)
    res = tg.send_video(video, caption="Preview. If it looks right, choose below.", buttons=_buttons())
    st["final"] = {"file_id": res["video"]["file_id"], "msg": res["message_id"]}
    st["status"] = "awaiting_approval"


def _title(st):
    ep = st["episode"]
    return f"{ep['title']}" + (f" (Part {ep['part']})" if ep["parts"] > 1 else "") + " | NammaBuildLabs #Shorts"


def post_everywhere(cfg, path, caption, st):
    lines, ok = [], 0
    if cfg.get("instagram_upload", True):
        if not (os.environ.get("IG_ACCESS_TOKEN") and os.environ.get("IG_USER_ID")):
            lines.append("Instagram: not set up yet, so skipped.")
        else:
            try:
                from .instagram import publish_reel_file
                mid = publish_reel_file(path, caption)
                lines.append(f"Instagram: posted (media id {mid}).")
                ok += 1
            except Exception as e:
                lines.append(f"Instagram: failed. {str(e)[:300]}")
    if cfg.get("youtube_upload", False):
        from . import youtube
        if not youtube.configured():
            lines.append("YouTube: not set up yet, so skipped.")
        else:
            try:
                privacy = cfg.get("youtube_privacy", "private")
                url = youtube.upload_short(path, _title(st), caption, privacy)
                lines.append(f"YouTube: uploaded as {privacy}: {url}")
                ok += 1
            except Exception as e:
                lines.append(f"YouTube: failed. {str(e)[:300]}")
    return lines, ok


def _deliver(cfg, st, manual):
    work = tempfile.mkdtemp()
    path = tg.download(st["final"]["file_id"], os.path.join(work, "reel.mp4"))
    caption = _caption(st["script"])
    if manual:
        tg.send_video(path, caption="Final video. Upload this file to Instagram and YouTube Shorts.", as_document=True)
        tg.send("<b>Caption to paste</b>\n" + _pre(caption))
        st["status"] = "posted_manually"
        return
    lines, ok = post_everywhere(cfg, path, caption, st)
    tg.send("\n".join(_esc(x) for x in lines) or "Nothing is set up for automatic posting yet.")
    if ok:
        st["status"] = "posted"
    else:
        tg.send("Nothing was posted automatically. You can try again or take the file and post by hand.", _buttons()[:2])
        st["status"] = "awaiting_approval"


HELP = ("/script  send today's script again (or make it if missing)\n/new  write a different script for today\n"
        "/status  where we are\n/done  join the clips I have sent so far\n/redo  forget my clips and start again\n"
        "/skip  skip today\nSend clips as video files, clip 1 first.")


def _clip_from(m):
    v = m.get("video") or m.get("animation")
    doc = m.get("document")
    if not v and doc and str(doc.get("mime_type", "")).startswith("video/"):
        v = doc
    return v


def _on_message(cfg, st, m):
    text = (m.get("text") or "").strip().lower()
    cmd = text.split()[0].split("@")[0] if text.startswith("/") else ""
    if cmd in ("/start", "/help"):
        tg.send(_esc(HELP))
    elif cmd == "/status":
        n = len(st.get("clips", []))
        need = len(st.get("script", {}).get("clips", [])) or 2
        tg.send(f"Status: {st.get('status')}. Episode: {st.get('episode', {}).get('title', 'none yet')}. Clips received: {n} of {need}.")
    elif cmd == "/script":
        if st.get("day") == str(_today(cfg)) and st.get("script"):
            _send_script(cfg, st)
        else:
            off = st.get("offset", 0)
            send_daily(cfg, force=True)
            st.clear()
            st.update(load())
            st["offset"] = off
    elif cmd == "/new":
        from .generate import episode_script
        script = episode_script(cfg, st["episode"]) if st.get("episode") else None
        if not script:
            tg.send("There is no episode yet. Send /script first.")
        else:
            st.update(script=script, clips=[], seen=[], final=None, status="waiting_clips")
            _send_script(cfg, st)
    elif cmd == "/redo":
        st.update(clips=[], seen=[], final=None, status="waiting_clips")
        tg.send("Okay, send clip 1 again.")
    elif cmd == "/skip":
        st["status"] = "skipped"
        tg.send("Skipped for today.")
    elif cmd == "/done":
        if st.get("clips"):
            _finalize(cfg, st)
        else:
            tg.send("I have no clips yet.")
    elif _clip_from(m):
        v = _clip_from(m)
        if st.get("status") != "waiting_clips":
            tg.send("I am not waiting for clips right now. Send /script to start, or /redo to start over.")
            return
        if v["file_unique_id"] in st.get("seen", []):
            return
        st.setdefault("seen", []).append(v["file_unique_id"])
        st.setdefault("clips", []).append({"file_id": v["file_id"], "msg": m["message_id"]})
        need = len(st["script"]["clips"])
        got = len(st["clips"])
        tg.send(f"Got clip {got} of {need}.")
        if got >= need:
            _finalize(cfg, st)
    elif text:
        tg.send("I did not understand that. Send /help to see what I can do.")


def _on_callback(cfg, st, cb):
    data = cb.get("data")
    tg.answer(cb["id"], "Working on it...")
    if st.get("status") != "awaiting_approval" or not st.get("final"):
        tg.send("That preview is no longer active. Send /script to start again.")
        return
    tg.clear_buttons(st["final"]["msg"])
    if data == "approve":
        _deliver(cfg, st, manual=False)
    elif data == "manual":
        _deliver(cfg, st, manual=True)
    elif data == "redo":
        st.update(clips=[], seen=[], final=None, status="waiting_clips")
        tg.send("Okay, send clip 1 again.")
    elif data == "skip":
        st["status"] = "skipped"
        tg.send("Skipped for today.")


def poll_once(cfg, timeout=0):
    st = load()
    handled = 0
    for u in tg.updates(st.get("offset", 0), timeout):
        st["offset"] = u["update_id"] + 1
        try:
            if "message" in u and str(u["message"]["chat"]["id"]) == tg.chat_id():
                _on_message(cfg, st, u["message"])
            elif "callback_query" in u and str(u["callback_query"]["message"]["chat"]["id"]) == tg.chat_id():
                _on_callback(cfg, st, u["callback_query"])
        except Exception as e:   # tell you, then carry on with the next message
            try:
                tg.send("Something went wrong: " + _esc(str(e))[:500])
            except Exception:
                pass
            print("error:", e, flush=True)
        handled += 1
        save(st)
    return handled
