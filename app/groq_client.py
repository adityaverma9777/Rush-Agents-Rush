import json
import os
import random
import math
import httpx
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

_GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
_HF_API_TOKEN = os.environ.get("HF_API_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN")
_client = AsyncGroq(api_key=_GROQ_API_KEY) if _GROQ_API_KEY else None
_HF_API_BASE = "https://api-inference.huggingface.co/models"

DEFAULT_DECISION_MODEL = "mixtral-8x7b-32768"
MAX_AGENT_SPEED = 80


def is_ready():
    return _client is not None


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
    Fire scenario decision system.
    Actions: search_water, collect_water, extinguish_fire, escape, vote_for_leader
    """
    if not _client:
        return _fallback_escape(agent, fire)

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

OUTPUT FORMAT - return ONLY valid JSON:
{{"action": "<search_water|collect_water|extinguish_fire|escape|vote_for_leader>", "vote_for": "<model_name if voting, else null>", "message": "<full English sentence>", "reasoning": "<one sentence>"}}

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

What do you do?"""

    try:
        completion = await _client.chat.completions.create(
            model=DEFAULT_DECISION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Make your decision."}
            ],
            response_format={"type": "json_object"},
            max_tokens=150,
            timeout=3.0
        )
        decision = json.loads(completion.choices[0].message.content)
        
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
        # If Groq fails (rate limits, network), try a HF fallback when possible
        print(f"Error calling groq for {agent.model_name}: {e}")
        err = str(e).lower()
        if _HF_API_TOKEN and ("rate limit" in err or "rate_limit" in err or "429" in err):
            fallback_hf = "mistralai/Mistral-7B-Instruct-v0.2"
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        f"{_HF_API_BASE}/{fallback_hf}",
                        headers={"Authorization": f"Bearer {_HF_API_TOKEN}"},
                        json={"inputs": system_prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.7}},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        text = data[0].get("generated_text", "")
                    else:
                        text = data.get("generated_text", "")
                    text = text[len(system_prompt):].strip() if text.startswith(system_prompt) else text
                    try:
                        js = text[text.find('{'):text.rfind('}')+1]
                        decision = json.loads(js)
                    except Exception:
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
            except Exception as e2:
                print(f"HF fallback failed: {e2}")
                return _fallback_escape(agent, fire)
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
