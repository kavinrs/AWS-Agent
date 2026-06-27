import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

export function ChatWindow({ messages, loading, onApprove, messagesEndRef }) {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
      {messages.length === 0 ? (
        <div className="flex h-full items-center justify-center">
          <div className="w-full max-w-3xl rounded-[32px] border border-slate-800/80 bg-slate-900/70 p-8 shadow-2xl shadow-black/20 backdrop-blur">
            <div className="text-center">
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl border border-slate-800 bg-slate-950/80 text-cyan-400 shadow-lg shadow-cyan-950/30 mx-auto">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="stroke-current">
                  <path d="M6 7h12M6 12h8M6 17h5" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M18 4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6Z" strokeWidth="1.8" />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-white">AWS AI Cloud Assistant</h2>
              <p className="mt-2 text-slate-400">Manage your AWS infrastructure using natural language.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="mx-auto flex max-w-7xl flex-col gap-4">
          {messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} message={message} onApprove={onApprove} />
          ))}
          {loading && (
            <div className="max-w-[90%]">
              <TypingIndicator />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  )
}
