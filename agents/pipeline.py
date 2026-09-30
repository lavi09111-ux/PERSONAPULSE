"""
pipeline.py

PersonaPulse - Full Pipeline
------------------------------------------
Wires all 5 agents together in order, so running this file once takes a
persona_id all the way from raw news fetching to a final, ready-to-show
digest.

Order (matches the synopsis):
  1. News Fetch Agent
  2. Filtering and Ranking Agent
  3. Content Reshaping Agent
  4. Insight Generation Agent
  5. Presentation Agent (plain Python, wrapped as an ADK agent here)

How data flows between agents:
- Each LlmAgent (1 to 4) is asked to reply with ONLY a JSON object,
  nothing else. This file parses that JSON after each step, and feeds
  the parsed dict into the next agent as its input text. This keeps the
  chain reliable even though the agents in the middle are LLMs, since we
  never trust free text between steps, only parsed structured data.
- Agent 5 (Presentation) is plain Python, no LLM. It is called directly
  as a normal function at the very end, once agent 4 finished.

Assumes:
- NEWSAPI_KEY is set as an environment variable
- Either GOOGLE_API_KEY is set (for Google AI Studio), OR
  GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION are set along with
  GOOGLE_GENAI_USE_VERTEXAI=TRUE (for Vertex AI on GCP)
- All 5 agent files already exist in this same agents folder.
"""

import asyncio
import json
import re
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from news_fetch_agent import news_fetch_agent
from ranking_and_filtering_agent import ranking_and_filtering_agent
from content_reshaping_agent import content_reshaping_agent
from insight_generation_agent import insight_generation_agent
from presentation_agent import build_final_digest


# ---------------------------------------------------------------------------
# Helper: safely pull a JSON object out of an LLM text reply
# ---------------------------------------------------------------------------

def extract_json(text: str) -> dict:
    """
    Finds the first {...} block in a block of text and parses it as
    JSON. LLMs sometimes wrap JSON in extra words or code fences, so
    this looks for the outermost curly braces rather than assuming the
    whole reply is clean JSON.

    LLMs also sometimes write \\' (an escaped single quote), which is
    valid in Python or JavaScript strings but is NOT valid JSON. JSON
    only allows escaping a small fixed set of characters. This cleans
    that up before parsing, since otherwise a perfectly good JSON
    object fails to parse over one stray character.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text[:200]}")

    json_str = match.group(0)
    json_str = json_str.replace("\\'", "'")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        snippet_start = max(0, e.pos - 60)
        snippet_end = min(len(json_str), e.pos + 60)
        print(f"  [debug] JSON parse failed near: ...{json_str[snippet_start:snippet_end]}...")
        raise


# ---------------------------------------------------------------------------
# Run each step manually, parsing JSON between them
# (kept explicit and readable rather than deeply nested, for clarity)
# ---------------------------------------------------------------------------

APP_NAME = "persona_pulse"
USER_ID = "pipeline_user"


async def run_agent_step(agent, input_text: str, session_id: str) -> str:
    """
    Runs a single ADK agent with the given input text, in its own fresh
    session, and returns its raw text reply.
    """
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)

    await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    message = types.Content(role="user", parts=[types.Part(text=input_text)])

    final_text = ""
    last_tool_output = None
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    print(f"  [debug] tool called: {part.function_call.name}")
                if getattr(part, "function_response", None):
                    last_tool_output = part.function_response.response
                    print(f"  [debug] tool returned: {str(last_tool_output)[:300]}")
                if part.text:
                    final_text += part.text

    if not final_text.strip():
        if last_tool_output is not None:
            print("  [debug] No text reply from model - using raw tool output instead.")
            final_text = json.dumps(last_tool_output)
        else:
            print("  [debug] WARNING: agent produced no text output for this step.")

    return final_text


async def run_pipeline(persona_id: str) -> dict:
    """
    Runs the full 5-agent PersonaPulse pipeline for one persona_id and
    returns the final digest dict.
    """
    print(f"Step 1: Fetching news for persona_id={persona_id}")
    step1_text = await run_agent_step(
        news_fetch_agent,
        f"Fetch this week news for persona_id {persona_id}.",
        session_id="step1",
    )
    step1_data = extract_json(step1_text)

    print("Step 2: Ranking and filtering articles")
    step2_text = await run_agent_step(
        ranking_and_filtering_agent,
        f"Rank and filter these articles for the persona: {step1_data}",
        session_id="step2",
    )
    step2_data = extract_json(step2_text)

    print("Step 3: Reshaping articles into bullet points")
    step3_text = await run_agent_step(
        content_reshaping_agent,
        f"Reshape these ranked articles for the persona: {step2_data}",
        session_id="step3",
    )
    step3_data = extract_json(step3_text)

    print("Step 4: Generating weekly insight")
    step4_text = await run_agent_step(
        insight_generation_agent,
        f"Generate the weekly insight for this persona: {step3_data}",
        session_id="step4",
    )
    step4_data = extract_json(step4_text)

    print("Step 5: Building final digest")
    final_digest = build_final_digest(
        persona=step4_data.get("persona", ""),
        insight=step4_data.get("insight", ""),
        articles=step4_data.get("articles", []),
    )

    return final_digest


if __name__ == "__main__":
    persona_arg = sys.argv[1] if len(sys.argv) > 1 else "tech_professional"

    result = asyncio.run(run_pipeline(persona_arg))

    print("\nFINAL DIGEST:")
    print(json.dumps(result, indent=2))
