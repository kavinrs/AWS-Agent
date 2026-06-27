import { useState } from 'react'

export function AuthPage({ onLogin, onRegister, errorMessage }) {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()
    if (!email.trim() || !password.trim()) return

    if (isRegister) {
      if (password !== confirmPassword) {
        return
      }
      onRegister(email.trim().toLowerCase(), password)
      return
    }

    onLogin(email.trim().toLowerCase(), password)
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mb-8 text-center">
        <p className="text-3xl font-semibold uppercase tracking-[0.3em] text-cyan-400">AWS Agent</p>
      </div>
      <div className="w-full max-w-md rounded-[32px] border border-slate-800 bg-slate-900/95 p-8 shadow-2xl shadow-black/40">
        <h1 className="mb-4 text-3xl font-semibold text-white">{isRegister ? 'Register' : 'Login'}</h1>
        <p className="mb-6 text-sm text-slate-400">
          {isRegister
            ? 'Create an account to save your chat history by email.'
            : 'Sign in with your email to load your saved conversations.'}
        </p>

        {errorMessage && (
          <div className="mb-4 rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-sm text-slate-300">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-500"
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="block text-sm text-slate-300">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-500"
              placeholder="Password"
              required
            />
          </label>

          {isRegister && (
            <label className="block text-sm text-slate-300">
              Confirm Password
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-500"
                placeholder="Confirm password"
                required
              />
            </label>
          )}

          <button
            type="submit"
            className="w-full rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            {isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-400">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            onClick={() => setIsRegister((value) => !value)}
            className="font-semibold text-cyan-400 hover:text-cyan-200"
          >
            {isRegister ? 'Login' : 'Register'}
          </button>
        </div>
      </div>
    </div>
  )
}
