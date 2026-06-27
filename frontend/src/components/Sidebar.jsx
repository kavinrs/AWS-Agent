export function Sidebar({
  sessions = [],
  activeSessionId,
  onNewChat,
  onSelectSession,
  collapsed,
  onToggleCollapse,
  userEmail,
}) {
  const groupSessions = (items) => {
    const sorted = [...items].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    const groups = { today: [], yesterday: [], previous: [] }
    const now = new Date()
    const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const startYesterday = new Date(startToday)
    startYesterday.setDate(startYesterday.getDate() - 1)

    sorted.forEach((session) => {
      const createdAt = new Date(session.createdAt)
      if (createdAt >= startToday) {
        groups.today.push(session)
      } else if (createdAt >= startYesterday) {
        groups.yesterday.push(session)
      } else {
        groups.previous.push(session)
      }
    })

    return groups
  }

  const grouped = groupSessions(sessions)

  const renderSection = (title, items) => (
    <div className="space-y-2">
      <p className="px-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{title}</p>
      {items.map((session) => {
        const isActive = session.id === activeSessionId
        return (
          <button
            key={session.id}
            type="button"
            onClick={() => onSelectSession(session.id)}
            className={`flex w-full items-center rounded-2xl border px-3 py-2.5 text-left text-sm transition ${
              isActive
                ? 'border-cyan-500/30 bg-cyan-500/10 text-white shadow-sm'
                : 'border-transparent bg-slate-900/50 text-slate-300 hover:border-slate-800 hover:bg-slate-900/80'
            }`}
          >
            <span className="mr-2 text-slate-500">✦</span>
            <span className="truncate">{session.title || 'New conversation'}</span>
          </button>
        )
      })}
    </div>
  )

  return (
    <aside className={`flex h-full flex-col border-r border-slate-800/80 bg-slate-950/95 transition-all duration-300 ${collapsed ? 'w-20' : 'w-72'}`}>
      <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-4">
        {!collapsed ? (
          <div>
            <p className="text-sm font-semibold text-white">AWS Agent</p>
            <p className="text-xs text-slate-400">Cloud operations copilot</p>
          </div>
        ) : (
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-cyan-400">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="stroke-current">
              <path d="M5 7h14M5 12h8M5 17h6" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </div>
        )}
        <button
          type="button"
          onClick={onToggleCollapse}
          className="rounded-full border border-slate-800 bg-slate-900/80 p-2 text-slate-400 transition hover:text-white"
          aria-label="Toggle sidebar"
        >
          {collapsed ? '→' : '←'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        <button
          type="button"
          onClick={onNewChat}
          className="mb-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-3 text-sm font-medium text-cyan-300 transition hover:bg-cyan-500/20"
        >
          <span className="text-base">+</span>
          {!collapsed && 'New Chat'}
        </button>

        {!collapsed && (
          <div className="space-y-5">
            {grouped.today.length > 0 && renderSection('Today\'s Chats', grouped.today)}
            {grouped.yesterday.length > 0 && renderSection('Yesterday', grouped.yesterday)}
            {grouped.previous.length > 0 && renderSection('Previous Chats', grouped.previous)}
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="border-t border-slate-800/80 p-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <p className="text-sm font-medium text-slate-200">Signed in</p>
            <p className="mt-1 text-xs text-slate-400">{userEmail || 'Unknown user'}</p>
          </div>
        </div>
      )}
    </aside>
  )
}
