---
title: RUSH AGENTS RUSH
emoji: 🔥
colorFrom: red
colorTo: yellow
sdk: docker
sdk_version: latest
python_version: "3.11"
pinned: false
---

# RUSH AGENTS RUSH

> *Different models. One fire. Real teamwork or chaos.*

Rush Agents Rush is a 2D multi-agent simulation where real AI models are dropped onto a map, a fire is placed, and the models must cooperate to survive and extinguish it. They vote for a leader, search for water, move as a coalition, and try to put the fire out before it consumes the map.

The current design has fully moved on from the old volcano/lava loop. The game is now about fire suppression, coalition strategy, and visible agent coordination.

## Core Idea

1. Pick 2-6 supported Hugging Face router models.
2. Start a simulation and click the map to place the fire.
3. Agents decide each tick whether to search water, collect water, extinguish fire, escape, or vote for a leader.
4. Fire grows over time, but water collection and extinguishing reduce intensity.
5. The game ends when the fire is fully extinguished or the agents are wiped out.

## Features

- Real model names and visible per-agent positions on the map
- Coalition voting and leader election
- Water wells placed around the fire arena
- Fire growth and deterministic extinguishing logic
- WebSocket-driven live simulation updates
- Chat feed with varied team-style messages
- End-of-game winner text showing the strongest extinguisher

## Tech Stack

| Layer | Tech |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python, Uvicorn |
| AI | Hugging Face Router chat completions |
| Realtime | WebSockets |

## Repository Layout

- [app](app): FastAPI app used by the Hugging Face Space Docker runtime
- [backend](backend): Local/backend mirror of the FastAPI app for development
- [frontend](frontend): Next.js UI, map rendering, chat feed, model selection

## Local Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000.

## Environment Variables

### Backend

```env
HUGGINGFACE_API_TOKEN=your_hf_token
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## API Overview

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /wake | Health and readiness check |
| GET | /available-models | List available models for the UI |
| POST | /start-simulation | Create a new simulation |
| POST | /place-fire | Place the fire and generate water wells |
| WS | /ws/{simulation_id} | Stream simulation ticks and events |

## Simulation Loop

Each tick the backend:

1. Collects decisions from all living agents in parallel.
2. Runs coalition voting if a leader has not been chosen.
3. Moves agents toward water or the fire edge based on their current action.
4. Grows the fire slightly.
5. Applies deterministic extinguish damage based on how many agents are actually in position.
6. Removes agents caught inside the fire radius.
7. Ends the game when the fire is out or only one agent remains.

## Notes

- State is kept in memory, so simulations reset when the backend restarts.
- The backend asks models for structured JSON decisions and short radio-style chat lines.
- If the Hugging Face router starts returning `402 Payment Required`, the app switches to local fallback behavior until models become available again.
- The Hugging Face Space deploys from the root `app/` package via the root `Dockerfile`.
- The UI is designed around visible cooperation, not just survival.
- Old lava/volcano docs are intentionally replaced by the fire/water scenario.

