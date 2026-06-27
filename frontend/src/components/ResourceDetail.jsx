export function ResourceDetail({ label, value }) {
  return (
    <div className="grid w-full gap-1 text-sm sm:grid-cols-[180px_minmax(0,1fr)] sm:items-start">
      <div className="font-medium text-slate-400 sm:text-right">{label}</div>
      <div className="break-words text-slate-100">{value}</div>
    </div>
  )
}
