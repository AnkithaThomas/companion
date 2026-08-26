# Companion — Voice Pipeline PoC

One file. One goal: prove LiveKit + Deepgram + Claude + ElevenLabs actually
talk to each other before building anything real on top.

## Setup

1. Get accounts + API keys (free tiers exist for all of these):
   - [LiveKit Cloud](https://cloud.livekit.io) — free Build plan, ~1,000 min/mo
   - [Deepgram](https://deepgram.com) — STT
   - [Anthropic](https://console.anthropic.com) — Claude API
   - [ElevenLabs](https://elevenlabs.io) — TTS

2. Install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your keys.

4. Run it:
   ```
   python agent.py dev
   ```
   This opens a local test session — a browser tab where you can talk to
   the agent through your mic. No phone number or real call needed yet.

## What this proves

That the four services actually chain together: your voice in, text out,
Claude's reply, voice back out. Nothing else. No database, no topic
steering, no metrics.

## What comes after this works

Once you've heard it talk back successfully:
1. ✅ Tune `instructions` to sound more like the real Companion persona
2. ✅ Add topic steering (sleep, meals, family, memory-jog)
3. ✅ Start capturing transcript + timestamps (needed for the metrics later)
4. Only then does the Supabase/scheduler/dual-mode structure from the
   scaffold become worth building — right now it'd just be plumbing with
   nothing flowing through it.

## v2: persona + topic steering + transcript capture

`agent_v2.py` builds on `agent.py` (kept as-is so you always have the
minimal version to fall back to). Run it the same way:

```
py agent_v2.py dev
```

Differences from v1:
- The agent now has real instructions — warm, unhurried, gently steers
  through a topic bank (sleep, meals, family contact, a memory-jog
  question, general wellbeing) instead of generic small talk.
- Every turn (yours and the agent's) gets timestamped and saved. After
  you hang up, check the new `companion_sessions/` folder — a JSON file
  appears there with the full transcript and per-turn elapsed time.

## v3: wired to Supabase

`agent_v3.py` builds on v2's persona but replaces the local JSON file with
real writes to your Supabase project — `call_sessions` and `call_turns`
tables, using the schema from `supabase/migrations/0001_init.sql` in the
full project scaffold.

Extra setup vs v2:
1. Create a Supabase project (separate from Clario/Carma)
2. Run the schema SQL in the Supabase SQL Editor
3. Add to `.env`:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   ```
4. `pip install -r requirements.txt` again (adds the `supabase` package)

Run it the same way:
```
py agent_v3.py dev
```

MVP 1 scope note: this uses one hardcoded test user (no auth/multi-user
yet — see docs/scope.md), and only `self_initiated` trigger mode. The
dual-mode scheduler is a later step, not this one.

After a call, check your Supabase **Table Editor** — you should see a row
in `call_sessions` and one row per turn in `call_turns`. Note: `call_metrics`
stays empty for now — computing those (latency, filler rate, coherence,
repetition) is the signal-extraction step, still ahead.
