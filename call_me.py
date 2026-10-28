#!/usr/bin/env python3
"""Have a Retell agent phone you, ask one question, and print your answer.

Usage:
  python3 call_me.py "Should I deploy the new page tonight, or wait for your review?"
  python3 call_me.py --check     # check config, key and limits; places no call

Exit codes:
  0    answered (your words are in "you_said")
  2    not answered (voicemail, declined, no pickup, silence)
  3    refused before calling (quiet hours, rate limit, bad config or question)
  4    Retell error
  124  timed out waiting for the call to end

Standard library only. The Retell API key is read from the macOS Keychain
(service "retell-api-key"); it is never printed or written to disk.
"""
import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timedelta

from retell_api import ROOT, KeychainError, RetellError, load_config_file, retell, retell_key

LOG_PATH = ROOT / "calls.log"
MAX_QUESTION_CHARS = 400
POLL_SECONDS = 5

# Ways a call can end without you actually answering the question.
NOT_ANSWERED = {
    "voicemail_reached", "ivr_reached", "dial_no_answer", "dial_busy",
    "user_declined", "inactivity", "error_user_not_joined", "registered_call_timeout",
}


def finish(code, **result):
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(code)


def load_config():
    cfg = load_config_file()
    if not cfg:
        finish(3, outcome="refused", reason="Missing config.json. Run the setup in INSTALL.md first.")
    missing = [k for k in ("from_number", "to_number", "agent_id") if not cfg.get(k)]
    if missing:
        finish(3, outcome="refused", reason=f"config.json is missing: {', '.join(missing)}")
    cfg.setdefault("your_name", "")
    cfg.setdefault("quiet_hours", {"start": "21:00", "end": "08:00"})
    cfg.setdefault("max_calls_per_hour", 3)
    cfg.setdefault("max_wait_seconds", 480)
    return cfg


def in_quiet_hours(cfg, now):
    start = datetime.strptime(cfg["quiet_hours"]["start"], "%H:%M").time()
    end = datetime.strptime(cfg["quiet_hours"]["end"], "%H:%M").time()
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # window crosses midnight


def calls_in_last_hour(now):
    if not LOG_PATH.exists():
        return 0
    cutoff = now - timedelta(hours=1)
    count = 0
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            if datetime.fromisoformat(json.loads(line)["placed_at"]) >= cutoff:
                count += 1
        except (ValueError, KeyError):
            continue
    return count


def log_call(entry):
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def check_limits(cfg, args, now):
    if in_quiet_hours(cfg, now) and not args.ignore_quiet_hours:
        q = cfg["quiet_hours"]
        finish(3, outcome="refused", reason=f"Quiet hours ({q['start']}-{q['end']}). No call placed.")
    used = calls_in_last_hour(now)
    if used >= cfg["max_calls_per_hour"]:
        finish(3, outcome="refused", reason=f"Already {used} calls in the last hour (limit {cfg['max_calls_per_hour']}).")


def wait_for_end(call_id, key, max_wait):
    deadline = time.monotonic() + max_wait
    call, failures = {}, 0
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            call = retell("GET", f"/v2/get-call/{call_id}", key)
            failures = 0
        except RetellError:
            failures += 1  # a dropped request mid-call is not a failed call
            if failures >= 6:
                raise
            continue
        if call.get("call_status") in ("ended", "error", "not_connected"):
            # The analysis lands a few seconds after the transcript; give it a moment.
            for _ in range(6):
                if call.get("call_analysis"):
                    break
                time.sleep(POLL_SECONDS)
                try:
                    call = retell("GET", f"/v2/get-call/{call_id}", key)
                except RetellError:
                    break
            return call
    return None


def main():
    p = argparse.ArgumentParser(description="Phone yourself with one question and print the answer.")
    p.add_argument("question", nargs="?", help="One short question, written to be spoken aloud.")
    p.add_argument("--check", action="store_true", help="Check config, key and limits without calling.")
    p.add_argument("--ignore-quiet-hours", action="store_true", help="Only when you said to call even at night.")
    args = p.parse_args()

    cfg = load_config()
    try:
        key = retell_key()
    except KeychainError as e:
        finish(3, outcome="refused", reason=str(e))
    now = datetime.now()

    if args.check:
        finish(0, outcome="ok", your_name=cfg["your_name"], from_number=cfg["from_number"],
               to_number=cfg["to_number"], agent_id=cfg["agent_id"],
               quiet_hours_now=in_quiet_hours(cfg, now), calls_last_hour=calls_in_last_hour(now),
               max_calls_per_hour=cfg["max_calls_per_hour"])

    question = " ".join((args.question or "").split())
    if not question:
        finish(3, outcome="refused", reason="No question given.")
    if len(question) > MAX_QUESTION_CHARS:
        finish(3, outcome="refused", reason=f"Question is {len(question)} characters; keep it under {MAX_QUESTION_CHARS} so it works spoken.")

    check_limits(cfg, args, now)

    try:
        call = retell("POST", "/v2/create-phone-call", key, {
            "from_number": cfg["from_number"],
            "to_number": cfg["to_number"],
            "override_agent_id": cfg["agent_id"],
            # The agent's prompt uses {{name}} and {{question}}; an empty name would be read aloud as-is.
            "retell_llm_dynamic_variables": {"question": question, "name": cfg["your_name"] or "there"},
            "metadata": {"source": "claude-call"},
            "idempotency_key": uuid.uuid4().hex,
        })
    except RetellError as e:
        finish(4, outcome="error", reason=str(e))

    call_id = call.get("call_id")
    log_call({"placed_at": now.isoformat(timespec="seconds"), "call_id": call_id, "question": question})

    try:
        done = wait_for_end(call_id, key, cfg["max_wait_seconds"])
    except RetellError as e:
        finish(4, outcome="error", call_id=call_id, reason=str(e))
    if done is None:
        finish(124, outcome="timed_out", call_id=call_id,
               reason=f"Call still running after {cfg['max_wait_seconds']}s. Check it in the Retell dashboard.")

    analysis = done.get("call_analysis") or {}
    reason = done.get("disconnection_reason")
    you_said = [u.get("content", "") for u in (done.get("transcript_object") or []) if u.get("role") == "user"]
    result = {
        "call_id": call_id,
        "disconnection_reason": reason,
        "duration_s": round((done.get("duration_ms") or 0) / 1000),
        "you_said": you_said,
        "transcript": done.get("transcript", ""),
        "summary": analysis.get("call_summary"),
    }

    if reason in NOT_ANSWERED or analysis.get("in_voicemail"):
        finish(2, outcome="not_answered", **result)
    if done.get("call_status") in ("error", "not_connected") or (reason or "").startswith("error_"):
        finish(4, outcome="error", **result)
    if not any(s.strip() for s in you_said):
        finish(2, outcome="not_answered", **result)
    finish(0, outcome="answered", **result)


if __name__ == "__main__":
    main()
