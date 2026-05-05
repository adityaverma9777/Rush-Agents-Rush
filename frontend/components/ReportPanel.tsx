"use client"

import React from "react"

export default function ReportPanel({ report, onClose }: { report: any, onClose: () => void }) {
  if (!report) return null

  const models = report.models || []

  return (
    <div className="absolute inset-0 z-50 flex items-start justify-center p-6 pointer-events-auto">
      <div className="w-full max-w-4xl bg-black/95 border border-white/10 rounded-xl p-6 text-white shadow-2xl overflow-auto max-h-[90vh]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Simulation Report</h2>
          <button onClick={onClose} className="px-3 py-1 bg-white/5 rounded">Close</button>
        </div>

        <div className="mb-4 text-sm text-white/70">Summary metrics for this match.</div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-900 p-4 rounded">
            <div className="text-xs text-white/60">Rounds</div>
            <div className="text-xl font-mono">{report.rounds}</div>
          </div>
          <div className="bg-gray-900 p-4 rounded">
            <div className="text-xs text-white/60">Models</div>
            <div className="text-xl font-mono">{models.length}</div>
          </div>
        </div>

        <div className="space-y-4">
          {models.map((m: any) => (
            <div key={m.id} className="bg-gray-900 p-4 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold">{m.display_name || m.id}</div>
                  <div className="text-xs text-white/60">{m.id}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-white/60">Decisions</div>
                  <div className="font-mono text-lg">{m.decisions}</div>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-4 gap-3 text-xs text-white/60">
                <div>Distance travelled: <div className="text-white font-mono">{m.distance.toFixed(0)} px</div></div>
                <div>Water pickups: <div className="text-white font-mono">{m.water_picks}</div></div>
                <div>Extinguish score: <div className="text-white font-mono">{m.extinguish_score.toFixed(1)}</div></div>
                <div>Logical moves: <div className="text-white font-mono">{Math.round(m.logical_pct)}%</div></div>
              </div>

              <div className="mt-3 text-xs">
                <div className="text-white/70 mb-1">Top messages</div>
                <div className="grid grid-cols-2 gap-2">
                  {(m.top_messages || []).map((msg: string, idx: number) => (
                    <div key={idx} className="text-[12px] font-mono text-white/80">- {msg}</div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}
