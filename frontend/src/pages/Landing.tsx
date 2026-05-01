import { useAuth } from '../context/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import LoaderOverlay from '../components/LoaderOverlay'

const featureCards = [
  {
    title: 'Resume Intelligence',
    description: 'Analyze resumes against job descriptions with lexical and semantic scoring to surface strengths and gaps instantly.'
  },
  {
    title: 'Interview Readiness',
    description: 'Generate role-focused mock interview questions and coaching plans that turn weak points into interview confidence.'
  },
  {
    title: 'Recruiter Toolkit',
    description: 'Create polished job descriptions, review candidate insights, and track analysis history from one unified workspace.'
  }
]

export default function Landing() {
  const { user, signIn, signInWithEmail, authMessage } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'google' | 'email'>('google')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorSeq, setErrorSeq] = useState(0)

  const formatAuthError = (err: any, fallback: string) => {
    const raw = typeof err === 'string' ? err : (err?.message || err?.error || err?.toString?.() || '')
    const trimmed = raw.trim()

    if (!trimmed) return fallback

    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        const parsed = JSON.parse(trimmed)
        const parsedMessage = parsed?.message || parsed?.error || parsed?.detail || parsed?.details
        if (typeof parsedMessage === 'string' && parsedMessage.trim()) return parsedMessage.trim()
      } catch {
        // Ignore JSON parse failures and fall back to the raw text below.
      }
    }

    const friendlyMap: Record<string, string> = {
      'auth/invalid-credential': 'The email or password you entered is incorrect.',
      'auth/wrong-password': 'The password you entered is incorrect.',
      'auth/user-not-found': 'No account was found for that email address.',
      'auth/popup-closed-by-user': 'Sign-in was canceled before completion.',
      'auth/cancelled-popup-request': 'Another sign-in popup is already open.',
      'auth/unauthorized-domain': 'This domain is not authorized for Google sign-in.',
      'auth/network-request-failed': 'Network error. Please check your connection and try again.'
    }

    for (const [key, message] of Object.entries(friendlyMap)) {
      if (trimmed.includes(key)) return message
    }

    return trimmed.replace(/^Firebase:\s*/i, '').replace(/^Error:\s*/i, '') || fallback
  }

  const showAuthError = (err: any, fallback: string) => {
    const message = formatAuthError(err, fallback)
    setError(message)
    setErrorSeq((value) => value + 1)
    window.alert(message)
  }

  useEffect(() => {
    if (!error) return
    const timer = window.setTimeout(() => setError(null), 4500)
    return () => window.clearTimeout(timer)
  }, [error, errorSeq])

  useEffect(() => {
    if (user) {
      navigate('/')
    }
  }, [user, navigate])

  const handleSignIn = async () => {
    setError(null)
    setLoading(true)
    try {
      await signIn()
    } catch (err: any) {
      showAuthError(err, 'Google sign-in failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleEmailLogin = async () => {
    setError(null)
    setLoading(true)
    try {
      await signInWithEmail(email, password)
    } catch (err: any) {
      showAuthError(err, 'Email sign-in failed. Please check your credentials and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="landing-shell">
      <div className="landing-atmosphere" aria-hidden="true" />
      <LoaderOverlay show={loading} message={mode === 'google' ? 'Signing you in…' : 'Verifying credentials…'} />
      <section className="landing-hero">
        <h1>AI Job Screening & Coaching Platform</h1>
        <p className="landing-tagline">Analyze Your Resume With AI</p>
        <p className="landing-copy">
          A professional end-to-end platform for job seekers and recruiters, combining resume diagnostics, interview prep,
          coaching workflows, and analytics in one intelligent dashboard.
        </p>

        <div className="landing-auth-card">
          <div className="landing-auth-tabs" aria-label="Login methods">
            <button className={`btn secondary ${mode === 'google' ? 'active' : ''}`} onClick={() => setMode('google')}>Google</button>
            <button className={`btn secondary ${mode === 'email' ? 'active' : ''}`} onClick={() => setMode('email')}>Email</button>
          </div>

          {mode === 'google' && (
            <div className="landing-auth-action">
              <button className="btn landing-cta" onClick={handleSignIn} disabled={loading}>
                {loading ? 'Signing in...' : 'Sign in with Google'}
              </button>
            </div>
          )}

          {mode === 'email' && (
            <div className="landing-auth-form">
              <p style={{ margin: '0 0 0.5rem', color: 'var(--muted)', fontSize: '0.95rem' }}>
                Email login only works if Email/Password is enabled in Firebase and the password matches the user you created.
              </p>
              <label>Email
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="recruiter@company.com" />
              </label>
              <label>Password
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" />
              </label>
              <button className="btn landing-cta" onClick={handleEmailLogin} disabled={loading || !email || !password}>
                {loading ? 'Signing in...' : 'Sign in with Email'}
              </button>
            </div>
          )}

          {authMessage && <p className="landing-auth-message">{authMessage}</p>}
          {error && <p className="landing-auth-error">{error}</p>}

          <div style={{ marginTop: '1rem', textAlign: 'center', fontSize: '0.95rem', color: 'var(--muted)' }}>
            Don't have an account? <Link to="/register" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: '500' }}>Register here</Link>
          </div>
        </div>
      </section>

      <section className="landing-features" aria-label="Key Features">
        {featureCards.map((card) => (
          <article className="landing-feature-card" key={card.title}>
            <h3>{card.title}</h3>
            <p>{card.description}</p>
          </article>
        ))}
      </section>
    </div>
  )
}
