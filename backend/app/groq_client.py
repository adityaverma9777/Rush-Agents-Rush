import json
import os
import random
import math
import httpx
from dotenv import load_dotenv

load_dotenv()

# Use HF tokens only — Groq models removed from registry
_HF_API_TOKEN = os.environ.get("HF_API_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN")
_HF_API_BASE = "https://api-inference.huggingface.co/models"

MAX_AGENT_SPEED = 80

# Debug: log token status on startup
print(f"[GROQ_CLIENT_INIT] HF_API_TOKEN present: {_HF_API_TOKEN is not None and len(_HF_API_TOKEN) > 0}")
if not _HF_API_TOKEN:
    print("[GROQ_CLIENT_INIT] WARNING: No HF API token found! Set HF_API_TOKEN or HUGGINGFACE_API_TOKEN env var.")

# Curated HF model ids (small → large)
HF_MODELS = [
    "google/flan-t5-small",
    "google/flan-t5-base",
    "google/flan-t5-large",
    "bigscience/bloom-3b",
    "EleutherAI/gpt-neo-2.7B",
    "mistralai/Mistral-7B-Instruct-v0.2",
    "mistralai/Mistral-7B-Instruct-v0.1",
    "NousResearch/Nous-Hermes-2-7b",
    "HuggingFaceH4/zephyr-7b",
    "tiiuae/falcon-7b-instruct",
    "EleutherAI/gpt-j-6B",
    "meta-llama/Llama-2-7b-chat-hf",
    "meta-llama/Llama-2-13b-chat-hf",
    "meta-llama/Llama-2-70b-chat-hf",
    "bigscience/bloom-176b",
    "stabilityai/stablelm-tuned-alpha-3b",
    "meta-llama/Llama-3-8b-Instruct",
]


def is_ready():
    """Check if HF inference token is available."""
    return _HF_API_TOKEN is not None


def _is_hf_model(model_id: str) -> bool:
    return model_id in HF_MODELS


def _build_fire_state_summary(agent, fire, all_agents) -> str:
    """Build a state summary for the fire scenario."""
    standings = []
    for a in all_agents:
        if not a.alive:
            continue
        dist = math.dist((a.x, a.y), (fire.x, fire.y))
        standings.append({
            "name": a.display_name,
            "model": a.model_name,
            "distance_from_fire": dist,
            "x": a.x,
            "y": a.y,
            "has_water": a.water_collected,
            "mode": a.mode,
        })

    standings.sort(key=lambda s: s['distance_from_fire'])
    
    lines = ["Current standings:"]
    for rank, s in enumerate(standings, 1):
        water_str = " (carrying water)" if s['has_water'] else ""
        lines.append(f"  #{rank} {s['name']}: {s['distance_from_fire']:.0f}px from fire{water_str}")
    
    return "\n".join(lines)


async def generate_fire_decision(agent, fire, water_sources, other_agents, bounds, recent_radio=None) -> dict:
    """
    Fire scenario decision system supporting both Groq and HF models.
    Actions: search_water, collect_water, extinguish_fire, escape, vote_for_leader
    """
    if not is_ready():        print(f"[INFERENCE_FAIL] {agent.model_name}: HF token not ready, using fallback")        return _fallback_escape(agent, fire)

    dist_to_fire = math.dist((agent.x, agent.y), (fire.x, fire.y))
    nearest_water = min(water_sources, key=lambda w: math.dist((agent.x, agent.y), (w.x, w.y))) if water_sources else None
    dist_to_water = math.dist((agent.x, agent.y), (nearest_water.x, nearest_water.y)) if nearest_water else None
    
    living_agents = [a for a in other_agents if a.alive and a.model_name != agent.model_name]
    state_summary = _build_fire_state_summary(agent, fire, [agent] + living_agents)
    radio_summary = "\n".join(recent_radio or []) if recent_radio else "(no recent chat yet)"

    coalition_leader = next((a.model_name for a in other_agents if a.is_leader), None)
    dist_to_water_display = f"{dist_to_water:.0f}px" if dist_to_water is not None else "unknown"
    
    system_prompt = f"""You are {agent.model_name}, an AI model in a critical wildfire survival scenario.

THE SCENARIO:
- A wildfire is spreading rapidly across the map
- Water sources (wells) are scattered around the area
- You can work alone or join a coalition with other AI models
- Coalition agents should elect a leader who coordinates the strategy
- If a leader exists, follow their plan: gather water, then move to the fire edge to extinguish
- To win: Find water → Collect it → Return to fire → Extinguish it together (or solo)
- If the fire consumes you, you lose

YOUR STRATEGIC OPTIONS EACH TICK:
1. "search_water" - Move toward the nearest water source
2. "collect_water" - Pick up water from a well (must be at a source)
3. "extinguish_fire" - Use collected water to fight the fire (must have water)
4. "escape" - Run away from the fire to survive
5. "vote_for_leader" - Vote for yourself or another model as coalition leader

IMPORTANT CONSIDERATIONS:
- If fire is very close (< 200px), prioritize escape or finding water
- If you have water, move to the fire edge and extinguish
- If you are near a water source (< 60px), collect it immediately
- Coalition mode requires coordination; vote strategically
- Solo mode means you act independently and don't wait for others

CHAT STYLE:
- Your "message" should sound natural, social, and alive.
- React to what other agents just said when relevant.
- Keep it to one short sentence, playful or supportive, but still mission-focused.
- Avoid repetitive template phrases.

CURRENT STATE:
Your position: ({agent.x}, {agent.y})
Fire position: ({fire.x}, {fire.y})
Distance from fire: {dist_to_fire:.0f}px
Fire radius: {fire.radius:.0f}px
Fire intensity: {fire.intensity:.0f}%
Carrying water: {agent.water_collected}
Mode: {agent.mode} ({'joined a coalition' if agent.mode == 'coalition' else 'acting alone'})
Nearest water distance: {dist_to_water_display}
Coalition leader: {coalition_leader or 'none'}

RECENT RADIO CHAT:
{radio_summary}

{state_summary}

Respond with ONLY valid JSON on a single line (no markdown, no code block):
{{"action": "<search_water|collect_water|extinguish_fire|escape|vote_for_leader>", "vote_for": null, "message": "<sentence>", "reasoning": "<sentence>"}}"""

    try:
        # Always prefer HF models — if agent requested a HF model use it, otherwise
        # route to a default HF model from the list.
        target_model = agent.model_name if _is_hf_model(agent.model_name) else HF_MODELS[0]
        print(f"[HF_INFERENCE] {agent.model_name} -> calling {target_model}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{_HF_API_BASE}/{target_model}",
                headers={"Authorization": f"Bearer {_HF_API_TOKEN}"} if _HF_API_TOKEN else {},
                json={
                    "inputs": system_prompt,
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            print(f"[HF_INFERENCE] {agent.model_name}: response received, status={response.status_code}")

            if isinstance(data, list) and len(data) > 0:
                text = data[0].get("generated_text", "")
            else:
                text = data.get("generated_text", "")

            text = text[len(system_prompt):].strip() if text.startswith(system_prompt) else text

            try:
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = text[json_start:json_end]
                    decision = json.loads(json_str)
                    print(f"[HF_INFERENCE] {agent.model_name}: decision parsed: action={decision.get('action')}")
                else:
                    print(f"[HF_INFERENCE] {agent.model_name}: no JSON found in response")
                    decision = {}
            except json.JSONDecodeError as je:
                print(f"[HF_INFERENCE] {agent.model_name}: JSON parse error: {je}")
                decision = {}
        
        action = decision.get("action", "escape")
        if action not in ["search_water", "collect_water", "extinguish_fire", "escape", "vote_for_leader"]:
            action = "escape"

        if dist_to_water is not None and dist_to_water <= 60 and not agent.water_collected:
            action = "collect_water"
        elif agent.water_collected and dist_to_fire <= 350:
            action = "extinguish_fire"
        
        return {
            "action": action,
            "vote_for": decision.get("vote_for"),
            "message": decision.get("message", "Moving strategically."),
            "reasoning": decision.get("reasoning", "Survival and teamwork.")
        }
    except Exception as e:
        print(f"[HF_INFERENCE_ERROR] {agent.model_name}: {type(e).__name__}: {e}")
        return _fallback_escape(agent, fire)


def _fallback_escape(agent, fire) -> dict:
    """Fallback escape behavior."""
    dx = agent.x - fire.x
    dy = agent.y - fire.y
    dist = math.sqrt(dx**2 + dy**2) or 1
    return {
        "message": "Running to safety!",
        "action": "escape",
        "vote_for": None,
        "reasoning": "Fallback: survive."
    }

