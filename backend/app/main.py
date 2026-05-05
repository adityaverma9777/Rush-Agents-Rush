import asyncio
import json
import math
import random
import uuid
import os
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from .models import SimulationState, AgentModel, TickResponse, FireScenario, WaterSource
from .simulation import SimulationEngine, TICK_INTERVAL_SECONDS
from . import groq_client
from . import hf_spaces

app = FastAPI(title="Unhinged 2.0", version="0.2.0")

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_simulations: dict[str, SimulationState] = {}
START_TIME = time.time()

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

    # Create fire at clicked location
    sim.fire = FireScenario(x=req.x, y=req.y)

    # Generate 3-5 water sources scattered around the map
    num_sources = random.randint(3, 5)
    for i in range(num_sources):
        water_x = random.randint(100, req.x - 200) if req.x > 200 else random.randint(0, 400)
        if random.random() > 0.5:
            water_x = random.randint(req.x + 200, sim.map_width - 100) if req.x < sim.map_width - 200 else random.randint(sim.map_width - 400, sim.map_width)
        water_y = random.randint(100, sim.map_height - 100)
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
