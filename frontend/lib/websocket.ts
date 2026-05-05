const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "")

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
      // DEBUG: surface incoming websocket payload for troubleshooting
      try { console.debug("WS_RECV", msg) } catch (e) {}
      onMessage(msg)
    } catch (e) {
      console.error("Failed to parse WebSocket message:", e)
    }
  }
  
  ws.onerror = (error) => {
    console.error("WebSocket error:", error)
    onError()
  }
  
  ws.onclose = (event) => {
    console.log("WebSocket closed", { code: event.code, reason: event.reason })
    onError()
  }
  
  return ws
}
