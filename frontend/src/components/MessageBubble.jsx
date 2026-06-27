import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ToolExecution } from './ToolExecution'
import { ResourceDetail } from './ResourceDetail'

const normalizeLine = (line = '') =>
  line
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/\s*\|\s*/g, ': ')
    .replace(/^-+$/, '')
    .trim()

const normalizeLabel = (label = '') => {
  const map = {
    'resource name': 'Resource Name',
    name: 'Resource Name',
    type: 'Resource Type',
    'resource type': 'Resource Type',
    status: 'Status',
    arn: 'ARN',
    region: 'Region',
    'account id': 'Account ID',
    vpc: 'VPC',
    endpoint: 'Endpoint',
    engine: 'Engine',
  }
  const normalized = label.trim().toLowerCase()
  return map[normalized] || label.replace(/\b\w/g, (char) => char.toUpperCase())
}

const parseResourceList = (text = '') => {
  const lines = text
    .split('\n')
    .map((line) => normalizeLine(line))
    .filter((line) => line.length > 0)

  const startIndexes = lines
    .map((line, index) => ({ line, index }))
    .filter(({ line }) => /resource name:/i.test(line))
    .map(({ index }) => index)

  if (!startIndexes.length) {
    return null
  }

  const titleLine = lines.find((line) => /resources found/i.test(line)) || 'AWS Resources Found'
  const summaryLine = lines.find((line) => /total:\s*\d+/i.test(line)) || ''

  const resources = startIndexes.map((startIndex, index) => {
    const endIndex = startIndexes[index + 1] || lines.length
    const block = lines.slice(startIndex, endIndex)
    const fields = {}

    block.forEach((line) => {
      line.split(/\s*-\s*/).forEach((segment) => {
        const [rawLabel, ...rest] = segment.split(/:\s*/)
        if (!rawLabel || !rest.length) return
        const label = normalizeLabel(rawLabel)
        const value = rest.join(': ').trim()
        if (value) {
          fields[label] = value
        }
      })
    })

    return { id: `resource-${index}`, fields }
  })

  return {
    title: titleLine,
    summary: summaryLine,
    count: resources.length,
    resources,
  }
}

const getOrderedFields = (fields) => {
  const priority = ['Resource Name', 'Account ID', 'Resource Type', 'Status', 'ARN', 'Region', 'VPC', 'Endpoint', 'Engine']
  const ordered = []

  priority.forEach((key) => {
    if (fields[key]) ordered.push([key, fields[key]])
  })

  Object.keys(fields)
    .filter((key) => !priority.includes(key))
    .sort()
    .forEach((key) => ordered.push([key, fields[key]]))

  return ordered
}

export function MessageBubble({ message, onApprove }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[92%] rounded-[24px] rounded-br-md border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-sm text-slate-100 shadow-sm sm:max-w-[88%]">
          {message.content}
        </div>
      </div>
    )
  }

  const resourceList = parseResourceList(message.content)

  return (
    <div className="flex justify-start">
      <div className="w-full rounded-[24px] rounded-bl-md border border-slate-800/80 bg-slate-900/80 px-4 py-3 text-sm text-slate-200 shadow-sm sm:max-w-[96%]">
        {resourceList ? (
          <div className="space-y-5">
            <div className="rounded-[30px] border border-slate-800/90 bg-slate-950/95 p-6 shadow-2xl shadow-black/20">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-base font-semibold uppercase tracking-[0.3em] text-cyan-300">{resourceList.title}</p>
                  {resourceList.summary && <p className="mt-1 text-sm text-slate-300">{resourceList.summary}</p>}
                </div>
                <div className="rounded-full bg-slate-900/90 px-4 py-2 text-sm font-medium text-slate-100 shadow-sm shadow-slate-950/40">
                  Total: {resourceList.count}
                </div>
              </div>

              <div className="mt-6 space-y-4">
                {resourceList.resources.map((resource, index) => (
                  <div key={resource.id} className="overflow-hidden rounded-[28px] border border-slate-800/90 bg-slate-900/90 p-5 shadow-sm shadow-black/10">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-lg font-semibold text-slate-100">Resource {index + 1}</p>
                        <p className="mt-1 text-sm text-slate-400">Clean, structured AWS resource details.</p>
                      </div>
                      {resource.fields.Status && (
                        <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200">
                          {resource.fields.Status}
                        </span>
                      )}
                    </div>

                    <div className="mt-5 space-y-3">
                      {getOrderedFields(resource.fields).map(([label, value]) => (
                        <ResourceDetail key={label} label={label} value={value} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="prose prose-invert max-w-none prose-p:my-2 prose-pre:rounded-2xl prose-pre:border prose-pre:border-slate-800 prose-pre:bg-slate-950 prose-code:rounded prose-code:bg-slate-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-cyan-300">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}

        {message.steps?.length > 0 && (
          <details className="mt-4 rounded-2xl border border-slate-800/80 bg-slate-950/60 p-3" data-testid="tool-call-collapse">
            <summary className="cursor-pointer rounded-2xl border border-slate-800/80 bg-slate-900/80 px-4 py-3 text-sm font-semibold text-slate-100 transition hover:border-slate-700 hover:bg-slate-900">
              View tool calls ({message.steps.length})
            </summary>
            <div className="mt-3 space-y-3">
              <ToolExecution steps={message.steps} />
            </div>
          </details>
        )}

        {message.approval_required && message.approval_id && (
          <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4">
            <div className="flex items-start gap-2">
              <span className="text-amber-400">⚠</span>
              <div>
                <p className="font-semibold text-amber-200">High Risk Operation</p>
                <p className="mt-1 text-sm text-amber-100/90">{message.approval_message || 'Confirmation needed before continuing.'}</p>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={() => onApprove?.(message.approval_id)}
                className="rounded-full border border-amber-400/30 bg-amber-500/20 px-3 py-1.5 text-sm font-medium text-amber-200 transition hover:bg-amber-500/30"
              >
                Approve
              </button>
            </div>
          </div>
        )}

        {message.duration && (
          <div className="mt-3 text-xs text-slate-500">Completed in {message.duration}ms</div>
        )}
      </div>
    </div>
  )
}
