"""Prompts for the Gemini app, and a no-AI fallback script."""


def _words(s, n):
    w = s.split()
    return " ".join(w[:n]).rstrip(" ,;:") + ("." if len(w) > n and not s.strip().endswith(".") else "")


def _clause(action):
    """One short clause starting with 'She', no full stop, so it can be followed by 'and says in ...'."""
    a = (action or "").strip().split(". ")[0].rstrip(".").strip()
    if not a:
        a = "She smiles at the camera"
    return a if a.lower().startswith("she ") else "She " + a[0].lower() + a[1:]


def app_prompt(cfg, action, line):
    """The prompt to paste into the Gemini app's video tool. Same fixed look every time, only the action and line change:
    <fixed look> She <action> and says in <speech style>: "<line>" <fixed ending>"""
    s = cfg["series"]
    return (f"{' '.join(s['host_prompt'].split())} {_clause(action)} and says in {s['speech_style']}: "
            f"\"{line}\" {s['prompt_ending']}")


def template_script(cfg, ep):
    """Used when no AI script is available. Plain, but always works."""
    t, part, parts = ep["title"], ep["part"], ep["parts"]
    note = (ep.get("note") or "").strip().rstrip(".")
    opener = "Hi, I am Nammi, virtual host of NammaBuildLabs." if part == 1 else "Welcome back."
    last = part == parts
    cta = "Want a mentor to build it with you? Registration link in bio." if last else "Join me next time for the next part."
    line1 = _words(f"{opener} Today: {t}.", 22)
    line2 = _words(f"{_words(note, 12) + ' ' if note else ''}{cta}", 22)
    caption = (f"{t}: part {part} of {parts}. {note + '. ' if note else ''}"
               f"Search \"{t.lower()}\" on GitHub for examples.")
    return {"episode_title": t, "caption": caption[:600],
            "hashtags": ["finalyearproject", "engineeringstudents", "bengaluru", "machinelearning", "python"],
            "clips": [{"action": "She waves, smiles at the camera" if part == 1 else "She smiles and nods at the camera", "line": line1},
                      {"action": "She gestures towards the floating cards beside her", "line": line2}],
            "claims_to_verify": ["Written from a template, not by AI. Read it before posting."]}
