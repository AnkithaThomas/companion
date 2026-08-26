"""
Companion — v2: Persona + Topic Steering + Transcript Capture
================================================================

What changed from the v1 PoC (agent.py):
1. Real persona — warm, unhurried, steers through a topic bank instead of
   a generic "have a nice chat" instruction.
2. Transcript capture — every turn (agent + user) is saved with a
   timestamp to a local JSON file when the session ends. This is the
   foundation the signal-extraction work (response latency, filler rate,
   etc.) will build on later — you can't measure timing without first
   capturing it.

Still no database, no scheduler, no dual-mode entry. Just the next two
things it made sense to prove out: does the persona feel right, and can
we actually capture what we need for the metrics work later.

--------------------------------------------------------------------------
WHAT'S NEW, TECHNICALLY
--------------------------------------------------------------------------
- TOPIC_BANK: the list of things the agent tries to gently cover in a call.
- SYSTEM_PROMPT: built from the topic bank, tells Claude how to behave.
- conversation_item_added event: LiveKit fires this every time a turn
  (user or agent) is finalized. We hook it to append to an in-memory list.
- On session close, we write that list to companion_sessions/<timestamp>.json

--------------------------------------------------------------------------
RUN IT
--------------------------------------------------------------------------
Same as before:
    py agent.py dev
Then connect via agents-playground.livekit.io like last time.

After you hang up, check the companion_sessions/ folder — a new .json
file should appear with your full transcript and timestamps.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import deepgram, anthropic, elevenlabs, silero

load_dotenv()

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

# where transcripts get saved locally for now (no DB yet)
SESSIONS_DIR = Path(__file__).parent / "companion_sessions"


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=anthropic.LLM(model="claude-sonnet-4-6"),
        tts=elevenlabs.TTS(),
    )

    # in-memory transcript buffer for this one session
    turns: list[dict] = []
    session_start = time.time()

    @session.on("conversation_item_added")
    def _on_item(event):
        item = event.item
        # item.content can be a string or a list of content blocks depending
        # on provider — normalize to plain text defensively.
        text = item.text_content if hasattr(item, "text_content") else str(item.content)
        turns.append(
            {
                "role": item.role,
                "text": text,
                "elapsed_seconds": round(time.time() - session_start, 3),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    await session.start(
        room=ctx.room,
        agent=Agent(instructions=SYSTEM_PROMPT),
    )

    await session.generate_reply(
        instructions="Greet the person warmly with something simple and "
        "brief, like you're picking up the phone to catch up with a "
        "friend. Ask one easy opening question — nothing more."
    )

    # wait here until the session actually ends on its own (participant
    # hangs up / disconnects) — do NOT call session.aclose() ourselves,
    # that would end the call immediately instead of letting it run.
    call_ended = asyncio.Event()

    @session.on("close")
    def _on_close(event):
        call_ended.set()

    await call_ended.wait()

    # write out the transcript now that the call is over
    SESSIONS_DIR.mkdir(exist_ok=True)
    out_path = SESSIONS_DIR / f"session_{int(session_start)}.json"
    with open(out_path, "w") as f:
        json.dump(
            {
                "started_at": datetime.utcfromtimestamp(session_start).isoformat(),
                "duration_seconds": round(time.time() - session_start, 3),
                "topic_bank": TOPIC_BANK,
                "turns": turns,
            },
            f,
            indent=2,
        )
    print(f"[companion] saved transcript -> {out_path}")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
