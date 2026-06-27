export function WelcomeScreen({ onPromptSelect, tools = [], showTools, onToggleTools }) {
  const suggestions = [
    'List my EC2 instances',
    'Create an S3 bucket',
    'Launch a development EC2 server',
    'Create a PostgreSQL database',
    'Show CloudWatch logs',
  ]

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
      <div className="w-full max-w-3xl rounded-[32px] border border-slate-800/80 bg-slate-900/70 p-8 shadow-2xl shadow-black/20 backdrop-blur sm:p-10">
        <div className="flex flex-col items-center text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl border border-slate-800 bg-gradient-to-br from-cyan-500/10 to-slate-900 text-cyan-400 shadow-lg shadow-cyan-950/30">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="stroke-current">
              <path d="M4 6h16M4 12h10M4 18h6" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M16 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" strokeWidth="1.8" />
            </svg>
          </div>

          <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            AWS AI Cloud Assistant
          </h2>
          <p className="mt-3 max-w-2xl text-base text-slate-400 sm:text-lg">
            Manage your AWS infrastructure using natural language with a premium, conversational experience.
          </p>

          <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onPromptSelect(suggestion)}
                className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-left text-sm text-slate-300 transition hover:border-slate-700 hover:bg-slate-900 hover:text-white"
              >
                {suggestion}
              </button>
            ))}
          </div>

          <div className="mt-8 w-full rounded-2xl border border-slate-800/80 bg-slate-950/70 p-4 text-left">
            <button
              type="button"
              onClick={onToggleTools}
              className="flex w-full items-center justify-between text-sm font-medium text-slate-200"
            >
              Available AWS tools
              <span className="text-slate-400">{showTools ? '−' : '+'}</span>
            </button>
            {showTools && (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {tools.map((tool) => (
                  <div key={tool.name} className="rounded-xl border border-slate-800 bg-slate-900/80 p-3 text-sm text-slate-400">
                    <p className="font-medium text-slate-200">{tool.name}</p>
                    <p className="mt-1 text-xs">{tool.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
