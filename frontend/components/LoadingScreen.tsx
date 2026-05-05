"use client"

import { useEffect, useState } from "react"
import { wakeBackend } from "../lib/api"

export default function LoadingScreen({ onReady }: { onReady: () => void }) {
  const [status, setStatus] = useState<"waking" | "connecting" | "ready" | "error">("waking")
  const [dots, setDots] = useState("")

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(d => (d.length >= 3 ? "" : d + "."))
    }, 500)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let timeoutId: NodeJS.Timeout
    let isActive = true

    async function poll() {
      try {
        const data = await wakeBackend()
        if (data.warm && data.groq_available) {
          setStatus("ready")
          setTimeout(() => {
            if (isActive) onReady()
          }, 1000)
        } else if (data.warm) {
          setStatus("connecting")
          timeoutId = setTimeout(poll, 2000)
        }
      } catch (err) {
        timeoutId = setTimeout(poll, 2000)
      }
    }

    poll()

    const failTimeout = setTimeout(() => {
      if (status !== "ready") setStatus("error")
    }, 60000)

    return () => {
      isActive = false
      clearTimeout(timeoutId)
      clearTimeout(failTimeout)
    }
  }, [onReady, status])

  return (
    <div className="fixed inset-0 bg-[#0a0a0a] flex flex-col items-center justify-center z-50">
      <div className="relative mb-8">
        <div className="text-6xl animate-bounce">🌋</div>
        <div className="absolute inset-0 bg-red-500/20 blur-3xl rounded-full animate-pulse" />
      </div>
      
      <div className="font-mono text-xs tracking-widest text-white/40 uppercase mb-2">
        {status === "waking" && `Waking up the arena${dots}`}
        {status === "connecting" && `Connecting to Groq${dots}`}
        {status === "ready" && "Ready for chaos"}
        {status === "error" && "Failed to start. Check your connection."}
      </div>

      {status === "error" && (
        <button 
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-white/10 hover:bg-white/20 text-white font-mono text-xs rounded transition-colors"
        >
          Retry
        </button>
      )}

      <div className="w-48 h-1 bg-white/5 rounded-full overflow-hidden mt-4">
        <div className={`h-full bg-red-500 transition-all duration-1000 ${status === "ready" ? "w-full" : "w-1/2 animate-pulse"}`} />
      </div>
    </div>
  )
}
