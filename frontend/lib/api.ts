const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "")

function apiUrl(path: string) {
  return `${BACKEND_URL}${path}`
}

export async function wakeBackend() {
  const response = await fetch(apiUrl("/wake"))
  return response.json()
}

export async function getAvailableModels() {
  const response = await fetch(apiUrl("/available-models"))
  return response.json()
}

export async function startSimulation(modelNames: string[]) {
  const response = await fetch(apiUrl("/start-simulation"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_names: modelNames,
      scenario: "fire",
      map_width: 1200,
      map_height: 800,
    }),
  })
  if (!response.ok) throw new Error("Failed to start simulation")
  return response.json()
}

export async function placeVolcano(simulationId: string, x: number, y: number) {
  const response = await fetch(apiUrl("/place-fire"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ simulation_id: simulationId, x, y }),
  })
  if (!response.ok) {
    const details = await response.text()
    throw new Error(`Failed to place fire (${response.status}): ${details}`)
  }
  return response.json()
}

export function createSimulationSocket(
  simulationId: string,
  onMessage: (msg: any) => void,
  onError: () => void
) {
  const wsBase = BACKEND_URL.replace(/^http:/, "ws:").replace(/^https:/, "wss:")
  const wsUrl = `${wsBase}/ws/${simulationId}`
  
  const ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      onMessage(msg)
    } catch (e) {
      console.error("Failed to parse message:", e)
    }
  }
  
  ws.onerror = () => onError()
  ws.onclose = () => onError()
  
  return ws
}
