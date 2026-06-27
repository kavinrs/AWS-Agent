export function Header({ darkMode, onToggleDarkMode, connectionStatus, userName }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-800/80 bg-slate-950/80 px-4 py-3 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-cyan-400 shadow-lg shadow-cyan-950/30">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="stroke-current">
            <path d="M6 7h12M6 12h8M6 17h5" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M18 4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6Z" strokeWidth="1.8" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-white">AWS AI Cloud Assistant</p>
          <p className="text-xs text-slate-400">Connected Region • us-east-1</p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-sm text-emerald-300 sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          {connectionStatus}
        </div>

        <div className="hidden items-center gap-2 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-sm text-slate-300 sm:flex">
          <span className="h-2 w-2 rounded-full bg-cyan-400" />
          {userName}
        </div>

        <button
          type="button"
          onClick={onToggleDarkMode}
          className="rounded-full border border-slate-800 bg-slate-900/80 p-2.5 text-slate-300 transition hover:border-slate-700 hover:text-white"
          aria-label="Toggle theme"
        >
          {darkMode ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="stroke-current">
              <path d="M12 3v2.5M12 18.5V21M4.5 4.5l1.8 1.8M17.7 17.7l1.8 1.8M3 12h2.5M18.5 12H21M4.5 19.5l1.8-1.8M17.7 6.3l1.8-1.8" strokeWidth="1.7" strokeLinecap="round" />
              <circle cx="12" cy="12" r="4" strokeWidth="1.7" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="stroke-current">
              <path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </div>
    </header>
  )
}
