"""
pipeline.py

PersonaPulse - Full Pipeline
------------------------------------------
Wires all 5 agents together in order, taking a persona_id all the way from
raw news fetching to a final, ready-to-show digest. Updates intermediate
output JSON files in the data folder at every step.

Order:
  1. News Fetch Agent
  2. Filtering and Ranking Agent
  3. Content Reshaping Agent
  4. Insight Generation Agent
  5. Presentation Agent
"""

import asyncio
import json
import os
import re
import sys
from dotenv import load_dotenv

from google.adk.runners import InMemoryRunner
from google.genai import types

# Load environment variables
load_dotenv()

from news_fetch_agent import news_fetch_agent, save_output_to_data_folder
from ranking_and_filtering_agent import ranking_and_filtering_agent, save_ranking_output
from content_reshaping_agent import content_reshaping_agent, save_reshaping_output
from insight_generation_agent import insight_generation_agent, save_insight_output
from presentation_agent import build_final_digest, save_presentation_output


# ---------------------------------------------------------------------------
# Helper: safely pull a JSON object out of an LLM text reply
# ---------------------------------------------------------------------------

def extract_json(text: str) -> dict:
    """
    Finds the first {...} block in a block of text and parses it as JSON.
    Handles unescaped quotes and markdown code fences.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text[:200]}")

    json_str = match.group(0).replace("\\'", "'")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        snippet_start = max(0, e.pos - 60)
        snippet_end = min(len(json_str), e.pos + 60)
        print(f"  [ERROR] JSON parse failed near: ...{json_str[snippet_start:snippet_end]}...")
        raise


# ---------------------------------------------------------------------------
# Runner helper for a single ADK agent step
# ---------------------------------------------------------------------------

APP_NAME = "persona_pulse"
USER_ID = "pipeline_user"


async def run_agent_step(agent, input_text: str, session_id: str) -> str:
    """
    Runs a single ADK agent with the given input text in a fresh session.
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
                if getattr(part, "function_response", None):
                    last_tool_output = part.function_response.response
                if part.text:
                    final_text += part.text

    if not final_text.strip():
        if last_tool_output is not None:
            final_text = json.dumps(last_tool_output)

    return final_text


# ---------------------------------------------------------------------------
# Full Pipeline Execution
# ---------------------------------------------------------------------------

async def run_pipeline(persona_id: str) -> dict:
    """
    Runs the full 5-agent PersonaPulse pipeline for persona_id and
    saves intermediate step outputs into the data directory.
    """
    print("=" * 65)
    print(f" PersonaPulse Pipeline Execution (Persona: {persona_id}) ")
    print("=" * 65)

    # -----------------------------------------------------------------------
    # Step 1: News Fetch Agent
    # -----------------------------------------------------------------------
    print("\n[Step 1/5] Running News Fetch Agent...")
    step1_raw_text = await run_agent_step(
        news_fetch_agent,
        f"Fetch this week's news for persona_id '{persona_id}'.",
        session_id="step1_fetch",
    )
    step1_data = extract_json(step1_raw_text)
    save_output_to_data_folder(step1_data)
    print(f"  [SUCCESS] News Fetch Agent Executed Successfully!")
    print(f"    - Persona: {step1_data.get('persona')}")
    print(f"    - Raw Articles Fetched: {step1_data.get('article_count', len(step1_data.get('articles', [])))}")
    print(f"    - Output saved to: data/news_fetch_agent_output.json")

    # -----------------------------------------------------------------------
    # Step 2: Ranking and Filtering Agent
    # -----------------------------------------------------------------------
    print("\n[Step 2/5] Running Ranking & Filtering Agent...")
    step2_raw_text = await run_agent_step(
        ranking_and_filtering_agent,
        f"Rank and filter these articles for the persona: {json.dumps(step1_data)}",
        session_id="step2_rank",
    )
    step2_data = extract_json(step2_raw_text)
    save_ranking_output(step2_data)
    print(f"  [SUCCESS] Ranking & Filtering Agent Executed Successfully!")
    print(f"    - Persona: {step2_data.get('persona')}")
    print(f"    - Top Articles Kept: {len(step2_data.get('articles', []))}")
    print(f"    - Output saved to: data/ranking_and_filtering_agent_output.json")

    # -----------------------------------------------------------------------
    # Step 3: Content Reshaping Agent
    # -----------------------------------------------------------------------
    print("\n[Step 3/5] Running Content Reshaping Agent...")
    step3_raw_text = await run_agent_step(
        content_reshaping_agent,
        f"Reshape these ranked articles for the persona: {json.dumps(step2_data)}",
        session_id="step3_reshape",
    )
    step3_data = extract_json(step3_raw_text)
    save_reshaping_output(step3_data)
    print(f"  [SUCCESS] Content Reshaping Agent Executed Successfully!")
    print(f"    - Persona: {step3_data.get('persona')}")
    print(f"    - Reshaped Articles Count: {len(step3_data.get('articles', []))}")
    print(f"    - Output saved to: data/content_reshaping_agent_output.json")

    # -----------------------------------------------------------------------
    # Step 4: Insight Generation Agent
    # -----------------------------------------------------------------------
    print("\n[Step 4/5] Running Insight Generation Agent...")
    step4_raw_text = await run_agent_step(
        insight_generation_agent,
        f"Generate the weekly insight for this persona: {json.dumps(step3_data)}",
        session_id="step4_insight",
    )
    step4_data = extract_json(step4_raw_text)
    save_insight_output(step4_data)
    print(f"  [SUCCESS] Insight Generation Agent Executed Successfully!")
    print(f"    - Generated Insight Summary: \"{step4_data.get('insight')}\"")
    print(f"    - Output saved to: data/insight_generation_agent_output.json")

    # -----------------------------------------------------------------------
    # Step 5: Presentation Agent
    # -----------------------------------------------------------------------
    print("\n[Step 5/5] Running Presentation Agent...")
    final_digest = build_final_digest(
        persona=step4_data.get("persona", ""),
        insight=step4_data.get("insight", ""),
        articles=step4_data.get("articles", []),
    )
    save_presentation_output(final_digest)
    print(f"  [SUCCESS] Presentation Agent Executed Successfully!")
    print(f"    - Output saved to: data/presentation_agent_output.json")

    print("\n" + "=" * 65)
    print(" PIPELINE COMPLETED SUCCESSFULLY! ")
    print("=" * 65)

    return final_digest


if __name__ == "__main__":
    from news_fetch_agent import load_personas

    persona_arg = sys.argv[1] if len(sys.argv) > 1 else "all"

    if persona_arg.lower() in ("all", "--all"):
        personas = load_personas()
        all_results = {}
        print(f"\n[PIPELINE BATCH TEST] Testing all {len(personas)} personas: {list(personas.keys())}\n")

        for persona_id in personas.keys():
            print(f"\n>>> Running pipeline for persona: '{persona_id}'...")
            result = asyncio.run(run_pipeline(persona_id))
            all_results[persona_id] = result

        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_paths = [
            os.path.join(base_dir, "data", "all_personas_digests.json"),
            os.path.join(os.path.dirname(base_dir), "data", "all_personas_digests.json"),
        ]
        for path in target_paths:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2)

        print("\n" + "=" * 65)
        print(f" ALL PERSONAS PIPELINE TEST COMPLETED! ({len(all_results)} personas)")
        print(f" Consolidated output saved to: data/all_personas_digests.json")
        print("=" * 65)

    else:
        result = asyncio.run(run_pipeline(persona_arg))
        print("\nFINAL DIGEST PREVIEW:")
        print(json.dumps(result, indent=2))

