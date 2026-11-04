import threading


def call_with_deadline(fn, seconds, what="request"):
    """Run fn() and give up after `seconds`, whatever the SDK's own timeout does. The worker is a daemon thread,
    so a stuck call cannot keep the job alive."""
    box = {}

    def work():
        try:
            box["value"] = fn()
        except BaseException as e:   # hand any error back to the caller
            box["error"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise TimeoutError(f"The {what} took longer than {seconds / 60:.0f} minutes.")
    if "error" in box:
        raise box["error"]
    return box["value"]
