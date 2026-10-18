import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ArrowRight, Check, Eye, EyeOff, Layers, LoaderCircle, LockKeyhole, LogOut, Mail, ShieldCheck } from 'lucide-react'
import { api, clearSession, getErrorMessage, getToken, signIn, subscribeToSessionExpiry } from './lib/api'
import './App.css'
import WorkItems from './components/WorkItems'

function Brand() {
  return <a className="brand" href="/" aria-label="Newtonite Ops home"><span className="brand-mark"><Layers size={23} /></span><span>newtonite<span className="brand-suffix"> / ops</span></span></a>
}

function Login({ onLogin, notice }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (pending) return
    setError('')
    setPending(true)
    try {
      onLogin(await signIn(email.trim(), password))
    } catch (failure) {
      setError(getErrorMessage(failure, 'login'))
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="login-layout">
      <aside className="story-panel">
        <Brand />
        <div className="story-content">
          <span className="eyebrow"><span className="status-dot" /> YOUR TEAM. IN SYNC.</span>
          <h1>Good work starts<br />with a clear <span>workspace.</span></h1>
          <p>Bring your people, priorities, and everyday operations together. Make room for what matters.</p>
          <div className="workflow-illustration" aria-hidden="true">
            <div className="illustration-heading"><span><Layers size={16} /> A little more clarity.</span><span className="mini-dots">•••</span></div>
            <div className="workflow-row"><span className="task-check"><Check size={14} /></span><span>Keep priorities in focus</span><span className="task-tag">Organize</span></div>
            <div className="workflow-row"><span className="task-check"><Check size={14} /></span><span>Move forward together</span><span className="task-tag">Collaborate</span></div>
            <div className="workflow-row"><span className="task-check"><Check size={14} /></span><span>Make every update count</span><span className="task-tag">Track</span></div>
          </div>
        </div>
        <div className="story-footer"><span>Built for the way teams work.</span><span>NEWTONITE OPS</span></div>
      </aside>
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="mobile-brand"><Brand /></div>
        <div className="login-card">
          <span className="form-icon"><LockKeyhole size={23} /></span>
          <p className="eyebrow form-eyebrow">YOUR WORKSPACE AWAITS</p>
          <h2 id="login-heading">Welcome back.</h2>
          <p className="form-description">Sign in to your Newtonite Ops account.</p>
          <form onSubmit={handleSubmit} aria-busy={pending}>
            {(error || notice) && <div className="form-alert" role="alert">{error || notice}</div>}
            <label htmlFor="email">Work email</label>
            <div className="input-wrap"><Mail size={18} aria-hidden="true" /><input id="email" name="email" type="email" autoComplete="username" placeholder="you@company.com" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={pending} /></div>
            <label htmlFor="password">Password</label>
            <div className="input-wrap"><LockKeyhole size={18} aria-hidden="true" /><input id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={pending} /><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
            <button className="primary-button" type="submit" disabled={pending}>{pending ? <><LoaderCircle size={18} className="spinner" /> Signing in…</> : <>Sign in to workspace <ArrowRight size={18} /></>}</button>
          </form>
          <p className="access-note">Need access or help with your password?<br /><strong>Contact your workspace administrator.</strong></p>
        </div>
        <p className="security-note"><ShieldCheck size={16} /> Your workspace, securely connected.</p>
      </section>
    </main>
  )
}

function Dashboard({ user, onLogout }) {
  return <div className="workspace"><header className="workspace-header"><Brand /><div className="workspace-account"><span title={user.email}>{user.name}</span><button className="secondary-button" onClick={onLogout}><LogOut size={16} /> Sign out</button></div></header><WorkItems user={user} /></div>
}

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))
  const [restoreError, setRestoreError] = useState('')
  const [notice, setNotice] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => subscribeToSessionExpiry(() => {
    setUser(null)
    setNotice('Your session has expired. Please sign in again.')
  }), [])

  useEffect(() => {
    if (!getToken()) return
    const controller = new AbortController()
    api.get('/me', { signal: controller.signal }).then(({ data }) => {
      if (!controller.signal.aborted) setUser(data)
    }).catch((error) => {
      if (!controller.signal.aborted && error.response?.status !== 401) setRestoreError(getErrorMessage(error))
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [attempt])

  function logout() {
    clearSession()
    setUser(null)
    setNotice('')
    setRestoreError('')
  }

  function retryRestore() {
    setLoading(true)
    setRestoreError('')
    setAttempt((value) => value + 1)
  }

  if (loading) return <main className="session-screen" role="status"><LoaderCircle className="spinner" size={28} /><p>Opening your workspace…</p></main>
  if (restoreError) return <main className="session-screen"><ShieldCheck size={32} /><h1>Let’s reconnect.</h1><p role="alert">{restoreError}</p><button className="primary-button" onClick={retryRestore}>Try again</button><button className="secondary-button" onClick={logout}>Back to sign in</button></main>

  return <BrowserRouter><Routes><Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Login notice={notice} onLogin={(profile) => { setUser(profile); setNotice('') }} />} /><Route path="/dashboard" element={user ? <Dashboard user={user} onLogout={logout} /> : <Navigate to="/login" replace />} /><Route path="*" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} /></Routes></BrowserRouter>
}

export default App
