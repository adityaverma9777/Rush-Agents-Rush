# Rush Agents Rush Frontend

Next.js UI for the fire-suppression simulation.

## What It Shows

- Model selection and simulation start flow
- Map-based agent positions and fire placement
- Water sources, coalition links, and leader markers
- Live event chat with varied team messages
- End-of-game result banner with top performer info

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000.

## Environment Variables

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Main Files

- `app/page.tsx` - app shell and simulation flow
- `components/MapCanvas.tsx` - 2D map rendering and agent visuals
- `components/ChatFeed.tsx` - event/chat panel
- `components/ModelSelector.tsx` - model picker
- `lib/api.ts` - backend requests
- `lib/websocket.ts` - simulation WebSocket client

## Notes

- The frontend expects the backend to be running before placing a fire.
- If the browser shows `Failed to fetch`, verify `http://localhost:8000/wake` first.
- The old volcano terminology has been removed from the current gameplay flow.
