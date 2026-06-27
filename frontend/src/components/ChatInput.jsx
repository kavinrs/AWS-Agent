export function ChatInput({ value, onChange, onSubmit, loading, onAttach }) {
  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit(event)
    }
  }

  return (
    <form onSubmit={onSubmit} className="rounded-[28px] border border-slate-800/80 bg-slate-900/90 p-2 shadow-2xl shadow-black/20 backdrop-blur">
      <div className="flex items-end gap-2">
        <button
          type="button"
          onClick={onAttach}
          className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/80 text-slate-400 transition hover:border-slate-700 hover:text-white"
          aria-label="Attach file"
        >
          +
        </button>

        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask about EC2, S3, RDS, logs, or policies..."
          disabled={loading}
          className="min-h-[48px] flex-1 resize-none border-0 bg-transparent px-2 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500"
        />

        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-500 text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
          aria-label="Send message"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="stroke-current">
            <path d="m5 12 14-7-4 7 4 7-14-7Z" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </form>
  )
}
