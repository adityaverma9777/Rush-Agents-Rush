"use client"

import { useEffect, useRef } from "react"

type ChatMessage = {
  agent_id: string
  text: string
  type?: 'message' | 'death' | 'alliance_proposal' | 'alliance_accept' | 'alliance_reject' | 'leadership_vote' | 'leader_elected' | 'water_collected' | 'fire_extinguished'
  to_model?: string
  from_model?: string
  candidates?: string[]
}

export default function ChatFeed({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function getAgentName(id: string) {
    return id.split("/").at(-1)?.split("-")[0].toUpperCase() || id
  }

  function getAgentColor(name: string) {
    let hash = 0
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    return `hsl(${hash % 360}, 70%, 60%)`
  }

  return (
    <div className="flex-1 overflow-y-auto py-4 space-y-3 min-h-0 custom-scrollbar">
      {messages.map((msg, i) => {
        const color = getAgentColor(msg.agent_id)
        
        if (msg.type === 'death') {
          return (
            <div key={i} className="mx-4 p-2 bg-red-500/10 border-l-2 border-red-500 animate-in slide-in-from-left duration-300">
              <span className="font-mono text-[10px] text-red-500 uppercase font-bold tracking-widest">
                💀 {getAgentName(msg.agent_id)} was consumed by the fire
              </span>
            </div>
          )
        }

        if (msg.type === 'alliance_proposal') {
            return (
              <div key={i} className="mx-4 p-2 bg-yellow-500/10 border-l-2 border-yellow-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-yellow-500 uppercase font-bold tracking-widest">
                  🤝 {getAgentName(msg.agent_id)} proposed an alliance to {msg.to_model ? getAgentName(msg.to_model) : 'someone'}
                </span>
              </div>
            )
          }

        if (msg.type === 'alliance_accept') {
            return (
              <div key={i} className="mx-4 p-2 bg-emerald-500/10 border-l-2 border-emerald-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-emerald-400 uppercase font-bold tracking-widest">
                  ✅ {getAgentName(msg.agent_id)} accepted the alliance{msg.to_model ? ` with ${getAgentName(msg.to_model)}` : ''}
                </span>
              </div>
            )
          }

        if (msg.type === 'alliance_reject') {
            return (
              <div key={i} className="mx-4 p-2 bg-orange-500/10 border-l-2 border-orange-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-orange-400 uppercase font-bold tracking-widest">
                  ❌ {getAgentName(msg.agent_id)} rejected the alliance{msg.to_model ? ` from ${getAgentName(msg.to_model)}` : ''}
                </span>
              </div>
            )
          }

        if (msg.type === 'leadership_vote') {
            return (
              <div key={i} className="mx-4 p-2 bg-purple-500/10 border-l-2 border-purple-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-purple-400 uppercase font-bold tracking-widest">
                  🗳️ {getAgentName(msg.agent_id)} voted for {msg.candidates ? getAgentName(msg.candidates[0]) : 'someone'}
                </span>
              </div>
            )
          }

        if (msg.type === 'leader_elected') {
            return (
              <div key={i} className="mx-4 p-2 bg-yellow-500/10 border-l-2 border-yellow-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-yellow-400 uppercase font-bold tracking-widest">
                  👑 {getAgentName(msg.agent_id)} elected as leader!
                </span>
              </div>
            )
          }

        if (msg.type === 'water_collected') {
            return (
              <div key={i} className="mx-4 p-2 bg-cyan-500/10 border-l-2 border-cyan-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-cyan-400 uppercase font-bold tracking-widest">
                  💧 {getAgentName(msg.agent_id)} collected water!
                </span>
              </div>
            )
          }

        if (msg.type === 'fire_extinguished') {
            return (
              <div key={i} className="mx-4 p-2 bg-green-500/10 border-l-2 border-green-500 animate-in slide-in-from-left duration-300">
                <span className="font-mono text-[10px] text-green-400 uppercase font-bold tracking-widest">
                  🔥 Fire being extinguished! Intensity dropping...
                </span>
              </div>
            )
          }

        return (
          <div key={i} className="px-4 group animate-in fade-in duration-500">
            <div className="flex items-baseline gap-2">
              <span 
                className="font-mono text-[10px] font-bold shrink-0 px-1.5 rounded bg-white/5" 
                style={{ color }}
              >
                {getAgentName(msg.agent_id)}
              </span>
              <span className="font-mono text-[12px] text-white/80 leading-relaxed break-words">
                {msg.text}
              </span>
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
