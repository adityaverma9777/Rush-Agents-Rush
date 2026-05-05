"use client"

import { useState, useEffect } from "react"
import { getAvailableModels } from "../lib/api"

interface Model {
  id: string
  name: string
  backend?: string
  tag?: string
}

export default function ModelSelector({
  models,
  onAdd,
  onRemove,
}: {
  models: string[]
  onAdd: (id: string) => void
  onRemove: (id: string) => void
}) {
  const [allModels, setAllModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)
  const full = models.length >= 6

  useEffect(() => {
    async function fetchModels() {
      try {
        const data = await getAvailableModels()
        
        // Combine Groq and HF Spaces models
        const combined: Model[] = [
          ...(data.groq_models || []).map((m: any) => ({
            id: m.id,
            name: m.name,
            backend: "groq",
            tag: "groq"
          })),
          ...(data.hf_spaces_models || []).map((m: any) => ({
            id: m.id,
            name: m.name,
            backend: "hf",
            tag: "hf-spaces"
          }))
        ]
        setAllModels(combined)
      } catch (err) {
        console.error("Failed to fetch models:", err)
        // Fallback to default Groq models
        setAllModels([
          { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B", backend: "groq", tag: "groq" },
          { id: "llama-3.1-70b-versatile", name: "Llama 3.1 70B", backend: "groq", tag: "groq" },
          { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B", backend: "groq", tag: "groq" },
          { id: "gemma-7b-it", name: "Gemma 7B", backend: "groq", tag: "groq" },
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchModels()
  }, [])

  if (loading) {
    return (
      <div className="px-4 py-6 space-y-6">
        <div className="text-center text-white/40 font-mono text-xs">
          Loading models...
        </div>
      </div>
    )
  }

  // Group models by backend
  const groqModels = allModels.filter(m => m.backend === "groq")
  const hfModels = allModels.filter(m => m.backend === "hf")

  return (
    <div className="px-4 py-6 space-y-6">
      <div>
        <h3 className="text-[10px] font-mono text-white/30 uppercase tracking-[0.2em] mb-4">
          Select Survivors ({models.length}/6)
        </h3>
        <div className="space-y-4">
          {/* Groq Models */}
          {groqModels.length > 0 && (
            <div>
              <h4 className="text-[8px] font-mono text-white/40 uppercase tracking-[0.15em] mb-2">Groq API</h4>
              <div className="grid grid-cols-1 gap-1.5">
                {groqModels.map((m) => {
                  const isSelected = models.includes(m.id)
                  return (
                    <button
                      key={m.id}
                      onClick={() => isSelected ? onRemove(m.id) : onAdd(m.id)}
                      disabled={full && !isSelected}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg border transition-all duration-200 ${
                        isSelected 
                          ? 'bg-blue-500/10 border-blue-500/30' 
                          : 'border-transparent hover:bg-white/5 opacity-60 hover:opacity-100'
                      } ${full && !isSelected ? 'cursor-not-allowed opacity-20' : ''}`}
                    >
                      <span className="font-mono text-xs text-white/90">{m.name}</span>
                      <span className="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
                        Groq
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* HF Spaces Models */}
          {hfModels.length > 0 && (
            <div>
              <h4 className="text-[8px] font-mono text-white/40 uppercase tracking-[0.15em] mb-2">HuggingFace Spaces</h4>
              <div className="grid grid-cols-1 gap-1.5">
                {hfModels.map((m) => {
                  const isSelected = models.includes(m.id)
                  return (
                    <button
                      key={m.id}
                      onClick={() => isSelected ? onRemove(m.id) : onAdd(m.id)}
                      disabled={full && !isSelected}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg border transition-all duration-200 ${
                        isSelected 
                          ? 'bg-purple-500/10 border-purple-500/30' 
                          : 'border-transparent hover:bg-white/5 opacity-60 hover:opacity-100'
                      } ${full && !isSelected ? 'cursor-not-allowed opacity-20' : ''}`}
                    >
                      <span className="font-mono text-xs text-white/90">{m.name}</span>
                      <span className="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
                        HF
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
      
      {models.length > 0 && (
        <div className="pt-4 border-t border-white/5">
          <div className="flex flex-wrap gap-2">
            {models.map(id => {
              const model = allModels.find(m => m.id === id)
              return (
                <div key={id} className="flex items-center gap-2 bg-white/5 px-2 py-1 rounded border border-white/10">
                  <span className="font-mono text-[10px] text-white/50">
                    {model?.name || id}
                  </span>
                  <button onClick={() => onRemove(id)} className="text-white/20 hover:text-white">✕</button>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
