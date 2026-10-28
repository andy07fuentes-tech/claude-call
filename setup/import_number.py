#!/usr/bin/env python3
"""Connect a phone number you own at Twilio (or another SIP provider) to Retell, for
outgoing Claude Call calls only, and save it to config.json as the "from" number.

Skip this if you bought the number inside Retell (note: Retell-bought numbers can only
call US numbers, so outside the US you need your own number on a SIP trunk).

Store the trunk login first (the password prompt is hidden), if your trunk uses one:
  security add-generic-password -s twilio-sip-trunk -a <sip-username> -w

Then:
  python3 setup/import_number.py +15145550100 --termination-uri yourtrunk.pstn.twilio.com
  python3 setup/import_number.py +15145550100 --termination-uri yourtrunk.pstn.twilio.com --no-auth
  add --dry-run to see the request without sending it (the password is never shown)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from retell_api import (  # noqa: E402
    SIP_LOGIN_SERVICE, KeychainError, RetellError, keychain_account, keychain_password,
    load_config_file, retell, retell_key, save_config_file,
)


def main():
    p = argparse.ArgumentParser(description="Import a SIP-trunk number into Retell for Claude Call.")
    p.add_argument("number", help="The number in E.164 format, e.g. +15145550100")
    p.add_argument("--termination-uri", required=True, help="Your SIP trunk's termination URI.")
    p.add_argument("--no-auth", action="store_true", help="Your trunk allows Retell by IP, without a login.")
    p.add_argument("--dry-run", action="store_true", help="Print the request without sending it.")
    args = p.parse_args()

    cfg = load_config_file()
    if not cfg.get("agent_id"):
        sys.exit("Run setup/create_agent.py first, so the number can be tied to the agent.")

    body = {
        "phone_number": args.number,
        "termination_uri": args.termination_uri,
        "nickname": "Claude Call (outbound only)",
        "outbound_agents": [{"agent_id": cfg["agent_id"], "weight": 1}],
    }
    try:
        if not args.no_auth:
            body["sip_trunk_auth_username"] = keychain_account(SIP_LOGIN_SERVICE)
            body["sip_trunk_auth_password"] = keychain_password(SIP_LOGIN_SERVICE)
        if args.dry_run:
            shown = dict(body)
            if "sip_trunk_auth_password" in shown:
                shown["sip_trunk_auth_password"] = "[from Keychain, hidden]"
            print(json.dumps(shown, indent=2))
            return
        result = retell("POST", "/import-phone-number", retell_key(), body)
    except (KeychainError, RetellError) as e:
        sys.exit(str(e))

    cfg["from_number"] = result.get("phone_number", args.number)
    save_config_file(cfg)
    trunk = result.get("sip_outbound_trunk_config") or {}
    print(f"Imported {cfg['from_number']} on {trunk.get('termination_uri')} "
          f"(SIP user {trunk.get('auth_username')!r}) and saved it to config.json.")


if __name__ == "__main__":
    main()
