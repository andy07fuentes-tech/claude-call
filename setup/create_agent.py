#!/usr/bin/env python3
"""Create the "Claude Call" agent in your Retell account and save its id to config.json.

Reads the agent definition from agent/agent.json and your Retell key from the
macOS Keychain (service "retell-api-key").

  python3 setup/create_agent.py                     # create it with the default voice
  python3 setup/create_agent.py --voice cartesia-Maren
  python3 setup/create_agent.py --dry-run           # show what would be sent, create nothing
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from retell_api import ROOT, KeychainError, RetellError, load_config_file, retell, retell_key, save_config_file  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Create the Claude Call agent in Retell.")
    p.add_argument("--voice", help="Retell voice id (default: the one in agent/agent.json).")
    p.add_argument("--dry-run", action="store_true", help="Print the requests without sending them.")
    args = p.parse_args()

    spec = json.loads((ROOT / "agent" / "agent.json").read_text(encoding="utf-8"))
    llm_body = spec["llm"]
    agent_body = {
        "agent_name": spec["agent_name"],
        "voice_id": args.voice or spec["voice_id"],
        "language": spec["language"],
        "max_call_duration_ms": spec["max_call_duration_ms"],
        "end_call_after_silence_ms": spec["end_call_after_silence_ms"],
        "response_engine": {"type": "retell-llm", "llm_id": "<created in step 1>"},
    }

    if args.dry_run:
        print(json.dumps({"step_1_create_retell_llm": llm_body, "step_2_create_agent": agent_body}, indent=2))
        return

    if load_config_file().get("agent_id"):
        sys.exit("config.json already has an agent_id. Delete that line first if you really want a second agent.")

    try:
        key = retell_key()
        llm = retell("POST", "/create-retell-llm", key, llm_body)
        agent_body["response_engine"]["llm_id"] = llm["llm_id"]
        agent = retell("POST", "/create-agent", key, agent_body)
    except (KeychainError, RetellError) as e:
        sys.exit(str(e))

    cfg = load_config_file() or json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
    cfg["agent_id"] = agent["agent_id"]
    save_config_file(cfg)
    print(json.dumps({"agent_id": agent["agent_id"], "llm_id": llm["llm_id"],
                      "saved_to": "config.json"}, indent=2))


if __name__ == "__main__":
    main()
