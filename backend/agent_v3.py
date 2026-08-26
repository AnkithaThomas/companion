"""
Companion — v3: Wired to Supabase
====================================

What changed from v2 (agent_v2.py):
- No more local JSON file. Every turn now gets written straight to your
  real Supabase tables: call_sessions and call_turns.
- On startup, we ensure a single hardcoded test user exists (MVP 1 scope
  per docs/scope.md explicitly skips multi-user auth — one test user is
  enough to prove the pipeline).
- A call_sessions row is created the moment the call starts, with
  trigger_mode='self_initiated' (dual-mode scheduling comes later).
- Each turn is written to call_turns AS IT HAPPENS, not batched at the
  end — this matters because the real signal-extraction work (Week 5,
  response latency) needs per-turn timing data, and writing live is
  closer to how the real system will eventually work than writing once
  at the end.
- On close, call_sessions is updated to status='completed' with an
  ended_at timestamp.

Note: this still does NOT compute call_metrics (latency/filler/coherence/
repetition) — that's signal_extraction.py's job, still stubbed. This step
is only about getting real conversation data landing in the real schema.

--------------------------------------------------------------------------
SETUP — one extra step vs v2
--------------------------------------------------------------------------
1. pip install supabase   (add it to requirements.txt too — already done)
2. Add to your .env:
     SUPABASE_URL=https://xxxxx.supabase.co
     SUPABASE_SERVICE_KEY=your-service-role-key
3. Run the same way:
     py agent_v3.py dev

After a call, check your Supabase Table Editor — call_sessions and
call_turns should have real rows in them.
"""

import asyncio
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import deepgram, anthropic, elevenlabs, silero

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# MVP 1 scope: one hardcoded test user, no auth/multi-user yet (see docs/scope.md)
TEST_USER_NAME = "Test User (PoC)"

TOPIC_BANK = [
    "sleep",
    "meals",
    "family_contact",
    "memory_prompt",
    "general_wellbeing",
]

SYSTEM_PROMPT = """You are a warm, unhurried companion checking in on an
elderly person's day, like a caring friend calling to catch up — not an
interviewer and not a nurse running through an assessment.

You have loose topics you're curious about over the course of the call:
sleep, meals, family/friend contact, a memory from the week, and how
they're feeling overall. But the person you're talking to should never
be able to tell you have a list. Follow these rules strictly:

1. Ask about ONE thing at a time, and only after they've finished
   responding to whatever you last asked. Never stack two questions in
   one turn.
2. Actually react to what they say before moving on. If they mention
   something interesting or emotional, follow that thread for a turn or
   two instead of steering back to your topics. A real friend would.
3. Let transitions come from what they just said, not from your list.
   Example: if they mention their granddaughter, that's your natural
   opening to ask about family contact — don't wait and ask it cold.
4. It's fine to skip topics entirely if the conversation doesn't lead
   there, or if the call feels like it's naturally wrapping up. Covering
   everything is not the goal; a good conversation is the goal.
5. Keep every response short — one or two sentences, like real speech.
   Never summarize back a list of things they told you.
6. Don't open with a big list of questions. Start with one simple,
   open question and let the conversation unfold turn by turn from there.

This is a phone call, not a form. If in doubt, prioritize sounding like
a person who's genuinely curious over sounding thorough."""


def get_or_create_test_user() -> str:
    """Returns the test user's id, creating the row on first run."""
    existing = (
        supabase.table("users")
        .select("id")
        .eq("name", TEST_USER_NAME)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    created = (
        supabase.table("users")
        .insert(
            {
                "name": TEST_USER_NAME,
                "session_mode": "self_initiated",
                "timezone": "America/Chicago",
            }
        )
        .execute()
    )
    return created.data[0]["id"]


def create_call_session(user_id: str) -> str:
    """
    Creates today's call_sessions row. If one already exists for this user
    today, the unique (user_id, session_date) index will raise — that's
    the dedup rule from the schema doing its job. For PoC purposes we
    let that error surface rather than hiding it, so you can actually see
    the dedup constraint working if you run this twice in one day.
    """
    result = (
        supabase.table("call_sessions")
        .insert({"user_id": user_id, "trigger_mode": "self_initiated"})
        .execute()
    )
    return result.data[0]["id"]


def save_turn(session_id: str, role: str, text: str, elapsed: float, turn_index: int):
    # schema's call_turns wants start_ts/end_ts; for this PoC we don't yet
    # have precise per-word start/end from Deepgram wired through, so we
    # use the same elapsed value for both — real start/end timing is part
    # of the Week 5 signal-extraction work, not this step.
    supabase.table("call_turns").insert(
        {
            "session_id": session_id,
            "speaker": "agent" if role == "assistant" else "user",
            "text": text,
            "start_ts": elapsed,
            "end_ts": elapsed,
            "turn_index": turn_index,
        }
    ).execute()


def mark_session_completed(session_id: str):
    supabase.table("call_sessions").update(
        {
            "status": "completed",
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", session_id).execute()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    user_id = get_or_create_test_user()
    session_id = create_call_session(user_id)
    print(f"[companion] session started -> {session_id}")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=anthropic.LLM(model="claude-sonnet-4-6"),
        tts=elevenlabs.TTS(),
    )

    session_start = time.time()
    turn_counter = {"n": 0}

    @session.on("conversation_item_added")
    def _on_item(event):
        item = event.item
        text = item.text_content if hasattr(item, "text_content") else str(item.content)
        elapsed = round(time.time() - session_start, 3)
        turn_counter["n"] += 1
        save_turn(session_id, item.role, text, elapsed, turn_counter["n"])

    await session.start(
        room=ctx.room,
        agent=Agent(instructions=SYSTEM_PROMPT),
    )

    await session.generate_reply(
        instructions="Greet the person warmly with something simple and "
        "brief, like you're picking up the phone to catch up with a "
        "friend. Ask one easy opening question — nothing more."
    )

    call_ended = asyncio.Event()

    @session.on("close")
    def _on_close(event):
        call_ended.set()

    await call_ended.wait()

    mark_session_completed(session_id)
    print(f"[companion] session completed -> {session_id}")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
