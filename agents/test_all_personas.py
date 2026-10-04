"""
test_all_personas.py

PersonaPulse - Test All Agents Across All Personas
---------------------------------------------------
Runs the full 5-agent pipeline across every persona defined in data/personas.json.

Agents Executed Per Persona:
  1. News Fetch Agent (via MCP & NewsAPI)
  2. Ranking & Filtering Agent
  3. Content Reshaping Agent
  4. Insight Generation Agent
  5. Presentation Agent
"""

import asyncio
import json
import os
import sys

from news_fetch_agent import load_personas
from pipeline import run_pipeline


async def main():
    personas = load_personas()
    persona_keys = list(personas.keys())

    print("=" * 70)
    print(" PersonaPulse - Comprehensive Multi-Persona Agent Testing ")
    print("=" * 70)
    print(f"Loaded {len(persona_keys)} personas from personas.json: {persona_keys}\n")

    summary_results = {}

    for idx, persona_id in enumerate(persona_keys, 1):
        display_name = personas[persona_id].get("display_name", persona_id)
        print(f"\n[{idx}/{len(persona_keys)}] Testing Pipeline for Persona: '{display_name}' ({persona_id})")
        print("-" * 70)

        try:
            digest = await run_pipeline(persona_id)
            summary_results[persona_id] = {
                "status": "SUCCESS",
                "display_name": display_name,
                "article_count": digest.get("article_count", 0),
                "insight_summary": digest.get("insight", "")[:120] + "...",
                "digest": digest,
            }
            print(f"\n[PASSED] '{display_name}' test completed successfully.")
        except Exception as e:
            summary_results[persona_id] = {
                "status": "FAILED",
                "display_name": display_name,
                "error": str(e),
            }
            print(f"\n[FAILED] '{display_name}' test failed: {e}")

    # Display Test Matrix Report
    print("\n" + "=" * 70)
    print(" AGENT TEST MATRIX RESULTS ")
    print("=" * 70)
    print(f"{'PERSONA ID':<22} | {'DISPLAY NAME':<20} | {'STATUS':<8} | {'ARTICLES':<8}")
    print("-" * 70)
    for pid, res in summary_results.items():
        status = res["status"]
        count = res.get("article_count", "N/A")
        dname = res.get("display_name", pid)
        print(f"{pid:<22} | {dname:<20} | {status:<8} | {count:<8}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
