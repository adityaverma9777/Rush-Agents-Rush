"use client"

import { useState, useEffect } from "react"
import { getAvailableModels } from "../lib/api"

interface Model {
  id: string
  name: string
  description?: string
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
        
        // Use unified model list (no backend categorization)
        // Support multiple backend response formats (new unified `models` or legacy grouped keys)
        if (data.models && Array.isArray(data.models)) {
          setAllModels(data.models)
        } else {
          const groq = data.groq_models || data.groqModels || data.groq || []
          const hf = data.hf_spaces_models || data.hf_spaces || data.hf_models || data.hfModels || []
          const merged: Model[] = []
          if (Array.isArray(groq)) {
            for (const g of groq) merged.push({ id: g.id, name: g.name || g.id, description: g.description || g.backend || '' })
          }
          if (Array.isArray(hf)) {
            for (const h of hf) merged.push({ id: h.id, name: h.name || h.id, description: h.description || h.space_url || '' })
          }
          if (merged.length > 0) setAllModels(merged)
          else setAllModels([])
        }
      } catch (err) {
        console.error("Failed to fetch models:", err)
        // Fallback to default models
        setAllModels([
          { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B", description: "High-performance model" },
          { id: "llama2-70b-4096", name: "Llama 2 70B", description: "Large instruction-tuned model" },
          { id: "mistralai/Mistral-7B-Instruct-v0.2", name: "Mistral 7B", description: "Fast 7B model" },
          { id: "NousResearch/Nous-Hermes-2-Mistral-7B-DPO", name: "Nous Hermes 2", description: "High-quality model" },
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

  return (
    <div className="px-4 py-6 space-y-6">
      <div>
        <h3 className="text-[10px] font-mono text-white/30 uppercase tracking-[0.2em] mb-4">
          Select Survivors ({models.length}/6)
        </h3>
        <div className="space-y-1.5">
          {allModels.map((m) => {
            const isSelected = models.includes(m.id)
            return (
              <button
                key={m.id}
                onClick={() => isSelected ? onRemove(m.id) : onAdd(m.id)}
                disabled={full && !isSelected}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border transition-all duration-200 ${
                  isSelected 
                    ? 'bg-white/10 border-white/20' 
                    : 'border-transparent hover:bg-white/5 opacity-60 hover:opacity-100'
                } ${full && !isSelected ? 'cursor-not-allowed opacity-20' : ''}`}
                title={m.description}
              >
                <span className="font-mono text-xs text-white/90 text-left flex-1">{m.name}</span>
                <span className={`text-[8px] font-mono ml-2 px-2 py-1 rounded ${isSelected ? 'bg-white/20 text-white' : 'text-white/30'}`}>
                  {isSelected ? "✓" : "○"}
                </span>
              </button>
            )
          })}
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
                    {model?.name || id.split("/").pop()}
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

