"""Cheap check (standard library only): are there new Telegram messages? Lets the poll job skip the heavy setup when idle."""
import json, os, urllib.request

tok = os.environ.get("TELEGRAM_TOKEN")
try:
    off = json.load(open("tg_state.json")).get("offset", 0)
except Exception:
    off = 0
has = "false"
if tok:
    try:
        res = json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getUpdates?offset={off}&limit=1&timeout=0", timeout=20))
        has = "true" if res.get("result") else "false"
    except Exception as e:
        print("peek failed, running the full job to be safe:", e)
        has = "true"
with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
    f.write(f"has={has}\n")
print("new messages:", has)
