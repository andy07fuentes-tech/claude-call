"""Small helpers shared by call_me.py and the setup scripts.

Standard library only. Secrets come from the macOS Keychain and are never printed.
"""
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
API = "https://api.retellai.com"
RETELL_KEY_SERVICE = "retell-api-key"
SIP_LOGIN_SERVICE = "twilio-sip-trunk"


class RetellError(Exception):
    pass


class KeychainError(Exception):
    pass


def keychain_password(service):
    """Return the password stored under a Keychain service name."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise KeychainError(f"Could not read the Keychain: {e}")
    if out.returncode != 0 or not out.stdout.strip():
        raise KeychainError(f'Nothing in the Keychain under "{service}".')
    return out.stdout.strip()


def keychain_account(service):
    """Return the account name stored with a Keychain entry (the SIP username)."""
    out = subprocess.run(["security", "find-generic-password", "-s", service],
                         capture_output=True, text=True, timeout=10)
    if out.returncode != 0:
        raise KeychainError(f'Nothing in the Keychain under "{service}".')
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith('"acct"<blob>="') and line.endswith('"'):
            return line[len('"acct"<blob>="'):-1]
    raise KeychainError(f'The "{service}" Keychain entry has no account name.')


def retell_key():
    return keychain_password(RETELL_KEY_SERVICE)


def retell(method, path, key, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RetellError(f"Retell answered {e.code} on {path}: {detail}")
    except urllib.error.URLError as e:
        raise RetellError(f"Could not reach Retell: {e.reason}")


def load_config_file():
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config_file(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
