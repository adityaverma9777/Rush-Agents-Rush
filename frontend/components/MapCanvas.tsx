"use client"

import { useEffect, useRef, useState } from "react"

type Agent = {
  model_name: string
  x: number
  y: number
  alive: boolean
  water_collected: boolean
  is_leader: boolean
  mode: "solo" | "coalition"
  status: "searching" | "collecting_water" | "extinguishing_fire" | "escaping" | "idle"
}

type Fire = {
  x: number
  y: number
  radius: number
  intensity: number
}

type WaterSource = {
  id: string
  x: number
  y: number
  water_amount: number
}

const BACKEND_W = 1200
const BACKEND_H = 800

function getAgentColor(name: string) {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return `hsl(${hash % 360}, 70%, 60%)`
}

function getStatusColor(status: string) {
  switch (status) {
    case "searching": return "#3b82f6"  // blue
    case "collecting_water": return "#06b6d4"  // cyan
    case "extinguishing_fire": return "#ef4444"  // red
    case "escaping": return "#f59e0b"  // amber
    default: return "#6b7280"  // gray
  }
}

export default function MapCanvas({
  agents,
  fire,
  waterSources,
  waitingForScenario,
  gameOver,
  winnerLabel,
  mapSize,
  onMapClick,
}: {
  agents: Agent[]
  fire: Fire | null
  waterSources: WaterSource[]
  waitingForScenario: boolean
  gameOver: boolean
  winnerLabel?: string | null
  mapSize: { width: number; height: number }
  onMapClick?: (x: number, y: number) => void
}) {
  const gridSize = 40
  const sx = (bx: number) => (bx / BACKEND_W) * mapSize.width
  const sy = (by: number) => (by / BACKEND_H) * mapSize.height
  const leader = agents.find(a => a.alive && a.is_leader)
  const coalitionAgents = agents.filter(a => a.alive && a.mode === "coalition" && !a.is_leader)

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!waitingForScenario || !onMapClick) return
    const rect = e.currentTarget.getBoundingClientRect()
    const backendX = Math.round(((e.clientX - rect.left) / mapSize.width) * BACKEND_W)
    const backendY = Math.round(((e.clientY - rect.top) / mapSize.height) * BACKEND_H)
    onMapClick(backendX, backendY)
  }

  return (
    <div
      className="relative w-full h-full bg-[#0a0a0a] overflow-hidden"
      style={{ cursor: waitingForScenario ? "crosshair" : "default" }}
      onClick={handleClick}
    >
      {/* Grid */}
      <div className="absolute inset-0 opacity-10 pointer-events-none" 
           style={{ backgroundImage: `linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)`, backgroundSize: `${gridSize}px ${gridSize}px` }} />

      {/* Fire */}
      {fire && (
        <div
          className="absolute rounded-full transition-all duration-500 ease-linear"
          style={{
            left: sx(fire.x),
            top: sy(fire.y),
            width: sx(fire.radius) * 2,
            height: sy(fire.radius) * 2,
            transform: "translate(-50%, -50%)",
            background: `radial-gradient(circle, #ff4500 0%, rgba(255, 69, 0, ${Math.min(fire.intensity / 100, 1)}) 60%, transparent 100%)`,
            boxShadow: `0 0 ${30 + fire.intensity / 2}px rgba(255, 69, 0, ${fire.intensity / 100})`,
          }}
        >
          <div className="absolute inset-0 rounded-full animate-pulse" style={{ backgroundColor: `rgba(255, 69, 0, ${fire.intensity / 200})` }} />
        </div>
      )}

      {/* Water Sources */}
      {waterSources.map((water) => (
        <div
          key={water.id}
          className="absolute"
          style={{
            left: sx(water.x),
            top: sy(water.y),
            transform: "translate(-50%, -50%)",
          }}
        >
          <div className="relative">
            <div className="w-6 h-6 rounded-full border-2 border-cyan-400 bg-cyan-500/20 flex items-center justify-center animate-pulse">
              <span className="text-[10px]">💧</span>
            </div>
          </div>
        </div>
      ))}

      {/* Coalition Links */}
      {leader && coalitionAgents.length > 0 && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {coalitionAgents.map((agent) => (
            <line
              key={`${leader.model_name}-${agent.model_name}`}
              x1={sx(leader.x)}
              y1={sy(leader.y)}
              x2={sx(agent.x)}
              y2={sy(agent.y)}
              stroke="rgba(250, 204, 21, 0.6)"
              strokeWidth={2}
              strokeDasharray="6 6"
            />
          ))}
        </svg>
      )}

      {/* Agents */}
      {agents.map((agent) => {
        const color = getAgentColor(agent.model_name)
        const isDead = !agent.alive
        const statusColor = getStatusColor(agent.status)
        const nodeSize = agent.water_collected ? 10 : 6
        
        return (
          <div
            key={agent.model_name}
            className={`absolute transition-all duration-200 ease-in-out flex flex-col items-center ${isDead ? 'opacity-30 grayscale scale-75' : ''}`}
            style={{
              left: sx(agent.x),
              top: sy(agent.y),
              transform: "translate(-50%, -50%)",
            }}
          >
            {!isDead && (
              <div className="mb-2 px-2 py-1 bg-[#111] border border-white/10 rounded-md shadow-2xl backdrop-blur-md max-w-[140px]">
                <span className="font-mono text-[8px] text-white break-words">
                  {agent.model_name}
                  {agent.is_leader && <span className="text-yellow-400 ml-1">👑</span>}
                  {agent.water_collected && <span className="text-cyan-400 ml-1">💧</span>}
                </span>
                <div className="text-[7px] text-white/60 mt-0.5">{agent.status}</div>
              </div>
            )}
            
            <div className="relative">
              <div 
                className="absolute rounded-full animate-pulse"
                style={{
                  width: nodeSize * 4,
                  height: nodeSize * 4,
                  left: -nodeSize,
                  top: -nodeSize,
                  borderColor: statusColor,
                  borderWidth: "2px",
                  borderStyle: "solid",
                }}
              />
              <div 
                className="rounded-full border-2 relative"
                style={{
                  width: nodeSize * 2,
                  height: nodeSize * 2,
                  backgroundColor: agent.water_collected ? "#06b6d4" : color,
                  borderColor: agent.is_leader ? "#ffff00" : color,
                  boxShadow: isDead ? "none" : `0 0 15px ${agent.water_collected ? "rgba(6, 182, 212, 0.4)" : "rgba(255,255,255,0.2)"}`,
                }}
              >
                {isDead && (
                  <div className="absolute inset-0 flex items-center justify-center text-[10px]">💀</div>
                )}
              </div>
            </div>
          </div>
        )
      })}

      {/* Fire Intensity Meter */}
      {fire && (
        <div className="absolute top-4 left-4 bg-black/70 border border-white/20 rounded-lg p-3 backdrop-blur-md">
          <div className="text-white/80 font-mono text-[10px] mb-2">Fire Intensity</div>
          <div className="w-32 h-3 bg-white/10 rounded-full overflow-hidden border border-white/20">
            <div
              className="h-full bg-gradient-to-r from-orange-500 to-red-600 transition-all duration-300"
              style={{ width: `${Math.min(fire.intensity, 100)}%` }}
            />
          </div>
          <div className="text-white/60 font-mono text-[9px] mt-1">{fire.intensity.toFixed(0)}%</div>
        </div>
      )}

      {/* Coalition Panel */}
      <div className="absolute top-4 right-4 bg-black/70 border border-white/20 rounded-lg p-3 backdrop-blur-md max-w-xs">
        <div className="text-white/80 font-mono text-[10px] mb-2">🎯 Coalition Status</div>
        <div className="space-y-1">
          {agents.filter(a => a.alive && a.mode === "coalition").map(agent => (
            <div key={agent.model_name} className="text-white/60 font-mono text-[9px]">
              {agent.is_leader ? "👑 " : "  "}{agent.model_name.split("/")[0]}
              {agent.water_collected && " 💧"}
            </div>
          ))}
          {agents.filter(a => a.alive && a.mode === "solo").length > 0 && (
            <div className="text-amber-400/80 font-mono text-[9px] mt-2">Lone Wolves:</div>
          )}
          {agents.filter(a => a.alive && a.mode === "solo").map(agent => (
            <div key={agent.model_name} className="text-amber-400/60 font-mono text-[9px]">
              🐺 {agent.model_name.split("/")[0]}
              {agent.water_collected && " 💧"}
            </div>
          ))}
        </div>
      </div>

      {/* Instructions */}
      {waitingForScenario && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-black/70 backdrop-blur-md border border-white/10 px-8 py-6 rounded-xl text-center">
          <span className="text-white font-mono text-sm uppercase tracking-widest">
            Click to place the fire and begin
          </span>
        </div>
      )}

      {/* Game Over */}
      {gameOver && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 bg-black/50">
          <div className="bg-black/90 backdrop-blur-xl border-2 border-yellow-400/50 p-8 rounded-2xl text-center max-w-md">
            <h2 className="text-5xl font-bold text-white font-mono tracking-tighter mb-4">🏁 GAME OVER</h2>
            <p className="text-yellow-400 font-mono text-sm uppercase tracking-widest mb-3">
              {fire && fire.intensity <= 0 ? "🔥 FIRE EXTINGUISHED!" : "❌ ALL BURNED"}
            </p>
            <p className="text-white/80 font-mono text-xs break-words">
              {winnerLabel || "The flames consumed the arena"}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
