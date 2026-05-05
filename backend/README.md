---
title: RUSH AGENTS RUSH Backend
emoji: 🔥
colorFrom: orange
colorTo: red
sdk: docker
pinned: false
---

# Rush Agents Rush Backend

FastAPI server driving the fire-suppression simulation.

## What It Does

- Accepts model selections and starts a new simulation.
- Places a fire on the map and generates water wells.
- Runs the tick-based AI loop with coalition voting, movement, and extinguishing.
- Streams state updates and events over WebSockets.

## Key Endpoints

- `GET /wake` - health and readiness check
- `GET /available-models` - list available models for the UI
- `POST /start-simulation` - create a new simulation
- `POST /place-fire` - place the fire and spawn water sources
- `WS /ws/{simulation_id}` - stream live simulation ticks

## Environment Variables

- `GROQ_API_KEY`: Required for agent decisions.
- `ALLOWED_ORIGINS`: CORS whitelist.

## Local Run

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Notes

- Simulation state is in memory.
- Fire growth, extinguish rate, and movement are tuned in `app/simulation.py`.
- Model decisions are generated in `app/groq_client.py`.
