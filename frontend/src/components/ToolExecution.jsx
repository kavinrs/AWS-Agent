import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function ToolExecution({ steps = [] }) {
  if (!steps.length) return null

  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={`${step.tool}-${index}`} className="rounded-3xl border border-slate-800/80 bg-slate-900/80 p-4 shadow-sm shadow-black/20">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-100">{step.tool || 'Tool execution'}</p>
              <p className="mt-1 text-xs text-slate-500">Step {index + 1}</p>
            </div>
            <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              Complete
            </span>
          </div>

          {step.tool_input && (
            <div className="mt-3 rounded-2xl border border-slate-800/80 bg-slate-950/80 p-3 text-sm text-slate-300">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Input</p>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-300">{JSON.stringify(step.tool_input, null, 2)}</pre>
            </div>
          )}

          {step.observation && (
            <div className="mt-3 rounded-2xl border border-slate-800/80 bg-slate-950/80 p-3 text-sm text-slate-300">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Result</p>
              <div className="mt-2 prose prose-invert prose-sm max-w-none prose-p:my-2 prose-ul:list-disc prose-li:ml-4 prose-code:rounded prose-code:bg-slate-900 prose-code:px-1 prose-code:text-cyan-300">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{step.observation}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
