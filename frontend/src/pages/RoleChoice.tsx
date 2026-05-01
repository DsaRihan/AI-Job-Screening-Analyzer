import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { selectAuthRole } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function RoleChoice() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedRole, setSelectedRole] = useState<'candidate' | 'recruiter' | null>(null)

  const chooseRole = async (role: 'candidate' | 'recruiter') => {
    if (!token) return
    setSelectedRole(role)
    setLoading(true)
    setError(null)
    try {
      await selectAuthRole(token, role)
      window.sessionStorage.setItem('pendingUserRole', role)
      window.location.reload()
    } catch (err: any) {
      setSelectedRole(null)
      setError(err?.message || 'Could not save role')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="landing-shell">
      <div className="landing-atmosphere" aria-hidden="true" />
      <section className="landing-hero">
        <h1>Choose Your Path</h1>
        <p className="landing-tagline">Are you here as a job seeker or recruiter?</p>

        <div className="landing-auth-card" style={{ display: 'grid', gap: '1rem' }}>
          {!selectedRole && (
            <>
              <button className="btn landing-cta" onClick={() => chooseRole('candidate')} disabled={loading}>
                I’m a Job Seeker
              </button>
              <button className="btn secondary landing-cta" onClick={() => chooseRole('recruiter')} disabled={loading}>
                I’m a Recruiter
              </button>
            </>
          )}

          {selectedRole === 'candidate' && <p className="landing-auth-message">Taking you to the Job Seeker experience…</p>}
          {selectedRole === 'recruiter' && <p className="landing-auth-message">Taking you to the Recruiter experience…</p>}

          {error && <p className="landing-auth-error">{error}</p>}

          <button className="btn" onClick={() => navigate('/')} disabled={loading}>
            Skip for now
          </button>
        </div>
      </section>
    </div>
  )
}