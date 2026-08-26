"""
Companion — Voice Pipeline Proof of Concept
=============================================

Goal: prove the full loop works before building anything else.
You speak -> Deepgram transcribes -> Claude replies -> ElevenLabs speaks it back.

No database. No routers. No scheduler. Just the voice loop, so the stack
stops being abstract and becomes something you can actually hear run.

--------------------------------------------------------------------------
HOW THE PIECES CONNECT (this is the whole architecture, for real this time)
--------------------------------------------------------------------------
LiveKit    -> the "room" / audio transport. Connects your mic to this script.
Deepgram   -> listens to you, turns speech into text (STT).
Claude     -> reads the text, decides what to say back.
ElevenLabs -> turns Claude's text reply into speech (TTS).

AgentSession (from livekit.agents) is the thing that wires all four
together for you — you just hand it each plugin, and it manages who's
"turn" it is to speak, streaming, interruptions, etc.

--------------------------------------------------------------------------
SETUP (do this before running)
--------------------------------------------------------------------------
1. pip install -r requirements.txt
2. Copy .env.example to .env and fill in your real API keys:
   - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET  (from livekit.io cloud project)
   - DEEPGRAM_API_KEY
   - ANTHROPIC_API_KEY
   - ELEVEN_API_KEY
3. Run in dev mode (opens a local test room + mic, no phone needed):
     python agent.py dev
   This opens a browser tab where you can talk to the agent directly.

--------------------------------------------------------------------------
WHAT TO EXPECT
--------------------------------------------------------------------------
The agent greets you, then just... talks. No topic steering, no metrics,
no memory of past calls. That's all later. Right now the only question
this file answers is: "does the pipeline work end to end?"
"""

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext
from livekit.plugins import deepgram, anthropic, elevenlabs, silero

load_dotenv()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),  # detects when you start/stop talking
        stt=deepgram.STT(model="nova-3"),
        llm=anthropic.LLM(model="claude-sonnet-4-6"),
        tts=elevenlabs.TTS(),
    )

    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions=(
                "You are a warm, unhurried companion checking in on someone's day. "
                "This is a proof-of-concept — just have a natural, brief conversation. "
                "Ask how their day is going and respond naturally to whatever they say."
            )
        ),
    )

    await session.generate_reply(
        instructions="Greet the person warmly and ask how their day is going."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
