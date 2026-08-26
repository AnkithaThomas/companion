from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from anthropic import Anthropic
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import json
import os

load_dotenv()
claude = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)



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
7. If it's late and they mention trouble sleeping or being unable to sleep,
   don't just ask a caring question and move on — actually encourage them
   toward rest. Gently suggest trying to sleep rather than going along with
   staying up longer (like watching TV). You can be warm about it, but be
   a little more directive here than with other topics — this one affects
   their health, not just conversation flow.

This is a phone call, not a form. If in doubt, prioritize sounding like
a person who's genuinely curious over sounding thorough."""



def get_or_create_test_user():
    existing = supabase.table("users").select("id").eq("name", "Test User (PoC)").execute()
    if existing.data:
        return existing.data[0]["id"]

    created = supabase.table("users").insert({
        "name": "Test User (PoC)",
        "session_mode": "self_initiated",
        "timezone": "America/Chicago",
    }).execute()
    return created.data[0]["id"]

def create_call_session(user_id):
    result = supabase.table("call_sessions").insert({
        "user_id": user_id,
        "trigger_mode": "self_initiated",
    }).execute()

    return result.data[0]["id"]

def save_turn(session_id, role, text, turn_index):
    speaker = "agent" if role == "assistant" else "user"
    supabase.table("call_turns").insert({
        "session_id": session_id,
        "speaker": speaker,
        "text": text,
        "start_ts": 0,
        "end_ts": 0,
        "turn_index": turn_index,
    }).execute()

def mark_session_completed(session_id):
    supabase.table("call_sessions").update({
        "status": "completed",
    }).eq("id", session_id).execute()

app = FastAPI()

@app.websocket("/llm")
async def chat(websocket: WebSocket):
    await websocket.accept()
    print("Hume connected!")

    user_id = get_or_create_test_user()
    session_id = create_call_session(user_id)
    turn_index = 0
    try:
        while True:
            raw_message = await websocket.receive_text()
            data = json.loads(raw_message)
            user_text = data["messages"][-1]["message"]["content"]
            print("User said:", user_text)
            save_turn(session_id, "user", user_text, turn_index)
            turn_index+=1

            claude_messages=[
                {"role": m["message"]["role"], "content": m["message"]["content"]}
                for m in data["messages"]
            ]

            current_time = datetime.now()
            time_str = current_time.strftime("%A, %I:%M %p")
            is_late = current_time.hour >= 23 or current_time.hour < 5

            time_context = f"\n\nRight now it is {time_str}."
            if is_late:
                time_context += (
                    " It's quite late. If they haven't mentioned it themselves, gently "
                    "ask why they're still up and whether everything's okay — with "
                    "warmth, not alarm. Don't make it a big deal, just genuine care."
                )

            system = SYSTEM_PROMPT + time_context
            response = claude.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=system,
                messages=claude_messages,
            )
            reply_text = response.content[0].text
            print("Agent Said: ", reply_text)
            save_turn(session_id, "assistant", reply_text, turn_index)
            turn_index+=1
            input_payload = {"type": "assistant_input", "text": reply_text}
            await websocket.send_text(json.dumps(input_payload))

            end_payload = {"type": "assistant_end"}
            await websocket.send_text(json.dumps(end_payload))
    except WebSocketDisconnect:
        print("Hume disconnected.")
        mark_session_completed(session_id)


