import { useState, type FormEvent } from 'react'
import { useSession } from '../../app/session-context'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import { ApiError, request, type Account } from '../../lib/accounts'
import {
  isSignupPasswordValid,
  PASSWORD_REQUIREMENTS,
} from '../../lib/password-policy'

export default function AccountPage() {
  const { user, setUser } = useSession()
  const [name, setName] = useState(user?.display_name ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordSaved, setPasswordSaved] = useState(false)
  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setSaved(false)
    try {
      setUser(
        await request<Account>('/me', {
          method: 'PATCH',
          body: JSON.stringify({
            display_name: name,
            expected_version: user?.version,
          }),
        }),
      )
      setSaved(true)
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        try {
          const latest = await request<Account>('/me')
          setUser(latest)
          setName(latest.display_name)
        } catch {
          /* Preserve the original error. */
        }
      }
      setError(
        failure instanceof Error
          ? failure.message
          : 'Could not save your profile.',
      )
    } finally {
      setBusy(false)
    }
  }
  async function changePassword(event: FormEvent) {
    event.preventDefault()
    setPasswordError('')
    setPasswordSaved(false)
    if (newPassword !== confirmPassword) {
      setPasswordError('The new passwords do not match.')
      return
    }
    if (!isSignupPasswordValid(newPassword)) {
      setPasswordError(PASSWORD_REQUIREMENTS)
      return
    }
    setPasswordBusy(true)
    try {
      setUser(
        await request<Account>('/me/password', {
          method: 'POST',
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        }),
      )
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordSaved(true)
      window.dispatchEvent(new Event('notifications-updated'))
    } catch (failure) {
      setPasswordError(
        failure instanceof Error
          ? failure.message
          : 'Could not change your password.',
      )
    } finally {
      setPasswordBusy(false)
    }
  }
  if (!user) return null
  return (
    <>
      <div className="page-intro">
        <p className="eyebrow">Your space</p>
        <h1>
          My account<span>.</span>
        </h1>
        <p>Keep your details up to date. Make yourself at home.</p>
      </div>
      <div className="account-columns">
        <section
          className="panel profile-panel"
          aria-labelledby="profile-title"
        >
          <div className="panel-title">
            <div>
              <span className="section-number">01 / Profile</span>
              <h2 id="profile-title">A name to grow with.</h2>
            </div>
            <span className="profile-monogram" aria-hidden="true">
              {user.display_name.slice(0, 1)}
            </span>
          </div>
          {error && <Notice message={error} />}
          {saved && (
            <Notice success message="Your display name has been saved." />
          )}
          <form onSubmit={save}>
            <Field
              label="Display name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              required
              minLength={2}
              maxLength={80}
              hint="This is how your name appears in WagaMaga."
            />
            <Field
              label="Email address"
              value={user.email}
              type="email"
              readOnly
              hint="Your sign-in email. Email changes are not available yet."
            />
            <div className="form-actions">
              <button className="primary" disabled={busy}>
                {busy ? 'Saving…' : 'Save changes'}{' '}
                <span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>
        </section>
        <aside className="account-notes">
          <section
            className="panel profile-panel"
            aria-labelledby="password-title"
          >
            <div className="panel-title">
              <div>
                <span className="section-number">02 / Security</span>
                <h2 id="password-title">Change your password.</h2>
              </div>
            </div>
            {passwordError && <Notice message={passwordError} />}
            {passwordSaved && (
              <Notice
                success
                message="Password changed. Other sessions have been signed out."
              />
            )}
            <form onSubmit={changePassword}>
              <Field
                label="Current password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
                maxLength={128}
              />
              <Field
                label="New password"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                minLength={8}
                maxLength={128}
                hint={PASSWORD_REQUIREMENTS}
              />
              <Field
                label="Confirm new password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={8}
                maxLength={128}
              />
              <div className="form-actions">
                <button className="primary" disabled={passwordBusy}>
                  {passwordBusy ? 'Changing…' : 'Change password'}
                </button>
              </div>
            </form>
          </section>
          <section className="panel">
            <span className="section-number">Account overview</span>
            <dl className="account-details">
              <div>
                <dt>Role</dt>
                <dd>
                  <span className="role-badge">{user.role}</span>
                </dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <span className="status-pill">Active</span>
                </dd>
              </div>
              <div>
                <dt>Joined</dt>
                <dd>
                  {new Intl.DateTimeFormat('en', {
                    dateStyle: 'medium',
                    timeZone: 'Asia/Colombo',
                  }).format(new Date(user.created_at))}
                </dd>
              </div>
            </dl>
          </section>
          <section className="gentle-note">
            <span aria-hidden="true">✳</span>
            <h2>Your account. Your space.</h2>
            <p>
              Your role determines the account tools available to you. Account
              management never grants access to someone else’s private farming
              records.
            </p>
          </section>
        </aside>
      </div>
    </>
  )
}
