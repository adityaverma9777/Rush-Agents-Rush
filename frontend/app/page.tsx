"use client"

import { useEffect, useRef, useState } from "react"
import LoadingScreen from "../components/LoadingScreen"
import MapCanvas from "../components/MapCanvas"
import ChatFeed from "../components/ChatFeed"
import ModelSelector from "../components/ModelSelector"
import { startSimulation, placeVolcano } from "../lib/api"
import { createSimulationSocket } from "../lib/websocket"
import ReportPanel from "../components/ReportPanel"

type AppState = "loading" | "selecting" | "placing" | "running" | "gameover"

export default function Page() {
  function buildReport(history: any[]) {
    if (!history || history.length === 0) return null
    const rounds = history.length
    const last = history[history.length - 1]
    const lastState = last.state || last
    const models = (lastState.agents || []).map((a: any) => ({ id: a.model_name, display_name: a.display_name || a.model_name }))

    const per = models.map((m: any) => {
      const positions = history.map(h => {
        const state = h.state || h
        const a = (state.agents || []).find((x: any) => x.model_name === m.id)
        return a ? { x: a.x, y: a.y, water: a.water_collected, status: a.status, extinguish_score: a.extinguish_score || 0, last_message: a.last_message } : null
      }).filter(Boolean)

      let distance = 0
      for (let i = 1; i < positions.length; i++) {
        const p0 = positions[i-1]
        const p1 = positions[i]
        const dx = p1.x - p0.x
        const dy = p1.y - p0.y
        distance += Math.sqrt(dx*dx + dy*dy)
      }

      let water_picks = 0
      let logical_moves = 0
      let logical_checks = 0
      const messages: Record<string, number> = {}

      // Count events (decisions/messages, water pickups) across ticks
      for (let i = 0; i < history.length; i++) {
        const tick = history[i]
        const events = tick.events || []
        for (const ev of events) {
          if (ev.type === 'message' && ev.model === m.id) {
            messages[ev.content] = (messages[ev.content] || 0) + 1
          }
          if (ev.type === 'water_collected' && ev.model === m.id) {
            water_picks++
          }
        }

        // logical move checks based on consecutive positions
        if (i > 0) {
          const prevState = history[i-1].state || history[i-1]
          const curState = history[i].state || history[i]
          const prevA = (prevState.agents || []).find((x: any) => x.model_name === m.id)
          const curA = (curState.agents || []).find((x: any) => x.model_name === m.id)
          if (prevA && curA) {
            if (curA.status === 'searching') {
              const ws = curState.water_sources || []
              if (ws.length > 0) {
                const distPrev = Math.min(...ws.map((w: any)=> Math.hypot(prevA.x - w.x, prevA.y - w.y)))
                const distCur = Math.min(...ws.map((w: any)=> Math.hypot(curA.x - w.x, curA.y - w.y)))
                logical_checks++
                if (distCur <= distPrev) logical_moves++
              }
            }
          }
        }
      }

      const sortedMessages = Object.entries(messages).sort((a:any,b:any)=>b[1]-a[1]).slice(0,6).map((x:any)=>x[0])

      return {
        id: m.id,
        display_name: m.display_name,
        decisions: positions.length,
        distance,
        water_picks,
        extinguish_score: positions.length>0 ? positions[positions.length-1].extinguish_score||0 : 0,
        logical_pct: logical_checks>0 ? (logical_moves / logical_checks)*100 : 0,
        top_messages: sortedMessages,
      }
    })

    return { rounds, models: per }
  }

  function tickHistoryToTracks(history: any[]) {
    const tracks: Record<string, { x: number; y: number }[]> = {}
    if (!history || history.length === 0) return tracks
    for (const h of history) {
      const state = h.state || h
      for (const a of state.agents || []) {
        if (!tracks[a.model_name]) tracks[a.model_name] = []
        tracks[a.model_name].push({ x: a.x, y: a.y })
      }
    }
    return tracks
  }
  const [appState, setAppState] = useState<AppState>("loading")
  const [models, setModels] = useState<string[]>([])
  const [simState, setSimState] = useState<any>(null)
  const [chatMessages, setChatMessages] = useState<any[]>([])
  const [winnerLabel, setWinnerLabel] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [tickHistory, setTickHistory] = useState<any[]>([])
  const [reportOpen, setReportOpen] = useState(false)
  const [reportData, setReportData] = useState<any | null>(null)
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
        setTickHistory([])
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
            // store the full tick message (state + events) for richer analysis
            setTickHistory(prev => [...prev, msg])
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
            // prepare report
            const report = buildReport([...tickHistory, msg])
            setReportData(report)
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
          tracks={tickHistoryToTracks(tickHistory)}
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
            <div className="space-y-2">
              {appState === 'gameover' && reportData && (
                <button onClick={() => setReportOpen(true)} className="w-full bg-white text-black font-mono text-xs font-bold py-3 rounded-xl">View Report</button>
              )}
              <button
                onClick={() => window.location.reload()}
                className="w-full bg-white/5 text-white/50 font-mono text-[10px] py-3 rounded-lg hover:bg-white/10 transition-all uppercase tracking-widest"
              >
                Reset Arena
              </button>
            </div>
          )}
        </div>
      </aside>
      {reportOpen && reportData && (
        <ReportPanel report={reportData} onClose={() => setReportOpen(false)} />
      )}
    </main>
  )
}
