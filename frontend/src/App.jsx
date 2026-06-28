import { useEffect, useMemo, useRef, useState } from 'react'
import { ChatInput } from './components/ChatInput'
import { ChatWindow } from './components/ChatWindow'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { WelcomeScreen } from './components/WelcomeScreen'
import { AuthPage } from './components/AuthPage'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const STORAGE_KEY_USERS = 'aws-agent-users'
const STORAGE_KEY_CURRENT_USER = 'aws-agent-current-user'

function userStorageKey(email) {
  return `aws-agent-sessions-${email}`
}

function activeSessionStorageKey(email) {
  return `aws-agent-active-session-${email}`
}

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

function loadStoredUsers() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY_USERS)
    return raw ? JSON.parse(raw) : {}
  } catch (error) {
    console.error('Failed to load users from storage:', error)
    return {}
  }
}

function saveStoredUsers(users) {
  try {
    window.localStorage.setItem(STORAGE_KEY_USERS, JSON.stringify(users))
  } catch (error) {
    console.error('Failed to save users to storage:', error)
  }
}

function loadStoredCurrentUser() {
  try {
    return window.localStorage.getItem(STORAGE_KEY_CURRENT_USER)
  } catch (error) {
    console.error('Failed to load current user from storage:', error)
    return null
  }
}

function saveCurrentUser(email) {
  try {
    window.localStorage.setItem(STORAGE_KEY_CURRENT_USER, email)
  } catch (error) {
    console.error('Failed to save current user to storage:', error)
  }
}

function clearCurrentUser() {
  try {
    window.localStorage.removeItem(STORAGE_KEY_CURRENT_USER)
  } catch (error) {
    console.error('Failed to clear current user from storage:', error)
  }
}

function loadStoredSessions(email) {
  try {
    const raw = window.localStorage.getItem(userStorageKey(email))
    if (!raw) return null
    return JSON.parse(raw)
  } catch (error) {
    console.error('Failed to load sessions from storage:', error)
    return null
  }
}

function loadStoredActiveSessionId(email) {
  try {
    return window.localStorage.getItem(activeSessionStorageKey(email))
  } catch (error) {
    console.error('Failed to load active session id from storage:', error)
    return null
  }
}

function saveSessions(email, sessions) {
  try {
    window.localStorage.setItem(userStorageKey(email), JSON.stringify(sessions))
  } catch (error) {
    console.error('Failed to save sessions to storage:', error)
  }
}

function saveActiveSessionId(email, sessionId) {
  try {
    window.localStorage.setItem(activeSessionStorageKey(email), sessionId)
  } catch (error) {
    console.error('Failed to save active session id to storage:', error)
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
  const [currentUser, setCurrentUser] = useState(null)
  const [authError, setAuthError] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetch(`${API_URL}/tools`)
      .then((res) => res.json())
      .then((data) => setTools(data.tools || []))
      .catch((error) => console.error('Failed to fetch tools:', error))
  }, [])

  useEffect(() => {
    const email = loadStoredCurrentUser()
    if (!email) {
      return
    }

    setCurrentUser(email)
    const storedSessions = loadStoredSessions(email)
    const storedActiveSessionId = loadStoredActiveSessionId(email)

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
    if (!activeSessionId || !currentUser) return

    saveSessions(currentUser, sessions)
    saveActiveSessionId(currentUser, activeSessionId)
  }, [sessions, activeSessionId, currentUser])

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

  const handleRegister = (email, password) => {
    const users = loadStoredUsers()
    if (users[email]) {
      setAuthError('This email is already registered.')
      return
    }

    users[email] = { password }
    saveStoredUsers(users)
    setAuthError('')
    setCurrentUser(email)
    saveCurrentUser(email)

    const initialSession = createSession([])
    setSessions([initialSession])
    setActiveSessionId(initialSession.id)
    setMessages([])
  }

  const handleLogin = (email, password) => {
    const users = loadStoredUsers()
    if (!users[email] || users[email].password !== password) {
      setAuthError('Invalid email or password.')
      return
    }

    setAuthError('')
    setCurrentUser(email)
    saveCurrentUser(email)

    const storedSessions = loadStoredSessions(email)
    const storedActiveSessionId = loadStoredActiveSessionId(email)

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
  }

  const handleLogout = () => {
    clearCurrentUser()
    setCurrentUser(null)
    setSessions([])
    setActiveSessionId(null)
    setMessages([])
    setInput('')
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

  if (!currentUser) {
    return <AuthPage onLogin={handleLogin} onRegister={handleRegister} errorMessage={authError} />
  }

  return (
    <div className={`flex min-h-screen flex-col bg-slate-950 text-slate-100 lg:flex-row ${darkMode ? '' : 'bg-stone-50 text-stone-900'}`}>
      <Sidebar
        sessions={orderedSessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((value) => !value)}
        userEmail={currentUser}
      />

      <div className="flex min-h-screen flex-1 flex-col">
        <Header
          darkMode={darkMode}
          onToggleDarkMode={() => setDarkMode((value) => !value)}
          connectionStatus="Online"
          userName={currentUser}
          onLogout={handleLogout}
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
