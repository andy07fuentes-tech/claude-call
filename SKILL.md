---
name: claude-call
description: Phone the user through their "Claude Call" Retell agent to ask one question when you are blocked on a decision and they are away from the computer. Use ONLY when the user has said in this session that you may call them (e.g. "call me if you need me", "I'm stepping out, call me if you're stuck", "/claude-call"). Never call on your own initiative otherwise.
---

# Claude Call

The user's phone rings, a voice agent reads your question, and their spoken answer comes
back to you as text. It costs money per minute and interrupts them, so it's for real
decisions only.

## When to call

Call only if all of these are true:
1. The user said in **this session** that you may call them.
2. You are blocked on a **decision only they can make**, and you can't keep making progress
   on another part of the task while you wait.
3. You already sent a push notification (PushNotification, if available) about it, and they
   didn't answer within about 10 minutes. Skip this step only if they said to call right away.

Do not call for:
- **Permission prompts.** Approvals reach their phone through Claude Code's Remote Control;
  a call can't approve them.
- Progress updates, "done" messages, or anything a push notification covers.
- Anything you can decide yourself with a sensible default. Make the call and tell them later.

## Write the question

- One question, under 300 characters, written to be heard rather than read.
- Give clear options when you can: "Should I A, or B?"
- Plain language, no file paths, code or jargon.
- **Privacy:** the question is sent to Retell and spoken over the phone, and Retell keeps
  the transcript. Never include other people's names, phone numbers or emails, customer
  data, call transcripts, or any key or password. Describe the decision without them
  ("the client's booking page", not the client's name). Privacy laws such as Québec's
  Law 25 or the GDPR may apply to that data.

## Place the call

Run it with the Bash tool in the background (`run_in_background: true`), because a call can
last several minutes. You'll be notified when it ends:

```bash
python3 ~/.claude/skills/claude-call/call_me.py "Your question here?"
```

`python3 ~/.claude/skills/claude-call/call_me.py --check` checks the setup without calling.

## Read the result

The script prints JSON and exits with:

| Exit | Outcome | What to do |
|---|---|---|
| 0 | `answered` | Read `you_said` (their exact words). If it clearly answers the question, act on it and say in your next message what you decided based on the call. If it's ambiguous, don't guess: send a push notification with what's unclear and wait. |
| 2 | `not_answered` | They didn't pick up or didn't answer. Send a push notification with the question. You may call **once more**, no sooner than 15 minutes later. After that, stop calling and wait. |
| 3 | `refused` | Quiet hours, the hourly limit, or a setup problem. Do not work around it. Send a push notification instead and explain in the session. |
| 4 | `error` | Retell or the phone line failed. Push-notify them, report the error text in the session, and don't retry more than once. |
| 124 | `timed_out` | The call ran past the wait limit. Report the `call_id` in the session. |

Never edit `config.json` or pass `--ignore-quiet-hours` to get around a limit unless the
user told you to in this session.
