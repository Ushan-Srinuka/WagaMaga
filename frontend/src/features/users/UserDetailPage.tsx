import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useSession } from '../../app/session-context'
import ConfirmDialog from '../../components/ConfirmDialog'
import Notice from '../../components/Notice'
import { ApiError, request, type Account, type Role } from '../../lib/accounts'

export default function UserDetailPage() {
  const { id } = useParams()
  const { user } = useSession()
  const navigate = useNavigate()
  const [account, setAccount] = useState<Account | null>(null)
  const [role, setRole] = useState<Role>('farmer')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [retry, setRetry] = useState(0)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<'role' | 'status' | 'delete' | null>(
    null,
  )
  useEffect(() => {
    let cancelled = false
    void request<Account>(`/admin/users/${id}`)
      .then((result) => {
        if (!cancelled) {
          setAccount(result)
          setRole(result.role)
        }
      })
      .catch((failure) => {
        if (!cancelled)
          setError(
            failure instanceof Error
              ? failure.message
              : 'Account could not be loaded.',
          )
      })
    return () => {
      cancelled = true
    }
  }, [id, retry])
  function propose(event: FormEvent) {
    event.preventDefault()
    setError('')
    setNotice('')
    setPending('role')
  }
  async function confirm() {
    if (!account || !pending) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      if (pending === 'delete') {
        await request<Account>(`/admin/users/${account.id}`, {
          method: 'DELETE',
          body: JSON.stringify({ reason, expected_version: account.version }),
        })
        navigate('/admin/users?status=deleted')
        return
      }
      const next = await request<Account>(
        `/admin/users/${account.id}/${pending}`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            reason,
            expected_version: account.version,
            ...(pending === 'role'
              ? { role }
              : { enabled: Boolean(account.disabled_at) }),
          }),
        },
      )
      setAccount(next)
      setRole(next.role)
      setReason('')
      setPending(null)
      setNotice('Account updated. Any affected sessions have been revoked.')
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        setPending(null)
        setRetry(retry + 1)
      }
      setError(
        failure instanceof Error
          ? failure.message
          : 'The account could not be updated.',
      )
    } finally {
      setBusy(false)
    }
  }
  if (!account)
    return (
      <>
        <Link to="/admin/users">← All accounts</Link>
        {error ? (
          <>
            <Notice message={error} />
            <button
              onClick={() => {
                setError('')
                setRetry(retry + 1)
              }}
            >
              Try again
            </button>
          </>
        ) : (
          <p role="status">Loading account…</p>
        )}
      </>
    )
  const self = account.id === user?.id
  return (
    <>
      <Link className="back-link" to="/admin/users">
        ← All accounts
      </Link>
      <div className="page-intro">
        <p className="eyebrow">Administration / Account details</p>
        <h1>
          {account.display_name}
          <span>.</span>
        </h1>
        <p>{account.email}</p>
      </div>
      {notice && <Notice success message={notice} />}
      {error && !pending && <Notice message={error} />}
      {account.deleted_at && (
        <Notice message="This account has been removed. Its sign-in details were erased and its administrative history was retained." />
      )}
      <section
        className="panel account-management"
        aria-labelledby="access-title"
      >
        <span className="section-number">Access & accountability</span>
        <h2 id="access-title">The right tools for their role.</h2>
        <div className="button-row">
          <span className="role-badge">{account.role}</span>
          <span
            className={`status-pill ${account.disabled_at ? 'disabled' : ''}`}
          >
            {account.deleted_at
              ? 'Deleted'
              : account.disabled_at
                ? 'Disabled'
                : 'Active'}
          </span>
        </div>
        {self && (
          <p className="form-notice">
            This is your account. Ask another administrator to change your role
            or status.
          </p>
        )}
        {!account.deleted_at && (
          <form onSubmit={propose}>
            <div className="field">
              <label htmlFor="account-role">Account role</label>
              <select
                id="account-role"
                value={role}
                disabled={self || busy}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                <option value="farmer">Farmer</option>
                <option value="advisor">Advisor</option>
                <option value="administrator">Administrator</option>
              </select>
              <small>
                Role assignment gives account permissions, not proof of
                professional qualification.
              </small>
            </div>
            <div className="field">
              <label htmlFor="change-reason">Reason for change</label>
              <textarea
                id="change-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                minLength={3}
                maxLength={300}
                disabled={self || busy}
                rows={3}
              />
              <small>
                Required for the audit record. Include no passwords or private
                farming information.
              </small>
            </div>
            <div className="button-row">
              <button
                className="primary"
                disabled={self || busy || role === account.role}
              >
                Review role change
              </button>
              <button
                type="button"
                className={account.disabled_at ? '' : 'danger-button'}
                disabled={self || busy || reason.trim().length < 3}
                onClick={() => {
                  setError('')
                  setNotice('')
                  setPending('status')
                }}
              >
                {account.disabled_at ? 'Re-enable account' : 'Disable account'}
              </button>
              <button
                type="button"
                className="danger-button"
                disabled={self || busy || reason.trim().length < 3}
                onClick={() => {
                  setError('')
                  setNotice('')
                  setPending('delete')
                }}
              >
                Remove account
              </button>
            </div>
          </form>
        )}
        <p className="page-footnote">
          Changes are recorded. Role changes and disablement end existing
          sessions. Re-enabling an account requires a fresh sign-in.
        </p>
      </section>
      {pending && (
        <ConfirmDialog
          title={
            pending === 'role'
              ? `Change role to ${role}?`
              : pending === 'delete'
                ? 'Permanently remove this account?'
                : account.disabled_at
                  ? 'Re-enable this account?'
                  : 'Disable this account?'
          }
          description={`${account.display_name} (${account.email}). ${pending === 'delete' ? 'Sign-in access and identity details will be erased permanently. The account history remains for audit. This cannot be undone.' : pending === 'role' ? 'Existing sessions will end.' : account.disabled_at ? 'They can sign in again. Old sessions stay revoked.' : 'They will be signed out and unable to sign in.'} This action will be recorded.`}
          busy={busy}
          error={error}
          onConfirm={() => {
            void confirm()
          }}
          onClose={() => {
            setPending(null)
            setError('')
          }}
        />
      )}
    </>
  )
}
