import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { useSession } from '../../app/session-context'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import Brand from '../../components/Brand'
import { registerAccount, signIn } from '../../lib/accounts'
import {
  isSignupPasswordValid,
  PASSWORD_REQUIREMENTS,
} from '../../lib/password-policy'

export default function AuthPage({ register = false }: { register?: boolean }) {
  const { user, setUser, phase } = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (phase === 'loading')
    return (
      <main className="session-state" role="status">
        Restoring your session…
      </main>
    )
  if (user) return <Navigate to="/" replace />
  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (register && password !== confirmation) {
      setError('The passwords do not match.')
      return
    }
    if (register && !isSignupPasswordValid(password)) {
      setError(PASSWORD_REQUIREMENTS)
      return
    }
    setBusy(true)
    try {
      if (register) {
        await registerAccount(name, email, password)
        navigate('/login?registered=1', { replace: true })
      } else {
        setUser((await signIn(email, password)).user)
        navigate('/', { replace: true })
      }
      setPassword('')
      setConfirmation('')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Please try again.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="auth-page">
      <header className="public-header">
        <Link to="/" className="wordmark">
          <Brand />
        </Link>
        <span className="quiet-label">
          A little clarity. A better tomorrow.
        </span>
      </header>
      <main className="auth-layout">
        <section className="auth-story" aria-label="Welcome to WagaMaga">
          <img
            className="auth-story-image"
            src="/images/chilli-field-hero-v1.webp"
            width="1672"
            height="941"
            alt="AI-generated view of a chilli field at sunrise"
          />
          <p className="eyebrow">Grow with confidence</p>
          <h1>
            Good decisions
            <br />
            start with
            <br />
            <em>a strong foundation.</em>
          </h1>
          <p>
            A space for your next growing season.
            <br />
            Start with an account that’s yours.
          </p>
          <span className="story-footnote">
            Thoughtful guidance. Human decisions.
          </span>
        </section>
        <section className="auth-card" aria-labelledby="auth-title">
          <span className="section-number">
            {register ? '01 / Get started' : 'Welcome back'}
          </span>
          <h2 id="auth-title">
            {register ? 'Create your account' : 'Make yourself at home.'}
          </h2>
          <p className="muted">
            {register
              ? 'Register as a farmer. Your account is the first step.'
              : 'Sign in to your WagaMaga account.'}
          </p>
          {!register && params.has('registered') && (
            <Notice
              success
              message="Registration request processed. You can now try signing in."
            />
          )}
          {error && <Notice message={error} />}
          <form onSubmit={submit} aria-busy={busy}>
            {register && (
              <Field
                label="Display name"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                minLength={2}
                maxLength={80}
              />
            )}
            <Field
              label="Email address"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              maxLength={254}
            />
            <Field
              label="Password"
              type="password"
              autoComplete={register ? 'new-password' : 'current-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={register ? 8 : 1}
              maxLength={128}
              hint={register ? PASSWORD_REQUIREMENTS : undefined}
            />
            {register && (
              <Field
                label="Confirm password"
                type="password"
                autoComplete="new-password"
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
                required
                minLength={8}
                maxLength={128}
              />
            )}
            <button
              type="submit"
              className="primary full-width"
              disabled={busy}
            >
              {busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}{' '}
              <span aria-hidden="true">↗</span>
            </button>
          </form>
          <p className="auth-switch">
            {register ? 'Already have an account?' : 'New to WagaMaga?'}{' '}
            <Link to={register ? '/login' : '/register'}>
              {register ? 'Sign in' : 'Create an account'}
            </Link>
          </p>
          <p className="local-note">
            Local development preview · Use synthetic account details.
          </p>
        </section>
      </main>
      <footer className="public-footer">
        <span>WagaMaga AI</span>
        <span>Rooted in care. Built for growth.</span>
      </footer>
    </div>
  )
}
