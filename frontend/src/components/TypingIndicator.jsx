import { useEffect, useState } from 'react'

const phases = ['Thinking...', 'Planning...', 'Calling AWS...', 'Retrieving Company Knowledge...', 'Executing Tool...']

export function TypingIndicator() {
  const [phaseIndex, setPhaseIndex] = useState(0)

  useEffect(() => {
    const interval = window.setInterval(() => {
      setPhaseIndex((value) => (value + 1) % phases.length)
    }, 1200)

    return () => window.clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-slate-800/80 bg-slate-900/70 px-4 py-3 text-sm text-slate-300 shadow-sm">
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:-0.2s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400 [animation-delay:-0.1s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-400" />
      </div>
      <span className="font-medium text-slate-100">{phases[phaseIndex]}</span>
    </div>
  )
}
