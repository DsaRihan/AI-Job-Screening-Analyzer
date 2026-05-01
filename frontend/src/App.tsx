// MAIN ROUTER: Navigation between Job Seeker, Recruiter, Coaching, History, and Landing pages with Firebase authentication
import { Routes, Route } from 'react-router-dom'
import React from 'react'
import Home from './pages/Home'
import Landing from './pages/Landing'
import JobSeeker from './pages/JobSeeker'
import Recruiter from './pages/Recruiter'
import Coaching from './pages/Coaching'
import MockInterview from './pages/MockInterview'
import History from './pages/History'
import Register from './pages/Register'
import RoleChoice from './pages/RoleChoice'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import { useAuth } from './context/AuthContext'

export default function App() {
  const { user } = useAuth()
  const isRecruiter = user?.role === 'recruiter' || user?.role === 'admin'
  const needsRoleSelection = !!user && !user.role

  class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
    constructor(props: any) {
      super(props)
      this.state = { hasError: false }
    }
    static getDerivedStateFromError() { return { hasError: true } }
    componentDidCatch(err: any) { console.error('UI error', err) }
    render() {
      if (this.state.hasError) {
        return <div className="card"><h3>Something went wrong</h3><p>Please refresh or try again.</p></div>
      }
      return this.props.children as any
    }
  }

  if (!user) {
    return (
      <div className="container">
        <main className="landing-main">
          <ErrorBoundary>
            <Routes>
              <Route path="/register" element={<Register />} />
              <Route path="*" element={<Landing />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    )
  }

  return (
      <div className="container">
      {needsRoleSelection ? (
        <main className="landing-main">
          <RoleChoice />
        </main>
      ) : (
        <>
      <NavBar />
      <main>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/job-seeker" element={<JobSeeker />} />
              <Route path="/recruiter" element={isRecruiter ? <Recruiter /> : <div className="card"><h3>Access denied</h3><p>Recruiter role required.</p></div>} />
              <Route path="/coaching" element={<Coaching />} />
              <Route path="/mock-interview" element={<MockInterview />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </ErrorBoundary>
      </main>
      <Footer />
        </>
      )}
    </div>
  )
}
