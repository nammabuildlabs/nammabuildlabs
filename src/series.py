import json

PARTS = {"beginner": 1, "intermediate": 2, "advanced": 3}   # episodes per project, by complexity


def queue(cfg):
    """Deterministic episode list. Day N of the series = queue[N % len(queue)]."""
    P = json.load(open("projects.json"))
    ptr = {k: 0 for k in P}
    out = []
    while any(ptr[k] < len(P[k]) for k in P):
        for lvl in cfg["series"]["rotation"]:
            if ptr[lvl] < len(P[lvl]):
                title = P[lvl][ptr[lvl]]
                ptr[lvl] += 1
                n = PARTS[lvl]
                out += [{"title": title, "level": lvl, "part": i + 1, "parts": n} for i in range(n)]
    return out
