"""Usage:
  python run.py draft [--sample] [--date YYYY-MM-DD]   build today's post (and reel) and notify you
  python run.py publish [--date YYYY-MM-DD]            publish an approved draft to Instagram
  python run.py health                                 check the Instagram token and message you
  python run.py alert --msg "text"                     send yourself a Telegram alert
"""
import argparse, json, os, sys
from datetime import date, datetime
from zoneinfo import ZoneInfo
import yaml
from src import render
from src.notify import notify, notify_video


def load():
    cfg = yaml.safe_load(open("config.yaml"))
    return cfg, json.load(open("calendar.json"))


def pick_date(cfg, arg):
    return date.fromisoformat(arg) if arg else datetime.now(ZoneInfo(cfg["timezone"])).date()


def entry_for(cfg, cal, d):
    n = (d - date.fromisoformat(cfg["start_date"])).days
    if n < 0:
        sys.exit("Before start_date: nothing scheduled yet.")
    return n + 1, cal[n % len(cal)]


def caption_of(post):
    tags = " ".join("#" + t.lstrip("#") for t in post["hashtags"][:5])
    return post["caption"].strip() + "\n\n" + tags


def save(rec):
    d = f"drafts/{rec['date']}"
    os.makedirs(d, exist_ok=True)
    json.dump(rec, open(f"{d}/post.json", "w"), indent=2, ensure_ascii=False)


def draft(cfg, cal, d, sample):
    if cfg.get("daily_format") == "series":
        return draft_series(cfg, d, sample)
    day_no, e = entry_for(cfg, cal, d)
    want_reel = day_no % cfg["reel_every_n_days"] == 0
    if sample:
        post = json.load(open("samples/sample.json"))
    else:
        from src.generate import generate
        post = generate(cfg, e, want_reel)
    out = f"out/{d}"
    os.makedirs(out, exist_ok=True)
    paths, n = [], len(post["slides"])
    for i, s in enumerate(post["slides"]):
        p = f"{out}/slide{i + 1}.jpg"
        kind = "cover" if i == 0 else ("cta" if i == n - 1 else "body")
        render.slide(cfg, s["title"], s["body"], i + 1, n, kind=kind).save(p, quality=92)
        paths.append(p)
    reel = None
    if want_reel and post.get("reel") and not sample:
        if cfg.get("reel_style") == "mascot":
            from src.mascot import build_reel
        else:
            from src.reel import build_reel
        reel = build_reel(cfg, post["reel"], f"{out}/reel")
    rec = {"date": str(d), "day": day_no, "pillar": e["pillar"], "topic": e["topic"],
           "caption": caption_of(post), "claims_to_verify": post.get("claims_to_verify", []),
           "slides": [], "reel": None, "ids": {}, "published": False}
    if sample or os.environ.get("SKIP_UPLOAD"):
        print("Local preview written to", out)
        return
    from src.storage import upload
    rec["slides"] = [upload(p, f"{d}/{os.path.basename(p)}") for p in paths]
    if reel:
        rec["reel"] = {"url": upload(reel[0], f"{d}/reel.mp4"), "cover": upload(reel[1], f"{d}/cover.jpg")}
    save(rec)
    claims = "\n".join("- " + c for c in rec["claims_to_verify"]) or "- none flagged"
    notify(f"Draft ready for {d} (day {day_no}, {e['pillar']})\nTopic: {e['topic']}\n\n"
           f"Slide 1: {rec['slides'][0]}\nReel: {rec['reel']['url'] if rec['reel'] else 'none today'}\n\n"
           f"Check these claims:\n{claims}\n\nCaption:\n{rec['caption']}\n\n"
           f"To approve: GitHub > Actions > Publish approved draft > Run workflow.")


def draft_series(cfg, d, sample):
    import shutil
    from src.series import queue
    from src.assemble import assemble
    n = (d - date.fromisoformat(cfg["start_date"])).days
    if n < 0:
        sys.exit("Before start_date: nothing scheduled yet.")
    q = queue(cfg)
    ep = q[n % len(q)]
    dry = sample or os.environ.get("DRY_SERIES")
    if dry:
        script = json.load(open("samples/series_sample.json"))
    else:
        from src.generate import episode_script
        script = episode_script(cfg, ep)
    out = f"out/{d}"
    os.makedirs(out, exist_ok=True)
    clips = []
    for i, c in enumerate(script["clips"]):
        p = f"{out}/clip{i + 1}.mp4"
        if dry:
            shutil.copy(os.environ["TEST_CLIP"], p)
        else:
            from src.veo import gen_clip
            gen_clip(cfg, c["action"], c["line"], p)
        clips.append(p)
    video, cover = assemble(cfg, ep, script, clips, out)
    tags = " ".join("#" + t.lstrip("#") for t in script["hashtags"][:5])
    caption = script["caption"].strip() + "\n\n" + tags + "\n\nHosted by Nammi, our AI virtual host."
    print(f"Episode: {ep['title']} (part {ep['part']}/{ep['parts']}, {ep['level']}) -> {video}")
    if dry or os.environ.get("SKIP_UPLOAD"):
        return
    direct = cfg.get("hosting") == "direct"
    if direct:
        reel_rec = {"file": video}
    else:
        from src.storage import upload
        reel_rec = {"url": upload(video, f"{d}/reel.mp4"), "cover": upload(cover, f"{d}/cover.jpg")}
    rec = {"date": str(d), "day": n + 1, "pillar": ep["level"], "topic": f"{ep['title']} (part {ep['part']}/{ep['parts']})",
           "caption": caption, "claims_to_verify": script.get("claims_to_verify", []), "slides": [],
           "reel": reel_rec,
           "ids": {}, "published": False}
    save(rec)
    if direct:
        notify_video(video, f"Preview: {rec['topic']}")
    claims = "\n".join("- " + c for c in rec["claims_to_verify"]) or "- none flagged"
    notify(f"Video ready for {d}: {rec['topic']}\nPreview: {rec['reel'].get('url', 'the video sent above')}\n\nCheck these claims:\n{claims}\n\n"
           f"Caption:\n{caption}\n\nIt will publish at 9:00 IST if AUTO_PUBLISH is on. To stop it: GitHub > Actions > Hold today's post.")


def veo_test(cfg):
    from src.veo import gen_clip
    os.makedirs("out", exist_ok=True)
    p = gen_clip(cfg, "She waves and smiles.", "Hi, I am Nammi, virtual host of NammaBuildLabs. This is a test clip.", "out/veo-test.mp4")
    print("Wrote", p)


def publish(cfg, d):
    from src.instagram import publish_carousel, publish_reel, publish_reel_file
    path = f"drafts/{d}/post.json"
    if not os.path.exists(path):
        sys.exit(f"No draft found at {path}")
    rec = json.load(open(path))
    if rec["published"]:
        print("Already published.")
        return
    if os.path.exists(f"drafts/{d}/HOLD"):
        notify(f"Publishing on hold for {d}.")
        return
    ids = rec.setdefault("ids", {})
    try:
        if rec["slides"] and "carousel" not in ids:
            ids["carousel"] = publish_carousel(rec["slides"], rec["caption"])
            save(rec)
        if rec["reel"] and "reel" not in ids:
            if rec["reel"].get("file"):
                ids["reel"] = publish_reel_file(rec["reel"]["file"], rec["caption"])
            else:
                ids["reel"] = publish_reel(rec["reel"]["url"], rec["caption"], rec["reel"].get("cover"))
            save(rec)
        rec["published"] = True
        save(rec)
        notify(f"Published {d}: {ids}")
    except Exception as ex:
        save(rec)
        notify(f"Publish failed for {d}: {ex}")
        raise


def health():
    import requests
    from src.instagram import GRAPH
    r = requests.get(f"{GRAPH}/{os.environ['IG_USER_ID']}", params={"fields": "username", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30)
    if not r.ok:
        notify(f"Weekly check FAILED: Instagram rejected the token ({r.status_code}). Refresh IG_ACCESS_TOKEN. {r.text[:200]}")
        sys.exit(1)
    notify(f"Weekly check OK: connected as @{r.json().get('username')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["draft", "publish", "health", "alert", "veo-test", "llm-test", "cleanup"])
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--date")
    ap.add_argument("--msg")
    a = ap.parse_args()
    if a.mode == "alert":
        notify(a.msg or "A workflow failed. Open GitHub Actions for details.")
        sys.exit(0)
    if a.mode == "health":
        health()
        sys.exit(0)
    cfg, cal = load()
    if a.mode == "cleanup":
        from src.storage import cleanup
        cleanup()
        sys.exit(0)
    if a.mode == "llm-test":
        from src.series import queue
        from src.generate import episode_script
        print(json.dumps(episode_script(cfg, queue(cfg)[0]), indent=2, ensure_ascii=False))
        sys.exit(0)
    if a.mode == "veo-test":
        veo_test(cfg)
        sys.exit(0)
    d = pick_date(cfg, a.date)
    draft(cfg, cal, d, a.sample) if a.mode == "draft" else publish(cfg, d)
