"use client"

import { useEffect, useRef, useState } from "react"
import LoadingScreen from "../components/LoadingScreen"
import MapCanvas from "../components/MapCanvas"
import ChatFeed from "../components/ChatFeed"
import ModelSelector from "../components/ModelSelector"
import { startSimulation, placeVolcano } from "../lib/api"
import { createSimulationSocket } from "../lib/websocket"

type AppState = "loading" | "selecting" | "placing" | "running" | "gameover"

export default function Page() {
  const [appState, setAppState] = useState<AppState>("loading")
  const [models, setModels] = useState<string[]>([])
  const [simState, setSimState] = useState<any>(null)
  const [chatMessages, setChatMessages] = useState<any[]>([])
  const [winnerLabel, setWinnerLabel] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [mapSize, setMapSize] = useState({ width: 1200, height: 800 })
  const wsRef = useRef<WebSocket | null>(null)
  const mapDivRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = mapDivRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setMapSize({ width, height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [appState])

  async function handleStart() {
    if (models.length < 2) return
    setLoading(true)
    try {
      const data = await startSimulation(models)
      setSimState(data.state)
      setWinnerLabel(null)
      setChatMessages([])
      setAppState("placing")
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleMapClick(x: number, y: number) {
    if (appState !== "placing" || !simState) return
    try {
      const data = await placeVolcano(simState.simulation_id, x, y)
      setSimState(data)
      setAppState("running")
      
      const ws = createSimulationSocket(
        simState.simulation_id,
        (msg) => {
          if (msg.type === "finished") {
            if (msg.state) {
              setSimState(msg.state)
              setWinnerLabel(msg.state.winner_model || null)
            }
            setAppState("gameover")
            return
          }
          if (msg.state) setSimState(msg.state)
          if (msg.events) {
            const newMsgs = msg.events.map((e: any) => {
                if (e.type === 'message') return { agent_id: e.model, text: e.content, type: 'message' }
                if (e.type === 'death') return { agent_id: e.model, text: '', type: 'death' }
                if (e.type === 'alliance_proposal') return { agent_id: e.from_model, text: '', type: 'alliance_proposal', to_model: e.to_model }
                if (e.type === 'alliance_accept') return { agent_id: e.model_a, text: '', type: 'alliance_accept', to_model: e.model_b }
                if (e.type === 'alliance_reject') return { agent_id: e.from_model, text: '', type: 'alliance_reject', to_model: e.to_model }
                return null
            }).filter(Boolean)
            setChatMessages(prev => [...prev, ...newMsgs])
          }
          if (msg.chat) {
            const chatMsgs = msg.chat.map((entry: any) => ({
              agent_id: entry.agent_id,
              text: entry.message,
              type: 'message',
            }))
            setChatMessages(prev => [...prev, ...chatMsgs])
          }
          if (msg.state?.status === "finished") {
            setWinnerLabel(msg.state.winner_model || null)
            setAppState("gameover")
          }
        },
        () => setAppState("gameover")
      )
      wsRef.current = ws
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-[#0a0a0a]">
      {appState === "loading" && <LoadingScreen onReady={() => setAppState("selecting")} />}

      {/* Map Area */}
      <div ref={mapDivRef} className="flex-[7] h-full relative">
        <MapCanvas
          agents={simState?.agents ?? []}
          fire={simState?.fire ?? null}
          waterSources={simState?.water_sources ?? []}
          waitingForScenario={appState === "placing"}
          gameOver={appState === "gameover"}
          winnerLabel={winnerLabel}
          mapSize={mapSize}
          onMapClick={handleMapClick}
        />
      </div>

      {/* Sidebar */}
      <aside className="flex-[3] h-full border-l border-white/5 flex flex-col bg-[#111] z-20">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-white tracking-tighter">RUSHH <span className="text-red-500">AGENT</span> RUSHHH !!</h1>
          <p className="text-[10px] text-white/30 uppercase tracking-[0.3em] mt-1">Survival Intelligence Test</p>
        </div>

        <div className="flex-1 flex flex-col min-h-0">
          {appState === "selecting" ? (
            <ModelSelector 
              models={models} 
              onAdd={id => setModels(p => [...p, id])}
              onRemove={id => setModels(p => p.filter(m => m !== id))}
            />
          ) : (
            <ChatFeed messages={chatMessages} />
          )}
        </div>

        <div className="p-6 border-t border-white/5">
          {appState === "selecting" && (
            <button
              onClick={handleStart}
              disabled={models.length < 2 || loading}
              className="w-full bg-white text-black font-mono text-xs font-bold py-4 rounded-xl hover:bg-white/90 disabled:opacity-20 transition-all uppercase tracking-widest"
            >
              {loading ? "Initializing..." : "Start Simulation"}
            </button>
          )}
          {appState === "placing" && (
            <div className="text-center py-4 bg-red-500/10 border border-red-500/20 rounded-xl">
              <span className="text-red-500 font-mono text-[10px] uppercase tracking-widest animate-pulse">
                Click on the map to ignite the fire
              </span>
            </div>
          )}
          {(appState === "running" || appState === "gameover") && (
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-white/5 text-white/50 font-mono text-[10px] py-3 rounded-lg hover:bg-white/10 transition-all uppercase tracking-widest"
            >
              Reset Arena
            </button>
          )}
        </div>
      </aside>
    </main>
  )
}
