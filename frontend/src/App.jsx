import { useState, useEffect, useRef } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [tools, setTools] = useState([])
  const [showTools, setShowTools] = useState(false)
  const messagesEndRef = useRef(null)

  // Parse and render markdown to React elements
  const parseMarkdown = (text) => {
    if (!text) return null

    const elements = []
    let key = 0

    // Split by headers (###, ##, #)
    const lines = text.split('\n')
    let currentBlock = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]

      // Handle headers
      if (line.startsWith('###')) {
        if (currentBlock.length > 0) {
          elements.push(parseBlock(currentBlock.join('\n'), key++))
          currentBlock = []
        }
        const headerText = line.replace(/^#+\s*/, '').trim()
        elements.push(
          <h3 key={key++} className="markdown-h3">{headerText}</h3>
        )
      } else if (line.startsWith('##')) {
        if (currentBlock.length > 0) {
          elements.push(parseBlock(currentBlock.join('\n'), key++))
          currentBlock = []
        }
        const headerText = line.replace(/^#+\s*/, '').trim()
        elements.push(
          <h2 key={key++} className="markdown-h2">{headerText}</h2>
        )
      } else if (line.startsWith('#')) {
        if (currentBlock.length > 0) {
          elements.push(parseBlock(currentBlock.join('\n'), key++))
          currentBlock = []
        }
        const headerText = line.replace(/^#+\s*/, '').trim()
        elements.push(
          <h1 key={key++} className="markdown-h1">{headerText}</h1>
        )
      } else if (line.trim() === '') {
        if (currentBlock.length > 0) {
          elements.push(parseBlock(currentBlock.join('\n'), key++))
          currentBlock = []
        }
      } else {
        currentBlock.push(line)
      }
    }

    if (currentBlock.length > 0) {
      elements.push(parseBlock(currentBlock.join('\n'), key++))
    }

    return <div className="markdown-content">{elements}</div>
  }

  // Parse a block of text with inline formatting
  const parseBlock = (block, key) => {
    if (!block.trim()) return null

    // Check if it's a numbered list
    if (/^\d+\.\s/.test(block.trim())) {
      // Split by numbered items and process each one
      const numberedItems = block.split(/\n(?=\d+\.\s)/)
      if (numberedItems.length > 1) {
        // Multiple numbered items - render each separately
        return (
          <div key={key}>
            {numberedItems.map((item, idx) => parseListItem(item, `${key}-${idx}`))}
          </div>
        )
      }
      return parseListItem(block, key)
    }

    // Check if it's a bullet list
    if (block.trim().startsWith('•') || block.trim().startsWith('-')) {
      return parseBulletItem(block, key)
    }

    // Regular paragraph with inline formatting
    return (
      <p key={key} className="markdown-p">
        {renderInlineMarkdown(block)}
      </p>
    )
  }

  // Render inline markdown (bold, formatting)
  const renderInlineMarkdown = (text) => {
    const elements = []
    let lastIndex = 0

    // Pattern for **bold** and other inline formatting
    const regex = /\*\*([^*]+)\*\*|`([^`]+)`/g
    let match

    while ((match = regex.exec(text)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        elements.push(text.substring(lastIndex, match.index))
      }

      // Add formatted text
      if (match[1]) {
        // Bold text
        elements.push(
          <strong key={`bold-${match.index}`}>{match[1]}</strong>
        )
      } else if (match[2]) {
        // Code text
        elements.push(
          <code key={`code-${match.index}`}>{match[2]}</code>
        )
      }

      lastIndex = regex.lastIndex
    }

    // Add remaining text
    if (lastIndex < text.length) {
      elements.push(text.substring(lastIndex))
    }

    return elements.length > 0 ? elements : text
  }

  // Parse numbered list item
  const parseListItem = (text, key) => {
    const match = text.match(/^(\d+)\.\s+(.*)/)
    if (!match) return <div key={key}>{text}</div>

    const number = match[1]
    const content = match[2]

    // Parse key-value pairs separated by " - "
    const properties = []
    const parts = content.split(' - ')

    for (const part of parts) {
      const kv = part.match(/\*\*([^*]+):\*\*\s*(.+)/)
      if (kv) {
        properties.push({
          key: kv[1].trim(),
          value: kv[2].trim()
        })
      }
    }

    if (properties.length > 1) {
      // Multiple properties - make it expandable but OPEN by default
      const mainProp = properties[0]
      return (
        <details key={key} className="resource-details" open>
          <summary className="resource-summary">
            <span className="resource-number">{number}.</span>
            <strong>{mainProp.key}:</strong>
            <span className="resource-main-value">{mainProp.value}</span>
            <span className="expand-icon">▼</span>
          </summary>
          <div className="resource-properties">
            {properties.map((prop, idx) => (
              <div key={idx} className="resource-property">
                <span className="prop-key">{prop.key}:</span>
                <span className="prop-value">{prop.value}</span>
              </div>
            ))}
          </div>
        </details>
      )
    } else if (properties.length === 1) {
      // Single property
      return (
        <div key={key} className="resource-item">
          <span className="resource-number">{number}.</span>
          <strong>{properties[0].key}:</strong>
          <span className="resource-main-value">{properties[0].value}</span>
        </div>
      )
    }

    return (
      <div key={key} className="markdown-li">
        <span className="list-marker">{number}.</span>
        <span>{renderInlineMarkdown(content)}</span>
      </div>
    )
  }

  // Parse bullet item
  const parseBulletItem = (text, key) => {
    const content = text.replace(/^[•-]\s*/, '').trim()
    return (
      <div key={key} className="markdown-li bullet">
        <span className="list-marker">•</span>
        <span>{renderInlineMarkdown(content)}</span>
      </div>
    )
  }

  // Format response text with proper structure
  const formatResponse = (text) => {
    if (!text) return null
    return parseMarkdown(text)
  }

  useEffect(() => {
    // Fetch available tools on mount
    fetch(`${API_URL}/tools`)
      .then(res => res.json())
      .then(data => setTools(data.tools || []))
      .catch(err => console.error('Failed to fetch tools:', err))
  }, [])

  useEffect(() => {
    // Auto-scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message to state
    const newMessages = [...messages, { role: 'user', content: userMessage }]
    setMessages(newMessages)
    setLoading(true)

    try {
      // Prepare chat history (include tool calls for context)
      const chatHistory = messages.map(msg => {
        const historyMsg = {
          role: msg.role,
          content: msg.content
        }
        
        // Include tool calls if this is an assistant message
        if (msg.role === 'assistant' && msg.steps && msg.steps.length > 0) {
          historyMsg.tool_calls = msg.steps
        }
        
        return historyMsg
      })

      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage,
          chat_history: chatHistory
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        steps: data.steps,
        duration: data.duration_ms
      }])
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}. Make sure the backend server is running at ${API_URL}`,
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="header-title">
            <h1>AWS Agent</h1>
            <p>S3 • CloudWatch • Cloud Control • Resource Management</p>
          </div>
        </div>
        <div className="header-right">
          <button className="icon-button" title="Toggle theme">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2"/>
              <line x1="12" y1="1" x2="12" y2="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="12" y1="21" x2="12" y2="23" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="1" y1="12" x2="3" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="21" y1="12" x2="23" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
          <button className="clear-button" onClick={clearChat}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Clear
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <h2>Welcome to AWS Agent!</h2>
            <p>Ask me about your AWS resources</p>
            
            <button className="tools-toggle" onClick={() => setShowTools(!showTools)}>
              Available Tools {showTools ? '▲' : '▼'}
            </button>

            {showTools && (
              <div className="tools-list">
                {tools.map((tool, idx) => (
                  <div key={idx} className="tool-item">
                    <strong>{tool.name}</strong>
                    <p>{tool.description}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="example-prompts">
              <h3>Try asking:</h3>
              <button onClick={() => setInput("List all my S3 buckets")} className="example-prompt">
                "List all my S3 buckets"
              </button>
              <button onClick={() => setInput("Show my CloudWatch log groups")} className="example-prompt">
                "Show my CloudWatch log groups"
              </button>
              <button onClick={() => setInput("Create an S3 bucket called my-test-bucket-2026")} className="example-prompt">
                "Create an S3 bucket called my-test-bucket-2026"
              </button>
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-content">
                  {msg.role === 'user' ? (
                    <div className="user-message">
                      <div className="message-avatar">You</div>
                      <div className="message-text">{msg.content}</div>
                    </div>
                  ) : (
                    <div className="assistant-message">
                      <div className="message-avatar">AI</div>
                      <div className="message-text">
                        <div className="formatted-content">
                          {formatResponse(msg.content)}
                        </div>
                        {msg.steps && msg.steps.length > 0 && (
                          <details className="steps-details">
                            <summary>View {msg.steps.length} tool call{msg.steps.length > 1 ? 's' : ''}</summary>
                            {msg.steps.map((step, i) => (
                              <div key={i} className="step-item">
                                <div className="step-header">
                                  <span className="step-number">Step {i + 1}</span>
                                  <span className="step-tool">🔧 {step.tool}</span>
                                </div>
                                <div className="step-input">
                                  <strong>Input:</strong>
                                  <pre>{JSON.stringify(step.tool_input, null, 2)}</pre>
                                </div>
                                <div className="step-observation">
                                  <strong>Result:</strong>
                                  <div className="observation-content">{parseMarkdown(step.observation)}</div>
                                </div>
                              </div>
                            ))}
                          </details>
                        )}
                        {msg.duration && (
                          <div className="duration">⏱️ {msg.duration}ms</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="assistant-message">
                    <div className="message-avatar">AI</div>
                    <div className="message-text loading-dots">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Input Area */}
      <footer className="input-area">
        <form onSubmit={sendMessage} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything... (S3, CloudWatch, Resource Management, etc.)"
            disabled={loading}
            className="message-input"
          />
          <button type="submit" disabled={loading || !input.trim()} className="send-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </form>
      </footer>
    </div>
  )
}

export default App
