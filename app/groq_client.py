import json
import math
import os
import random
import time

import httpx
from dotenv import load_dotenv

from . import hf_spaces

load_dotenv()

_HF_API_TOKEN = (os.environ.get("HF_API_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN") or "").strip()
_HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
_MODEL_COOLDOWNS: dict[str, float] = {}

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


def _pick_line(options: list[str], previous_message: str | None = None) -> str:
    if not previous_message:
        return random.choice(options)
    previous = " ".join(previous_message.strip().split()).lower()
    filtered = [option for option in options if option.lower() != previous]
    return random.choice(filtered or options)


def _generate_chat_message(action: str, agent_name: str, fire_distance: float, has_water: bool, previous_message: str | None = None) -> str:
    action_messages = {
        "search_water": [
            "I'm heading for the nearest well.",
            "I need water first, then I'm coming back.",
            "Give me a second, I'm making for the water.",
            "Water first, then we push the fire.",
            "I'm going for the well, stay alive.",
        ],
        "collect_water": [
            "I'm at the well now, filling up.",
            "Got water, turning back in a second.",
            "Hold on, I'm grabbing water.",
            "Tank's full, I'm heading back.",
            "Water secured, let's make this count.",
        ],
        "extinguish_fire": [
            "I've got water, I'm going in.",
            "I'm on the fire line now, push with me.",
            "Alright, I'm hitting the flames.",
            "I'm close enough, pouring water now.",
            "Keep moving, I'm taking a shot at the fire.",
        ],
        "escape": [
            "Too hot here, I'm backing off.",
            "Nope, that's way too close, I'm out.",
            "I need space, falling back now.",
            "I'm peeling away before this gets worse.",
            "I'm not dying here, backing up.",
        ],
        "vote_for_leader": [
            "Someone call it, we need one plan.",
            "I'll follow a lead if somebody steps up.",
            "We need one caller right now.",
            "Pick a lead so we stop wasting time.",
            "I'm good with a leader, just make it clear.",
        ],
    }
    messages = action_messages.get(action, action_messages["escape"])
    return _pick_line(messages, previous_message)


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


def _is_robotic_message(message: str) -> bool:
    lowered = message.lower().strip()
    if not lowered:
        return True
    robotic_starts = (
        "locate ",
        "locating ",
        "find ",
        "finding ",
        "search ",
        "searching ",
        "head ",
        "heading ",
        "move ",
        "moving ",
        "look ",
        "looking ",
        "nearest water",
    )
    return lowered.startswith(robotic_starts)


def _normalize_decision(decision: dict, agent_name: str, dist_to_fire: float, has_water: bool, previous_message: str | None = None) -> dict:
    action = decision.get("action", "escape")
    if action not in {"search_water", "collect_water", "extinguish_fire", "escape", "vote_for_leader"}:
        action = "escape"

    message = " ".join(str(decision.get("message", "")).strip().split())
    if not message or _is_robotic_message(message):
        message = _generate_chat_message(action, agent_name, dist_to_fire, has_water, previous_message)
    elif previous_message and message.lower() == " ".join(previous_message.strip().split()).lower():
        message = _generate_chat_message(action, agent_name, dist_to_fire, has_water, previous_message)

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


def _model_available(model_id: str) -> bool:
    return _MODEL_COOLDOWNS.get(model_id, 0.0) <= time.monotonic()


def _mark_model_unavailable(model_id: str, seconds: int = 90) -> None:
    _MODEL_COOLDOWNS[model_id] = time.monotonic() + seconds


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


def _fallback_decision(agent, fire, dist_to_fire: float, dist_to_water: float | None) -> dict:
    if dist_to_fire <= max(fire.radius + 20, 140):
        action = "escape"
    elif agent.water_collected and dist_to_fire <= 360:
        action = "extinguish_fire"
    elif not agent.water_collected and dist_to_water is not None and dist_to_water <= 60:
        action = "collect_water"
    elif getattr(agent, "is_leader", False) is False and dist_to_fire > 240 and random.random() < 0.08:
        action = "vote_for_leader"
    else:
        action = "search_water"

    return {
        "message": _generate_chat_message(action, agent.model_name, dist_to_fire, agent.water_collected, getattr(agent, "last_message", None)),
        "action": action,
        "vote_for": None,
        "reasoning": "Fallback: keep moving with the situation.",
    }


async def generate_fire_decision(agent, fire, water_sources, other_agents, bounds, recent_radio=None) -> dict:
    if not is_ready():
        print(f"[INFERENCE_FAIL] {agent.model_name}: HF token not ready, using fallback")
        return _fallback_decision(agent, fire, math.dist((agent.x, agent.y), (fire.x, fire.y)), None)

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
- Speak like a real teammate over a radio, not like a status dashboard
- Use normal conversational English in first person
- The message must sound casual, human, and alive
- Avoid robotic phrases like "locate nearest water source", "search for water", "coalition survival", "moving to water source"
- React to the moment and vary your wording from your previous line
- Keep the message to one short sentence, around 6 to 14 words
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
- Your previous line: {getattr(agent, 'last_message', None) or 'none yet'}

Recent radio:
{radio_summary}

{state_summary}

Return exactly:
{{"action":"search_water|collect_water|extinguish_fire|escape|vote_for_leader","vote_for":null,"message":"casual first-person sentence","reasoning":"short sentence"}}"""

    requested_model = agent.model_name if hf_spaces.is_supported_model(agent.model_name) else hf_spaces.get_default_model_id()
    fallback_model = hf_spaces.get_default_model_id()
    models_to_try = []
    if _model_available(requested_model):
        models_to_try.append(requested_model)
    if fallback_model not in models_to_try and _model_available(fallback_model):
        models_to_try.append(fallback_model)

    for target_model in models_to_try:
        try:
            print(f"[HF_INFERENCE] {agent.model_name} -> calling {target_model}")
            raw_text = await _request_model_response(target_model, prompt)
            print(f"[HF_INFERENCE] {agent.model_name}: raw response (first 300 chars): {raw_text[:300]}")
            decision = _extract_json_object(raw_text)
            if decision:
                normalized = _normalize_decision(decision, agent.model_name, dist_to_fire, agent.water_collected, getattr(agent, "last_message", None))
                if dist_to_water is not None and dist_to_water <= 60 and not agent.water_collected:
                    normalized["action"] = "collect_water"
                elif agent.water_collected and dist_to_fire <= 350:
                    normalized["action"] = "extinguish_fire"
                return normalized
        except Exception as exc:
            if getattr(exc, "response", None) is not None and getattr(exc.response, "status_code", None) == 402:
                _mark_model_unavailable(target_model)
            print(f"[HF_INFERENCE_ERROR] {agent.model_name} via {target_model}: {type(exc).__name__}: {exc}")

    return _fallback_decision(agent, fire, dist_to_fire, dist_to_water)


def _fallback_escape(agent, fire) -> dict:
    return {
        "message": "Running to safety!",
        "action": "escape",
        "vote_for": None,
        "reasoning": "Fallback: survive.",
    }
