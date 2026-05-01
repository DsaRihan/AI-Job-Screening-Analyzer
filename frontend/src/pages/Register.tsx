import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { API_BASE } from '../api/client'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setMsg(null)
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, displayName }),
      })

      const contentType = res.headers.get('content-type') || ''
      const rawBody = await res.text()
      const j = rawBody && contentType.includes('application/json') ? JSON.parse(rawBody) : null

      if (!res.ok) throw new Error(j?.message || rawBody || 'Register failed')
      setMsg('Registered successfully. Please sign in.')
    } catch (err: any) {
      setMsg(err.message || String(err))
    }
  }

  return (
    <div className="landing-shell">
      <div className="landing-atmosphere" aria-hidden="true" />
      <section className="landing-hero">
        <h1>Create Your Account</h1>
        <p className="landing-tagline">Join the AI Job Screening Platform</p>

        <div className="landing-auth-card">
          <form onSubmit={submit}>
            <label style={{ display: 'block', marginBottom: '1rem' }}>
              Email
              <input 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                type="email" 
                required
                placeholder="your@email.com"
                style={{ marginTop: '0.5rem', width: '100%', padding: '0.75rem', borderRadius: 'var(--radius)' }}
              />
            </label>
            <label style={{ display: 'block', marginBottom: '1rem' }}>
              Password
              <input 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                type="password" 
                required
                placeholder="Minimum 6 characters"
                style={{ marginTop: '0.5rem', width: '100%', padding: '0.75rem', borderRadius: 'var(--radius)' }}
              />
            </label>
            <label style={{ display: 'block', marginBottom: '1.5rem' }}>
              Display Name (optional)
              <input 
                value={displayName} 
                onChange={(e) => setDisplayName(e.target.value)} 
                placeholder="Your name"
                style={{ marginTop: '0.5rem', width: '100%', padding: '0.75rem', borderRadius: 'var(--radius)' }}
              />
            </label>
            <button type="submit" className="btn landing-cta">Create Account</button>
          </form>

          {msg && <p style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: msg.includes('successfully') ? '#d4edda' : '#f8d7da', color: msg.includes('successfully') ? '#155724' : '#721c24', borderRadius: 'var(--radius)' }}>{msg}</p>}

          <div style={{ marginTop: '1rem', textAlign: 'center', fontSize: '0.95rem', color: 'var(--muted)' }}>
            Already have an account? <Link to="/" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: '500' }}>Sign in here</Link>
          </div>
        </div>
      </section>
    </div>
  )
}
