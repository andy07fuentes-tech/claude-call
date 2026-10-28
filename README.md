# Claude Call

Let Claude Code phone you when it's stuck on a decision while you're away from your computer.

Your phone rings, a voice agent reads Claude's question, and your spoken answer goes back
to Claude as text so it can keep working. Built on [Retell AI](https://www.retellai.com)
for the voice agent and your own phone number for the call.

```
Claude Code ──► call_me.py ──► Retell API ──► your phone rings
     ▲                                             │
     └────────── your answer, as text ◄────────────┘
```

It's for questions only. For approvals ("may I run this?") and "job done" alerts, use
Claude Code's built-in Remote Control with push notifications, which is free.

## How it works

1. Claude runs `call_me.py "Should I deploy tonight, or wait for your review?"`.
2. The script asks Retell to call your cell from your number, with the Claude Call agent
   and the question filled in.
3. The agent greets you by name, reads the question, takes down your answer, repeats it
   back and hangs up. You can interrupt it at any time.
4. The script reads the call transcript from Retell and prints your exact words for Claude.

Nothing runs in the background and nothing on your computer is exposed to the internet:
the script only sends requests to Retell's API and checks back until the call ends.

## Requirements

- **macOS.** Keys are kept in the macOS Keychain.
- **Python 3.9+.** Standard library only, nothing to install.
- **Claude Code.**
- **A Retell account and API key.** You pay Retell for your own calls.
- **A phone number connected to Retell.** Numbers bought inside Retell can only call US
  numbers. Outside the US, use your own Twilio number on an Elastic SIP trunk.

## Install

The easy way: clone the repo, open Claude Code in the folder and say:

> Install claude-call by following INSTALL.md.

Claude walks you through it step by step: your Retell key, your name and number, creating
the agent, connecting the number, a test call, and installing the skill. You never paste
a key or password into the chat; secrets go straight into the macOS Keychain.

To do it by hand, follow the same steps in [INSTALL.md](INSTALL.md).

## Use it

When you step away, tell Claude in the session: **"call me if you need me."** Claude only
calls when you've said that, and only for a decision it can't make on its own.
The rules it follows are in [SKILL.md](SKILL.md).

## Safety limits

- No calls unless you allowed them in the current session.
- No calls during quiet hours (21:00 to 08:00 by default, in `config.json`).
- At most 3 calls an hour, counted from a local log.
- Questions are capped at 400 characters.
- Your Retell key and SIP password stay in the Keychain. Your numbers live in
  `config.json`, which git ignores.

## Cost

You pay Retell (and your phone provider) per minute. On Retell's pricing as of
October 2026 with the default setup (GPT-4.1, a standard voice, your own SIP number),
that's about **$0.115 USD a minute** plus about 2 cents per call for the after-call
summary, plus your provider's rate (Twilio to Canada: about $0.01 a minute).
A typical call lasts under a minute. Check current prices on retellai.com and your
provider's site.

## Privacy

Claude's question and your answer go through Retell (and the language model it uses), and
Retell stores the transcript and recording under your account's settings. The skill tells
Claude never to put other people's details, customer data or secrets in a question.

## Responsible use

This tool is built to call **you**, at a number you own. Changing it to call other people
puts you under telemarketing and consent rules (for example CASL in Canada or the TCPA in
the US). That's your responsibility.

## Files

| File | What it is |
|---|---|
| `call_me.py` | Places one call, waits for it to end, prints the answer as JSON. |
| `retell_api.py` | Shared helpers: Keychain reads and Retell API requests. |
| `SKILL.md` | The rules Claude follows: when it may call and what to do with the result. |
| `INSTALL.md` | Step-by-step install, written for Claude Code to follow with you. |
| `agent/agent.json` | The voice agent's script and settings. |
| `setup/create_agent.py` | Creates the agent in your Retell account. |
| `setup/import_number.py` | Connects your own number to Retell over a SIP trunk. |
| `setup/set_trunk_auth.py` | Fixes the SIP login on an already-connected number. |
| `config.example.json` | Settings template. |

## Undo

Delete the agent, its LLM and the number in Retell, remove `~/.claude/skills/claude-call`,
and delete the Keychain entries (`security delete-generic-password -s retell-api-key`,
and `-s twilio-sip-trunk` if you used it).

## License

[MIT](LICENSE). Not affiliated with Anthropic or Retell AI.
