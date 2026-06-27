import { useEffect, useMemo, useRef, useState } from 'react'
import { ChatInput } from './components/ChatInput'
import { ChatWindow } from './components/ChatWindow'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { WelcomeScreen } from './components/WelcomeScreen'

const API_URL = 'http://localhost:8000'
const STORAGE_KEY_SESSIONS = 'aws-agent-sessions'
const STORAGE_KEY_ACTIVE_SESSION = 'aws-agent-active-session'

function createSession(messages = []) {
  const firstUserPrompt = messages.find((item) => item.role === 'user')?.content || 'New conversation'

  return {
    id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title: firstUserPrompt.slice(0, 40),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messages,
  }
}

function loadStoredSessions() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY_SESSIONS)
    if (!raw) return null
    return JSON.parse(raw)
  } catch (error) {
    console.error('Failed to load sessions from storage:', error)
    return null
  }
}

function loadStoredActiveSessionId() {
  try {
    return window.localStorage.getItem(STORAGE_KEY_ACTIVE_SESSION)
  } catch (error) {
    console.error('Failed to load active session id from storage:', error)
    return null
  }
}

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [tools, setTools] = useState([])
  const [showTools, setShowTools] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [darkMode, setDarkMode] = useState(true)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetch(`${API_URL}/tools`)
      .then((res) => res.json())
      .then((data) => setTools(data.tools || []))
      .catch((error) => console.error('Failed to fetch tools:', error))
  }, [])

  useEffect(() => {
    const storedSessions = loadStoredSessions()
    const storedActiveSessionId = loadStoredActiveSessionId()

    if (storedSessions?.length > 0) {
      setSessions(storedSessions)
      if (storedActiveSessionId && storedSessions.some((session) => session.id === storedActiveSessionId)) {
        setActiveSessionId(storedActiveSessionId)
        const selectedSession = storedSessions.find((session) => session.id === storedActiveSessionId)
        setMessages(selectedSession?.messages || [])
        return
      }

      const firstSession = storedSessions[0]
      setActiveSessionId(firstSession.id)
      setMessages(firstSession.messages || [])
      return
    }

    const initialSession = createSession([])
    setSessions([initialSession])
    setActiveSessionId(initialSession.id)
    setMessages([])
  }, [])

  useEffect(() => {
    if (!activeSessionId) return

    try {
      window.localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions))
      window.localStorage.setItem(STORAGE_KEY_ACTIVE_SESSION, activeSessionId)
    } catch (error) {
      console.error('Failed to save sessions to storage:', error)
    }
  }, [sessions, activeSessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const persistSession = (nextMessages, titleOverride) => {
    if (!activeSessionId) return

    setSessions((prev) =>
      prev.map((session) =>
        session.id === activeSessionId
          ? {
              ...session,
              messages: nextMessages,
              title: titleOverride || session.title || 'New conversation',
              updatedAt: new Date().toISOString(),
            }
          : session,
      ),
    )
  }

  const handleNewChat = () => {
    if (activeSessionId) {
      persistSession(messages)
    }

    const freshSession = createSession([])
    setSessions((prev) => [freshSession, ...prev.filter((session) => session.id !== freshSession.id)])
    setActiveSessionId(freshSession.id)
    setMessages([])
    setInput('')
  }

  const handleSelectSession = (sessionId) => {
    const selectedSession = sessions.find((session) => session.id === sessionId)
    if (!selectedSession) return

    setActiveSessionId(sessionId)
    setMessages(selectedSession.messages || [])
    setInput('')
  }

  const sendMessage = async (event) => {
    event.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    const currentMessages = messages
    const optimisticMessages = [...currentMessages, { role: 'user', content: userMessage }]

    setInput('')
    setMessages(optimisticMessages)
    persistSession(optimisticMessages, userMessage.slice(0, 40))
    setLoading(true)

    try {
      const chatHistory = currentMessages.map((message) => {
        const historyMessage = { role: message.role, content: message.content }
        if (message.role === 'assistant' && message.steps?.length > 0) {
          historyMessage.tool_calls = message.steps
        }
        return historyMessage
      })

      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, chat_history: chatHistory }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        steps: data.steps || [],
        duration: data.duration_ms,
        approval_required: data.approval_required,
        approval_id: data.approval_id,
        approval_message: data.approval_message,
        ragSources: data.rag_sources || [],
      }

      const nextMessages = [...optimisticMessages, assistantMessage]
      setMessages(nextMessages)
      persistSession(nextMessages)
    } catch (error) {
      const fallbackMessage = {
        role: 'assistant',
        content: `Error: ${error.message}. Make sure the backend server is running at ${API_URL}`,
        error: true,
      }
      const nextMessages = [...optimisticMessages, fallbackMessage]
      setMessages(nextMessages)
      persistSession(nextMessages)
    } finally {
      setLoading(false)
    }
  }

  const approveDeletion = async (approvalId) => {
    try {
      const response = await fetch(`${API_URL}/approve/${approvalId}`, { method: 'POST' })

      if (!response.ok) {
        const errText = await response.text()
        throw new Error(`Approval failed: ${response.status} ${errText}`)
      }

      const data = await response.json()
      const assistantMessage = {
        role: 'assistant',
        content: `Deletion approved and executed. Result: ${JSON.stringify(data.result)}`,
        steps: [],
      }
      const nextMessages = [...messages, assistantMessage]
      setMessages(nextMessages)
      persistSession(nextMessages)
    } catch (error) {
      const fallbackMessage = {
        role: 'assistant',
        content: `Approval error: ${error.message}`,
        error: true,
      }
      const nextMessages = [...messages, fallbackMessage]
      setMessages(nextMessages)
      persistSession(nextMessages)
    }
  }

  const orderedSessions = useMemo(() => [...sessions].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)), [sessions])

  return (
    <div className={`flex min-h-screen flex-col bg-slate-950 text-slate-100 lg:flex-row ${darkMode ? '' : 'bg-stone-50 text-stone-900'}`}>
      <Sidebar
        sessions={orderedSessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((value) => !value)}
      />

      <div className="flex min-h-screen flex-1 flex-col">
        <Header
          darkMode={darkMode}
          onToggleDarkMode={() => setDarkMode((value) => !value)}
          connectionStatus="Online"
          userName="admin"
        />

        <main className="flex-1 overflow-hidden">
          {messages.length === 0 ? (
            <WelcomeScreen
              onPromptSelect={(prompt) => setInput(prompt)}
              tools={tools}
              showTools={showTools}
              onToggleTools={() => setShowTools((value) => !value)}
            />
          ) : (
            <ChatWindow messages={messages} loading={loading} onApprove={approveDeletion} messagesEndRef={messagesEndRef} />
          )}
        </main>

        <footer className="border-t border-slate-800/80 bg-slate-950/90 px-4 py-4 sm:px-6">
          <div className="mx-auto max-w-7xl">
            <ChatInput
              value={input}
              onChange={setInput}
              onSubmit={sendMessage}
              loading={loading}
              onAttach={() => setShowTools(true)}
            />
          </div>
        </footer>
      </div>
    </div>
  )
}

export default App
