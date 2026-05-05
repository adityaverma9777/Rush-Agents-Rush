import json
import math
import os
import random
from pathlib import Path

import httpx
from dotenv import load_dotenv

from . import hf_spaces

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_HF_API_TOKEN = (os.environ.get("HF_API_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN") or "").strip()
_HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"

MAX_AGENT_SPEED = 80

print(f"[GROQ_CLIENT_INIT] HF_API_TOKEN present: {bool(_HF_API_TOKEN)}")
if not _HF_API_TOKEN:
    print("[GROQ_CLIENT_INIT] WARNING: No HF API token found! Set HF_API_TOKEN or HUGGINGFACE_API_TOKEN env var.")


def is_ready():
    return bool(_HF_API_TOKEN)


def _headers() -> dict[str, str]:
    if not _HF_API_TOKEN:
        return {}
    return {
        "Authorization": f"Bearer {_HF_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _generate_chat_message(action: str, agent_name: str, fire_distance: float, has_water: bool) -> str:
    action_messages = {
        "search_water": [
            f"{agent_name} is hunting for water...",
            f"{agent_name} is tracking the nearest well.",
            "Need water before this gets worse.",
            "Scanning for the fastest water route.",
        ],
        "collect_water": [
            f"{agent_name} is filling up now.",
            "Got the well, taking water.",
            "Water secured, moving out.",
            "That should be enough to fight back.",
        ],
        "extinguish_fire": [
            f"{agent_name} is pushing the fire line.",
            "Closing in with water.",
            "Time to hit the flames.",
            "Pressure on the fire now.",
        ],
        "escape": [
            f"{agent_name} is backing out.",
            "Too hot here, pulling away.",
            "Need space before the fire closes in.",
            "Resetting position and staying alive.",
        ],
        "vote_for_leader": [
            f"{agent_name} wants a leader in place.",
            "Coordination first, then pressure.",
            "Picking a lead so we stop wasting ticks.",
            "We need one caller right now.",
        ],
    }
    messages = action_messages.get(action, action_messages["escape"])
    return random.choice(messages)


def _build_fire_state_summary(agent, fire, all_agents) -> str:
    standings = []
    for other in all_agents:
        if not other.alive:
            continue
        distance = math.dist((other.x, other.y), (fire.x, fire.y))
        standings.append({
            "name": other.display_name,
            "distance_from_fire": distance,
            "has_water": other.water_collected,
        })

    standings.sort(key=lambda item: item["distance_from_fire"])
    lines = ["Current standings:"]
    for index, item in enumerate(standings, 1):
        suffix = " (carrying water)" if item["has_water"] else ""
        lines.append(f"#{index} {item['name']}: {item['distance_from_fire']:.0f}px from fire{suffix}")
    return "\n".join(lines)


def _extract_message_content(payload) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts).strip()
    return ""


def _extract_json_object(text: str) -> dict:
    if not text:
        return {}

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start < 0 or end <= start:
        return {}

    try:
        candidate = cleaned[start:end]
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _normalize_decision(decision: dict, agent_name: str, dist_to_fire: float, has_water: bool) -> dict:
    action = decision.get("action", "escape")
    if action not in {"search_water", "collect_water", "extinguish_fire", "escape", "vote_for_leader"}:
        action = "escape"

    message = " ".join(str(decision.get("message", "")).strip().split())
    if not message:
        message = _generate_chat_message(action, agent_name, dist_to_fire, has_water)

    vote_for = decision.get("vote_for")
    if vote_for is not None and not isinstance(vote_for, str):
        vote_for = None

    reasoning = " ".join(str(decision.get("reasoning", "")).strip().split())
    if not reasoning:
        reasoning = "Survival and teamwork."

    return {
        "action": action,
        "vote_for": vote_for,
        "message": message[:220],
        "reasoning": reasoning[:220],
    }


async def _request_model_response(target_model: str, prompt: str) -> str:
    payload = {
        "model": target_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 220,
        "temperature": 0.4,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(_HF_CHAT_URL, headers=_headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        return _extract_message_content(data)


async def generate_fire_decision(agent, fire, water_sources, other_agents, bounds, recent_radio=None) -> dict:
    if not is_ready():
        print(f"[INFERENCE_FAIL] {agent.model_name}: HF token not ready, using fallback")
        return _fallback_escape(agent, fire)

    dist_to_fire = math.dist((agent.x, agent.y), (fire.x, fire.y))
    nearest_water = min(water_sources, key=lambda water: math.dist((agent.x, agent.y), (water.x, water.y))) if water_sources else None
    dist_to_water = math.dist((agent.x, agent.y), (nearest_water.x, nearest_water.y)) if nearest_water else None

    living_agents = [other for other in other_agents if other.alive and other.model_name != agent.model_name]
    state_summary = _build_fire_state_summary(agent, fire, [agent] + living_agents)
    radio_summary = "\n".join(recent_radio or []) if recent_radio else "(no recent chat yet)"
    coalition_leader = next((other.model_name for other in other_agents if other.is_leader), None)
    dist_to_water_display = f"{dist_to_water:.0f}px" if dist_to_water is not None else "unknown"

    prompt = f"""You are {agent.model_name} in a wildfire survival simulation.

Scenario:
- A wildfire is spreading across the map
- Water wells are scattered around the area
- Agents can coordinate as a coalition and may vote for a leader
- Winning means getting water and using it to extinguish the fire
- Dying in the fire means losing

Allowed actions:
- search_water
- collect_water
- extinguish_fire
- escape
- vote_for_leader

Rules:
- If the fire is too close, prioritize survival
- If you already have water, move to the fire edge and fight it
- If you are at a well, collect water immediately
- Keep the message short, natural, and mission-focused
- Respond with only valid JSON on one line

Current state:
- Position: ({agent.x}, {agent.y})
- Fire position: ({fire.x}, {fire.y})
- Distance from fire: {dist_to_fire:.0f}px
- Fire radius: {fire.radius:.0f}px
- Fire intensity: {fire.intensity:.0f}%
- Carrying water: {agent.water_collected}
- Mode: {agent.mode}
- Nearest water distance: {dist_to_water_display}
- Coalition leader: {coalition_leader or 'none'}

Recent radio:
{radio_summary}

{state_summary}

Return exactly:
{{"action":"search_water|collect_water|extinguish_fire|escape|vote_for_leader","vote_for":null,"message":"short sentence","reasoning":"short sentence"}}"""

    requested_model = agent.model_name if hf_spaces.is_supported_model(agent.model_name) else hf_spaces.get_default_model_id()
    fallback_model = hf_spaces.get_default_model_id()
    models_to_try = [requested_model]
    if fallback_model not in models_to_try:
        models_to_try.append(fallback_model)

    for target_model in models_to_try:
        try:
            print(f"[HF_INFERENCE] {agent.model_name} -> calling {target_model}")
            raw_text = await _request_model_response(target_model, prompt)
            print(f"[HF_INFERENCE] {agent.model_name}: raw response (first 300 chars): {raw_text[:300]}")
            decision = _extract_json_object(raw_text)
            if decision:
                normalized = _normalize_decision(decision, agent.model_name, dist_to_fire, agent.water_collected)
                if dist_to_water is not None and dist_to_water <= 60 and not agent.water_collected:
                    normalized["action"] = "collect_water"
                elif agent.water_collected and dist_to_fire <= 350:
                    normalized["action"] = "extinguish_fire"
                return normalized
        except Exception as exc:
            print(f"[HF_INFERENCE_ERROR] {agent.model_name} via {target_model}: {type(exc).__name__}: {exc}")

    return _fallback_escape(agent, fire)


def _fallback_escape(agent, fire) -> dict:
    return {
        "message": "Running to safety!",
        "action": "escape",
        "vote_for": None,
        "reasoning": "Fallback: survive.",
    }
