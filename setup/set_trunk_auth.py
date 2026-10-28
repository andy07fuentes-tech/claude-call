#!/usr/bin/env python3
"""Change the SIP trunk login Retell uses for a number that's already imported.

Use it when a test call fails with "telephony_provider_permission_denied" (wrong or
missing login). Reads the login from the Keychain (service "twilio-sip-trunk"; the
account is the SIP username) and never prints the password.

Store or replace the login first (the password prompt is hidden):
  security add-generic-password -U -s twilio-sip-trunk -a <sip-username> -w

Then:
  python3 setup/set_trunk_auth.py +15145550100
"""
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from retell_api import SIP_LOGIN_SERVICE, KeychainError, RetellError, keychain_account, keychain_password, retell, retell_key  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 setup/set_trunk_auth.py +1XXXXXXXXXX")
    number = sys.argv[1]
    try:
        body = {
            "auth_username": keychain_account(SIP_LOGIN_SERVICE),
            "auth_password": keychain_password(SIP_LOGIN_SERVICE),
        }
        result = retell("PATCH", "/update-phone-number/" + urllib.parse.quote(number), retell_key(), body)
    except (KeychainError, RetellError) as e:
        sys.exit(str(e))
    trunk = result.get("sip_outbound_trunk_config") or {}
    print(f"Updated {number}: SIP user now {trunk.get('auth_username')!r} on {trunk.get('termination_uri')}")


if __name__ == "__main__":
    main()
