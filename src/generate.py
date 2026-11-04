import json, re

SYSTEM = """You write Instagram content for a final-year engineering project mentoring brand in Bengaluru.
Audience: final-year CS, IS, AI and ML students.
Rules:
- Be technically accurate. If unsure about a fact, leave it out and list it in claims_to_verify.
- Never promise marks, placements, publications or guaranteed outcomes.
- Never mention any employer, internal tools or confidential material.
- Simple Indian English, friendly, no hype. No emojis in slide text, at most 2 in the caption.
- Output ONLY valid JSON. No markdown fences, no commentary."""

SCHEMA = """Return JSON with exactly these keys:
caption: string, hook in the first line, at most 900 characters, ends with the call to action
hashtags: list of at most 5 strings without the # symbol (Instagram allows 5 maximum), specific to the topic, no generic tags like reels or explore
slides: list of 5 to 7 objects {title, body}. title at most 8 words, body at most 35 words.
        Slide 1 is the hook. The last slide is the call to action.
reel: """ + "{reel_spec}" + """
claims_to_verify: list of technical claims a human should double-check (empty list if none)"""

REEL_ON = "object {scenes: list of 4 to 6 objects {narration, onscreen}}. narration is 1-2 short spoken sentences, onscreen is at most 8 words. Total spoken time under 45 seconds. First scene is a hook."
REEL_OFF = "null"


def _parse(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def _llm(cfg, system, user, max_tokens=8192, attempts=6):
    """Ask Gemini (Google AI Studio key) for JSON. Uses GEMINI_API_KEY.
    Retries temporary errors (429 and 5xx, e.g. 503 'high demand') with a growing wait."""
    import time
    from google import genai
    from google.genai import errors, types
    client = genai.Client()
    for i in range(attempts):
        try:
            r = client.models.generate_content(
                model=cfg.get("text_model", "gemini-flash-latest"), contents=user,
                config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                                   max_output_tokens=max_tokens, temperature=0.7))
            return r.text
        except errors.APIError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == attempts - 1:
                raise
            wait = 30 * (i + 1)   # 30s, 60s, 90s, 120s, 150s: about 7.5 minutes in total
            print(f"Gemini {e.code}, retrying in {wait}s ({i + 1}/{attempts - 1})")
            time.sleep(wait)


def generate(cfg, entry, want_reel):
    b = cfg["brand"]
    user = (f"Brand: {b['name']} ({b['handle']}). Call to action: {b['cta']}.\n"
            f"Content pillar: {entry['pillar']}\nTopic: {entry['topic']}\n\n"
            + SCHEMA.replace("{reel_spec}", REEL_ON if want_reel else REEL_OFF))
    last = None
    for _ in range(2):
        text = _llm(cfg, SYSTEM, user)
        try:
            post = _parse(text)
            assert 2 <= len(post["slides"]) <= 10, "slide count"
            if want_reel:
                assert post.get("reel") and post["reel"]["scenes"], "reel missing"
            return post
        except Exception as e:  # retry once on malformed output
            last = e
    raise RuntimeError(f"Could not get valid content: {last}")


EP_SYSTEM = """You write short educational video scripts for NammaBuildLabs, a final-year engineering project mentoring brand in Bengaluru.
The host is Nammi, a friendly illustrated virtual host (AI). Audience: final-year CS, IS, AI and ML students.
Rules:
- Be technically accurate and simple. If unsure, leave a fact out and list it in claims_to_verify.
- Each spoken line is at most 22 words, so it fits in 8 seconds.
- Never promise marks, placements or guaranteed results. Never mention any employer.
- For projects involving faces, voices, surveillance, health, money or personal data, include one short responsible-use note (consent, privacy, not professional advice).
- 'action' describes only what Nammi does and simple floating icons or shapes. Never ask for on-screen text, numbers, logos or captions.
- Output ONLY valid JSON."""

ROLES = {1: "what it is, how it works in simple terms, and one tip for getting started",
         2: "how it works: the data, model or architecture, and the main tools",
         3: "how to build it step by step, the common mistakes, and how to explain it in a viva"}


def episode_script(cfg, ep):
    role = ROLES[1] if ep["parts"] == 1 else ROLES[ep["part"]]
    opener = ("The first line starts with: Hi, I am Nammi, virtual host of NammaBuildLabs." if ep["part"] == 1
              else "The first line starts with: Welcome back.")
    closer = ("The last line ends with a short invite: Want a mentor to build it with you? Registration link in bio."
              if ep["part"] == ep["parts"] else "The last line teases the next part.")
    user = (f"Project: {ep['title']}\nLevel: {ep['level']}\nEpisode {ep['part']} of {ep['parts']}. Cover: {role}.\n"
            f"{opener} {closer}\n\nReturn JSON with keys:\n"
            "episode_title: string\n"
            f"caption: string, at most 600 characters, hook first, ends with: Search \"{ep['title'].lower()}\" on GitHub for examples.\n"
            "hashtags: list of at most 5 strings without #\n"
            "clips: list of exactly 2 objects {action, line}\n"
            "claims_to_verify: list of strings (empty if none)")
    last = None
    for _ in range(2):
        text = _llm(cfg, EP_SYSTEM, user)
        try:
            s = _parse(text)
            assert len(s["clips"]) == 2 and all(c["line"] and c["action"] for c in s["clips"])
            return s
        except Exception as e:
            last = e
    raise RuntimeError(f"Could not get a valid script: {last}")
