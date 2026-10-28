# Installing Claude Call (instructions for Claude Code)

The user asked you to install this repo. Walk them through it one step at a time, in plain
language. Explain what each step does before you run it, and wait for them when a step
needs them.

## Ground rules

- **Never ask the user to paste a key or password into the chat.** Every secret goes into
  the macOS Keychain with a `security ... -w` command that the user runs in their own
  Terminal; it prompts for the value and hides what they type.
- Never print secrets, and never commit `config.json` or `calls.log`.
- Creating the agent and importing a number change the user's Retell account, and a test
  call costs a few cents. Say so and get their OK before each of those steps.
- Before installing, read the repo's files yourself (they're short) so you can answer
  questions about what they do.

## Steps

1. **Check the basics.** macOS (`uname` says Darwin) and `python3 --version` (3.9 or newer).
   The tool uses the macOS Keychain, so it doesn't run on Windows or Linux as is.

2. **Retell account and key.** The user needs a Retell account (retellai.com) and an API
   key from the Retell dashboard. Have them store it:
   ```bash
   security add-generic-password -s retell-api-key -a "$USER" -w
   ```
   Check it's there without showing it: `security find-generic-password -s retell-api-key >/dev/null && echo ok`.

3. **Settings.** Copy `config.example.json` to `config.json`. Ask for their first name
   (the agent greets them with it) and their cell number in E.164 format (`+1...`), and
   fill in `your_name` and `to_number`. Leave the quiet hours and limits as they are unless
   they want different ones.

4. **Create the agent.** Show them the dry run, then create it once they agree:
   ```bash
   python3 setup/create_agent.py --dry-run
   python3 setup/create_agent.py            # or --voice <id> for another voice
   ```
   This saves `agent_id` in `config.json`.

5. **A number to call from.** Ask which case applies:
   - **They bought a number inside Retell:** put it in `from_number`. Retell-bought
     numbers can only call US numbers.
   - **They have a number at Twilio (or another SIP provider)**, which is the usual case
     outside the US: they need an Elastic SIP trunk with a termination URI (ends in
     `.pstn.twilio.com`) and either a credential list or Retell's IPs allowed. Have them
     store the trunk login, then import:
     ```bash
     security add-generic-password -s twilio-sip-trunk -a <sip-username> -w
     python3 setup/import_number.py +1XXXXXXXXXX --termination-uri <trunk>.pstn.twilio.com --dry-run
     python3 setup/import_number.py +1XXXXXXXXXX --termination-uri <trunk>.pstn.twilio.com
     ```
     Use a number that nothing else uses. This saves `from_number` in `config.json`.

6. **Check and test.** `python3 call_me.py --check`, then, with their OK, one test call
   (run it in the background):
   ```bash
   python3 call_me.py "This is a test call. Can you hear me clearly?"
   ```
   If it fails with `telephony_provider_permission_denied`, the trunk login is wrong:
   have them fix the Keychain entry (`security add-generic-password -U ...`) and run
   `python3 setup/set_trunk_auth.py +1XXXXXXXXXX`, then test again.

7. **Install the skill** so every Claude Code session can use it:
   ```bash
   mkdir -p ~/.claude/skills/claude-call
   rsync -a --exclude .git --exclude calls.log ./ ~/.claude/skills/claude-call/
   ```
   Tell them how to use it: when they step away, say "call me if you need me" in the
   session. For approvals and "done" alerts on their phone, they can also turn on
   Remote Control (`/remote-control`) with push notifications.

## Undo

- In Retell: delete the "Claude Call" agent, its LLM, and the imported number.
- `rm -rf ~/.claude/skills/claude-call`
- `security delete-generic-password -s retell-api-key` and, if used,
  `security delete-generic-password -s twilio-sip-trunk`.
