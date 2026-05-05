# RUSH AGENTS - Quick Start Guide

## 📋 Overview

**RUSH AGENTS** is an AI model battle arena where models compete for survival by escaping lava and forming strategic alliances.

- **Intelligence Test**: See which AI model survives the longest
- **Alliance System**: Models can propose partnerships (but proposing signals weakness)
- **Rules-Based**: No personalities—all models play by identical rules
- **Groq API**: Fast, parallel decision-making for all models
- **Real-time**: WebSocket streaming, 3-second ticks

---

## 🚀 Quick Start (Local Development)

### Prerequisites
✅ Already installed:
- Python 3.10+
- Node.js 18+
- Groq API Key (in `backend/.env`)

### Start Backend

```bash
cd backend

# Verify .env has GROQ_API_KEY
cat .env

# Run the server
python -m uvicorn app.main:app --reload
```

Server runs on: **http://localhost:8000**

### Start Frontend (New Terminal)

```bash
cd frontend

# Run dev server
npm run dev
```

Frontend runs on: **http://localhost:3000**

### Play

1. Open http://localhost:3000
2. Wait for "Ready for chaos"
3. Select 2-6 models from the dropdown
4. Click "Start Simulation"
5. Click map to place volcano
6. Watch the battle unfold!

---

## 📚 What's Available

### Models
**Groq Models (Free Tier)**:
- `llama-3.1-8b-instant` — 8B fast
- `llama-3.1-70b-versatile` — 70B smart
- `mixtral-8x7b-32768` — 8x7B expert
- `gemma-7b-it` — 7B instruction-tuned

**HuggingFace Spaces** (Can add more):
- Falcon-7B
- Llama-2-7B
- Mistral-7B
- Zephyr-7B
- OpenHermes-7B

---

## 🎮 Game Rules

### Each Model Sees:
- All other models' positions (x, y)
- Volcano position & radius
- Map bounds (1200x800)
- Distance to lava edge
- Alliance status (who's allied with whom)

### Each Tick (3 seconds):

**1. Groq Decision Call** (Parallel for all models)
   - "run" → Sprint away from lava
   - "propose_alliance" → Ask another model to team up

**2. Alliance Processing**
   - If A proposes to B, B gets asked immediately
   - If B accepts → Both merge at same position
   - If B rejects → A keeps running, B keeps running

**3. Movement**
   - Models move based on decisions
   - Position clamped to map bounds

**4. Lava Expands**
   - Radius grows by 120 pixels

**5. Deaths**
   - Models in lava radius die
   - EXCEPT if they're stacked with an alive ally

**6. Win Check**
   - ≤1 model alive → Game Over

### Strategic Cost of Alliances
- **Proposing** = signaling weakness
- **First to propose** = lose strategic leverage
- **Benefit** = survival through numbers

---

## 🔑 Environment Variables

### Backend (.env)
```
GROQ_API_KEY=<your key here>           # REQUIRED
HUGGINGFACE_API_TOKEN=                 # Optional
ALLOWED_ORIGINS=http://localhost:3000
ENV=development
```

### Frontend (.env.local)
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## 📡 API Endpoints

```
GET  /wake                    → Health check + status
GET  /available-models        → List of all available models
POST /start-simulation         → Create new simulation
POST /place-volcano            → Place volcano, start ticking
GET  /ws/{simulation_id}       → WebSocket stream
```

---

## 🧠 How Groq Decision-Making Works

### Per Model, Per Tick:
1. **Build state summary**
   - Current standings (distance from lava)
   - All agents' positions
   - Volcano position & radius

2. **Send to Groq Llama 3.1 8B**
   ```json
   {
     "system": "You are [ModelName]. Make a strategic decision...",
     "user": "[Game state]"
   }
   ```

3. **Get response**
   ```json
   {
     "action": "run|propose_alliance",
     "alliance_target": "ModelName or null",
     "reasoning": "..."
   }
   ```

4. **Execute action**

All models queried in parallel (async) = fast ticks

---

## 🎨 Frontend Features

### Map Canvas
- **White circles** = Individual models
- **Yellow glowing circles** = Stacked alliances (2+ models)
- **Orange/red glow** = Lava expanding
- **Gray skull** = Dead models
- **Yellow 🤝** = Alliance indicator on label

### Sidebar
- **Model Selector** = Pick 2-6 models (groups by Groq/HF)
- **Chat Feed** = Events (alliances, deaths, decisions)
- **Status** = Current round, agents alive

---

## 🔧 Troubleshooting

### "Failed to fetch models"
- Check backend is running: `python -m uvicorn app.main:app --reload`
- Check port 8000 is available

### "Groq API error"
- Verify `GROQ_API_KEY` in `backend/.env`
- Check Groq dashboard: https://console.groq.com

### WebSocket connection fails
- Frontend tries `ws://localhost:8000` (port 8000)
- Make sure backend is running

### No models showing up
- Check `/available-models` returns data: `curl http://localhost:8000/available-models`

---

## 📝 Key Files

```
backend/
  app/
    main.py            → FastAPI server
    simulation.py      → Game engine logic
    models.py          → Pydantic schemas
    groq_client.py     → Groq API integration
    hf_spaces.py       → HF model discovery
    movement.py        → Physics/movement
  .env                 → API keys (REQUIRED)
  requirements.txt     → Python dependencies

frontend/
  app/
    page.tsx           → Main app component
  components/
    MapCanvas.tsx      → 2D map rendering
    ModelSelector.tsx  → Model selection UI
    ChatFeed.tsx       → Event stream display
  lib/
    api.ts             → Backend API calls
```

---

## 🚢 Deployment

### Backend (Railway, Heroku, etc.)
```bash
# Set env vars
GROQ_API_KEY=...
ALLOWED_ORIGINS=https://yourdomain.com

# Deploy
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Frontend (Vercel, Netlify)
```bash
npm run build
# Deploy the .next folder
```

---

## 📖 Learn More

- Groq API docs: https://console.groq.com/docs
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/docs
- WebSocket: https://mdn.io/WebSocket

---

## 💡 Ideas for Experimentation

1. **Add new models** — Edit `hf_spaces.py` KNOWN_SPACES_MODELS
2. **Change game rules** — Edit `simulation.py` tick logic
3. **New scenarios** — Add earthquake, meteor, etc. in `simulation.py`
4. **Leaderboard** — Track best survival times across sessions
5. **Replay system** — Save/load simulation events
6. **Model attack mechanic** — Add "push" action to shove others toward lava

---

**Ready to battle?** Open http://localhost:3000! 🌋
