import { Link } from 'react-router'
import Notice from '../../components/Notice'
import { ApiError } from '../../lib/accounts'
import { Intro } from '../farms/RecordUI'
import { useRecord } from '../farms/record-hooks'
import './reporting.css'

export type RecordCounts = { total: number; active: number; archived: number }
export type Overview = {
  generated_at: string
  accounts: {
    total: number
    enabled: number
    disabled: number
    farmers: number
    advisors: number
    administrators: number
    new_farmers_30_days: number
    removed: number
  }
  farms: RecordCounts
  cultivations: RecordCounts
  support: {
    total: number
    open: number
    in_progress: number
    resolved: number
  }
}
export type FarmerSummary = {
  user_id: string
  generated_at: string
  farms: RecordCounts
  cultivations: RecordCounts
}

function Snapshot({ value }: { value: string }) {
  return (
    <p className="record-footnote">
      Snapshot{' '}
      {new Intl.DateTimeFormat('en-GB', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(value))}{' '}
      · Your device timezone
    </p>
  )
}
function Failure({ error, retry }: { error: unknown; retry: () => void }) {
  const denied = error instanceof ApiError && [403, 404].includes(error.status)
  return (
    <div>
      <Notice
        message={
          denied
            ? 'This summary is unavailable or your account cannot access it.'
            : 'The summary could not be loaded. No counts are shown. Try again.'
        }
      />
      {!denied && <button onClick={retry}>Try again</button>}
    </div>
  )
}
function Counts({ data, label }: { data: RecordCounts; label: string }) {
  return (
    <div>
      <h3>{label}</h3>
      <dl className="report-counts">
        <div>
          <dt>Total</dt>
          <dd>{data.total}</dd>
        </div>
        <div>
          <dt>Active records</dt>
          <dd>{data.active}</dd>
        </div>
        <div>
          <dt>Archived records</dt>
          <dd>{data.archived}</dd>
        </div>
      </dl>
    </div>
  )
}

export default function OverviewPage() {
  const report = useRecord<Overview>('/admin/overview')
  const data = report.data
  return (
    <div className="farm-records report-page">
      <Intro eyebrow="Administration / Overview" title="Admin Overview">
        A clear view of accounts, record counts and support requests. Private
        farm details stay private.
      </Intro>
      <div className="record-toolbar">
        <Link to="/admin/users?role=farmer">Manage farmers</Link>
        <Link to="/admin/support">Review support requests</Link>
        <button onClick={report.reload} disabled={report.loading}>
          Refresh overview
        </button>
      </div>
      {!data ? (
        report.loading ? (
          <p role="status">Loading administration summary…</p>
        ) : (
          <Failure error={report.error} retry={report.reload} />
        )
      ) : (
        <>
          <section
            className="report-highlights"
            aria-label="Administration summary"
          >
            <article>
              <p>Farmer accounts</p>
              <strong>{data.accounts.farmers}</strong>
              <span>
                {data.accounts.new_farmers_30_days} new in the last 30 days
              </span>
            </article>
            <article>
              <p>Farm records</p>
              <strong>{data.farms.total}</strong>
              <span>
                {data.farms.active} active · {data.farms.archived} archived
              </span>
            </article>
            <article>
              <p>Cultivation records</p>
              <strong>{data.cultivations.total}</strong>
              <span>
                {data.cultivations.active} active · {data.cultivations.archived}{' '}
                archived
              </span>
            </article>
            <article>
              <p>Support to review</p>
              <strong>{data.support.open + data.support.in_progress}</strong>
              <span>
                {data.support.open} open · {data.support.in_progress} in
                progress
              </span>
            </article>
          </section>
          <section className="panel" aria-labelledby="report-accounts">
            <div className="title-row">
              <h2 id="report-accounts">Accounts</h2>
              <Link to="/admin/users">Manage accounts</Link>
            </div>
            <dl className="report-facts">
              {Object.entries({
                'Current accounts': data.accounts.total,
                'Enabled accounts': data.accounts.enabled,
                'Disabled accounts': data.accounts.disabled,
                'Farmer accounts': data.accounts.farmers,
                'Advisor accounts': data.accounts.advisors,
                'Administrator accounts': data.accounts.administrators,
                'Removed accounts': data.accounts.removed,
              }).map(([label, count]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>
            <p className="muted">
              Current account and role totals exclude removed accounts. Enabled
              means access is allowed; it does not measure recent website use.
            </p>
          </section>
          <section className="panel" aria-labelledby="report-records">
            <h2 id="report-records">Farm and cultivation totals</h2>
            <div className="report-record-groups">
              <Counts label="Farms" data={data.farms} />
              <Counts label="Cultivations" data={data.cultivations} />
            </div>
            <p className="muted">
              These counts belong to current farmer accounts, including disabled
              accounts. Workspace-deleted farms, their crops and
              removed/former-farmer accounts are excluded. A crop is archived
              when it or its farm is archived.
            </p>
          </section>
          <section className="panel" aria-labelledby="report-support">
            <div className="title-row">
              <h2 id="report-support">Website support</h2>
              <Link to="/admin/support">Review the inbox</Link>
            </div>
            <dl className="report-facts">
              {Object.entries({
                'All submitted requests': data.support.total,
                'Open requests': data.support.open,
                'In progress': data.support.in_progress,
                'Resolved requests': data.support.resolved,
              }).map(([label, count]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>
            <p className="muted">
              Support totals include retained submitted requests, even when a
              requester account is unavailable.
            </p>
          </section>
          <Snapshot value={data.generated_at} />
          <p className="record-scope">
            Reports show counts only. They do not provide farm names,
            coordinates, field notes, conversations or permission to act for a
            farmer. Report views are recorded in administrative audit history.
          </p>
        </>
      )}
    </div>
  )
}

export function FarmerRecordSummary({ userId }: { userId: string }) {
  const report = useRecord<FarmerSummary>(`/admin/users/${userId}/farm-summary`)
  return (
    <section
      className="panel report-page"
      aria-labelledby="farmer-record-summary"
    >
      <h2 id="farmer-record-summary">Farm record summary</h2>
      {!report.data ? (
        report.loading ? (
          <p role="status">Loading farmer record counts…</p>
        ) : (
          <Failure error={report.error} retry={report.reload} />
        )
      ) : (
        <>
          <div className="report-record-groups">
            <Counts label="Farms" data={report.data.farms} />
            <Counts label="Cultivations" data={report.data.cultivations} />
          </div>
          <Snapshot value={report.data.generated_at} />
        </>
      )}
      <p className="muted">
        Counts only. Farm names, locations and field notes remain private.
        Workspace-deleted farms and their crops are excluded; crops archived
        through their farm count as archived.
      </p>
    </section>
  )
}
