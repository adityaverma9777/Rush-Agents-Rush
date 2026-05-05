import asyncio
import json
import math
import random
import uuid
import os
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .models import SimulationState, AgentModel, TickResponse, FireScenario, WaterSource
from .simulation import SimulationEngine, TICK_INTERVAL_SECONDS
from . import groq_client
from . import hf_spaces

app = FastAPI(title="Unhinged 2.0", version="0.2.0")

_DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]
_configured_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _configured_origins:
    ALLOWED_ORIGINS = [origin.strip() for origin in _configured_origins.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = _DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_simulations: dict[str, SimulationState] = {}
START_TIME = time.time()


def _safe_randint(low: int, high: int) -> int:
    """Return a valid random int even if bounds are inverted."""
    if low > high:
        low, high = high, low
    return random.randint(low, high)

class StartSimulationRequest(BaseModel):
    model_names: list[str] = Field(..., min_length=2, max_length=6)
    scenario: str = "fire"
    map_width: int = 1200
    map_height: int = 800

class StartSimulationResponse(BaseModel):
    simulation_id: str
    state: SimulationState

class PlaceFireRequest(BaseModel):
    simulation_id: str
    x: int
    y: int

class TickRequest(BaseModel):
    simulation_id: str

@app.get("/")
async def root():
    return {
        "service": "rush-agents-backend",
        "status": "ok",
        "groq_available": groq_client.is_ready(),
    }

@app.get("/wake")
async def wake():
    return {
        "warm": True,
        "groq_available": groq_client.is_ready(),
        "uptime_seconds": int(time.time() - START_TIME),
    }

@app.get("/available-models")
async def get_available_models():
    """Get list of available models (Groq + HF Spaces) for the UI."""
    return await hf_spaces.get_available_models()

@app.post("/start-simulation", response_model=StartSimulationResponse)
async def start_simulation(req: StartSimulationRequest):
    if req.scenario != "fire":
        raise HTTPException(status_code=400, detail="Only 'fire' scenario supported.")

    agents = _spawn_agents(req.model_names, req.map_width, req.map_height)

    state = SimulationState(
        simulation_id=str(uuid.uuid4()),
        scenario=req.scenario,
        map_width=req.map_width,
        map_height=req.map_height,
        agents=agents,
        fire=None,
        water_sources=[],
        round=0,
        status="waiting_for_scenario",
    )

    active_simulations[state.simulation_id] = state
    return StartSimulationResponse(simulation_id=state.simulation_id, state=state)

@app.post("/place-fire", response_model=SimulationState)
def place_fire(req: PlaceFireRequest):
    sim = _get_or_404(req.simulation_id)
    if sim.status != "waiting_for_scenario":
        raise HTTPException(status_code=409, detail="Fire already placed or simulation finished.")

    # Create fire at a clamped location inside map bounds.
    fire_x = max(0, min(req.x, sim.map_width))
    fire_y = max(0, min(req.y, sim.map_height))
    sim.fire = FireScenario(x=fire_x, y=fire_y)

    # Generate 3-5 water sources scattered around the map
    num_sources = random.randint(3, 5)
    x_margin = 80
    y_margin = 80
    x_min = x_margin
    x_max = max(x_margin, sim.map_width - x_margin)
    y_min = y_margin
    y_max = max(y_margin, sim.map_height - y_margin)

    for i in range(num_sources):
        # Prefer spawning wells to one side of the fire, but always keep ranges valid.
        left_low = x_min
        left_high = min(fire_x - 180, x_max)
        right_low = max(fire_x + 180, x_min)
        right_high = x_max

        pick_left = random.random() < 0.5
        if pick_left and left_low <= left_high:
            water_x = _safe_randint(left_low, left_high)
        elif right_low <= right_high:
            water_x = _safe_randint(right_low, right_high)
        elif left_low <= left_high:
            water_x = _safe_randint(left_low, left_high)
        else:
            water_x = _safe_randint(x_min, x_max)

        water_y = _safe_randint(y_min, y_max)
        sim.water_sources.append(WaterSource(id=f"water_{i}", x=water_x, y=water_y))

    sim.status = "running"
    return sim

@app.websocket("/ws/{simulation_id}")
async def simulation_ws(websocket: WebSocket, simulation_id: str):
    await websocket.accept()
    sim = active_simulations.get(simulation_id)
    if not sim:
        await websocket.close(code=1008)
        return

    try:
        while True:
            if sim.status == "waiting_for_scenario":
                await asyncio.sleep(1)
                continue
            
            if sim.status == "finished":
                await websocket.send_json({"type": "finished", "state": sim.model_dump()})
                await websocket.close(code=1000)
                return

            engine = SimulationEngine(sim)
            result = await engine.tick()
            active_simulations[simulation_id] = result.state
            
            # DEBUG: log outgoing TickResponse summary for troubleshooting
            try:
                agent_states = [(a.model_name, a.alive) for a in result.state.agents]
            except Exception:
                agent_states = str(result.state)
            print(f"WS_SEND sim={simulation_id} round={result.round} agents={agent_states} events={len(result.events)}")

            await websocket.send_json(result.model_dump())
            
            if result.state.status == "finished":
                await websocket.close(code=1000)
                return
                
            await asyncio.sleep(TICK_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        pass

def _spawn_agents(model_names: list[str], width: int, height: int) -> list[AgentModel]:
    min_gap = 100
    positions = []
    agents = []
    for name in model_names:
        for _ in range(100):
            x = random.randint(100, width - 100)
            y = random.randint(100, height - 100)
            if all(math.dist((x, y), p) >= min_gap for p in positions):
                positions.append((x, y))
                break
        else:
            positions.append((x, y))

        agents.append(AgentModel(
            model_name=name,
            display_name=name.split("/")[-1].split("-")[0].capitalize(),
            x=positions[-1][0],
            y=positions[-1][1],
            alive=True
        ))
    return agents

def _get_or_404(simulation_id: str) -> SimulationState:
    sim = active_simulations.get(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim
