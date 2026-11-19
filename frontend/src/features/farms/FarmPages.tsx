import { useState, type FormEvent } from 'react'
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router'
import ConfirmDialog from '../../components/ConfirmDialog'
import Notice from '../../components/Notice'
import Field from '../../components/Field'
import type { Cultivation, Farm, FarmDeleted, Page } from '../../lib/farms'
import { area, farmWrite } from '../../lib/farms'
import {
  Archived,
  CultivationForm,
  FarmForm,
  Intro,
  Pagination,
  ReadState,
  SaveError,
  ScopeNote,
} from './RecordUI'
import { useRecord, useSave } from './record-hooks'

export default function FarmsPage() {
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  return (
    <>
      {location.state?.farmDeleted === true && (
        <Notice
          success
          message="Farm deleted from your workspace. Historical records are retained; restoring a deleted farm is not available."
        />
      )}
      <FarmsList key={params.toString()} params={params} change={setParams} />
    </>
  )
}
function FarmsList({
  params,
  change,
}: {
  params: URLSearchParams
  change: (next: URLSearchParams) => void
}) {
  const [search, setSearch] = useState(params.get('q') ?? '')
  const status = ['active', 'archived', 'all'].includes(
    params.get('status') ?? '',
  )
    ? params.get('status')!
    : 'active'
  const page = Math.max(1, Math.min(10000, Number(params.get('page')) || 1))
  const query = new URLSearchParams({
    status,
    page: String(page),
    q: params.get('q') ?? '',
  })
  const records = useRecord<Page<Farm>>(`/farms?${query}`)
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params)
    next.set(key, value)
    if (key !== 'page') next.delete('page')
    change(next)
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    filter('q', search.trim())
  }
  return (
    <div className="farm-records">
      <Intro eyebrow="Your workspace / Farm records" title="My Farms">
        A place for your fields, cultivations and everyday observations.
      </Intro>
      <section className="record-welcome">
        <div>
          <span className="eyebrow">Your growing ground</span>
          <h2>Keep the details that matter.</h2>
          <p>
            Start with a farm. Add what you know, and leave the rest unknown.
          </p>
        </div>
        <Link className="primary record-link" to="/farms/new">
          Add farm <span aria-hidden="true">＋</span>
        </Link>
      </section>
      <section className="panel" aria-labelledby="farms-heading">
        <div className="title-row">
          <h2 id="farms-heading">Your farm records</h2>
          <span className="count-label">
            {records.data?.total ?? '—'}{' '}
            {records.data?.total === 1 ? 'farm' : 'farms'}
          </span>
        </div>
        <div className="record-filters">
          <form className="search-form" onSubmit={submit}>
            <label className="visually-hidden" htmlFor="farm-search">
              Search farms
            </label>
            <input
              id="farm-search"
              type="search"
              maxLength={100}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Find a farm by name"
            />
            <button>Search</button>
          </form>
          <label className="filter-label">
            Farm status
            <select
              value={status}
              onChange={(e) => filter('status', e.target.value)}
            >
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="all">All records</option>
            </select>
          </label>
        </div>
        {!records.data ? (
          <ReadState
            loading={records.loading}
            error={records.error}
            retry={records.reload}
          />
        ) : (
          <>
            {records.data.items.length === 0 ? (
              <div className="empty-state">
                <h3>No farms here yet.</h3>
                <p>
                  {status === 'active' && !search
                    ? 'Add your first farm to begin keeping records.'
                    : 'Try another search or status filter.'}
                </p>
              </div>
            ) : (
              <ul className="farm-cards">
                {records.data.items.map((farm) => (
                  <li key={farm.id}>
                    <div className="record-card-top">
                      <span
                        className={`status-pill ${farm.effective_archived ? 'disabled' : ''}`}
                      >
                        {farm.effective_archived ? 'Archived' : 'Active'}
                      </span>
                      <span className="record-area">
                        {area(farm.area_value, farm.area_unit)}
                      </span>
                    </div>
                    <h3>
                      <Link to={`/farms/${farm.id}`}>{farm.name}</Link>
                    </h3>
                    <p>{farm.location}</p>
                    <Link className="record-link" to={`/farms/${farm.id}`}>
                      Open farm <span aria-hidden="true">↗</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <Pagination
              result={records.data}
              page={page}
              change={(value) => filter('page', String(value))}
            />
          </>
        )}
      </section>
      <ScopeNote />
      <p className="record-footnote">
        Only your account can open these records. Archive keeps their history
        available.
      </p>
    </div>
  )
}

export function NewFarmPage() {
  const navigate = useNavigate()
  return (
    <div className="farm-records">
      <Link className="back-link" to="/farms">
        ← My Farms
      </Link>
      <Intro eyebrow="Farm records / New farm" title="A new beginning">
        Step 1: give your farm a name and location. Add what you are growing
        next.
      </Intro>
      <section className="panel record-editor">
        <h2>Farm details</h2>
        <FarmForm
          saved={(record) => navigate(`/farms/${record.id}`)}
          review="/farms"
        />
      </section>
    </div>
  )
}

export function FarmDetailPage() {
  const { farmId = '' } = useParams()
  return <FarmDetail key={farmId} id={farmId} />
}
function FarmDetail({ id }: { id: string }) {
  const navigate = useNavigate()
  const resource = useRecord<Farm>(`/farms/${id}`)
  const [editing, setEditing] = useState(false)
  const [editorBusy, setEditorBusy] = useState(false)
  const [archive, setArchive] = useState(false)
  const [action, setAction] = useState<'restore' | 'delete' | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const [notice, setNotice] = useState('')
  const save = useSave()
  function reload() {
    setEditing(false)
    setNotice('')
    setArchive(false)
    setAction(null)
    setConfirmation('')
    save.reset()
    resource.reload()
  }
  if (!resource.data)
    return (
      <ReadState
        loading={resource.loading}
        error={resource.error}
        retry={reload}
      />
    )
  const farm = resource.data
  return (
    <div className="farm-records">
      <Link className="back-link" to="/farms">
        ← My Farms
      </Link>
      <Intro eyebrow="Farm records / Farm details" title={farm.name}>
        {farm.location}
      </Intro>
      {notice && <Notice success message={notice} />}
      {farm.effective_archived && <Archived />}
      {farm.effective_archived && (
        <p className="record-scope">
          Find archived farms in My Farms → Farm status → Archived. Restore this
          farm to use it again, or delete it from your workspace. Deletion
          retains historical records and cannot be undone here.
        </p>
      )}
      <div className="record-toolbar">
        <span
          className={`status-pill ${farm.effective_archived ? 'disabled' : ''}`}
        >
          {farm.effective_archived ? 'Archived' : 'Active farm'}
        </span>
        <Link to={`/farms/${id}/history`}>Farm history</Link>
        {farm.effective_archived && (
          <>
            <button
              disabled={save.busy || save.blocked}
              onClick={() => setAction('restore')}
            >
              Restore farm
            </button>
            <button
              className="danger-action"
              disabled={save.busy || save.blocked}
              onClick={() => {
                setConfirmation('')
                setAction('delete')
              }}
            >
              Delete farm
            </button>
          </>
        )}
        {!farm.effective_archived && (
          <>
            <button
              onClick={() => setEditing(!editing)}
              disabled={save.busy || editorBusy}
            >
              {editing ? 'Cancel editing' : 'Edit farm'}
            </button>
            <button
              className="danger-action"
              disabled={save.busy || save.blocked || editing}
              onClick={() => setArchive(true)}
            >
              Archive farm
            </button>
          </>
        )}
      </div>
      {!archive && !action && <SaveError {...save} review={reload} />}
      {editing && !farm.effective_archived ? (
        <section className="panel record-editor">
          <h2>Edit farm details</h2>
          <FarmForm
            record={farm}
            onBusy={setEditorBusy}
            saved={(next) => {
              resource.replace(next)
              setEditing(false)
              setNotice('Farm details saved.')
            }}
            review={reload}
          />
        </section>
      ) : (
        <section className="panel record-summary" aria-label="Farm details">
          <dl>
            <div>
              <dt>Location</dt>
              <dd>{farm.location}</dd>
            </div>
            <div>
              <dt>Farm area</dt>
              <dd>{area(farm.area_value, farm.area_unit)}</dd>
            </div>
            <div>
              <dt>Timezone</dt>
              <dd>{farm.timezone}</dd>
            </div>
            <div>
              <dt>Coordinates</dt>
              <dd>
                {farm.latitude !== null
                  ? `${farm.latitude}, ${farm.longitude}`
                  : 'Not recorded'}
              </dd>
            </div>
          </dl>
        </section>
      )}
      <Cultivations key={`${farm.id}:${farm.version}`} farm={farm} />
      {archive && (
        <ConfirmDialog
          title="Archive this farm?"
          eyebrow="Farm records / Archive"
          description={`Archive ${farm.name}? Its cultivations and observations become read-only. Find it in My Farms under Archived. You can restore this farm later; its history stays available.`}
          busy={save.busy}
          confirmDisabled={save.blocked}
          error={save.error}
          confirmLabel="Archive farm"
          onClose={() => setArchive(false)}
          onConfirm={() =>
            void save.run(
              () =>
                farmWrite<Farm>(`/farms/${id}/archive`, 'POST', {
                  expected_version: farm.version,
                }),
              (next) => {
                resource.replace(next)
                setEditing(false)
                setArchive(false)
                setNotice('Farm archived. Its history remains available.')
              },
            )
          }
        />
      )}
      {action && (
        <ConfirmDialog
          title={
            action === 'restore'
              ? 'Restore this farm?'
              : 'Delete this farm from your workspace?'
          }
          eyebrow="Farm records / Lifecycle"
          description={
            action === 'restore'
              ? `Restore ${farm.name} to active farms? Crops archived only through this farm become editable again. Separately archived crops stay archived.`
              : `Delete ${farm.name}? It and its crops, observations and history will no longer be accessible in your workspace. Historical records are retained in storage. This does not erase data permanently, and restoring a deleted farm is not available.`
          }
          busy={save.busy}
          confirmDisabled={
            save.blocked ||
            (action === 'delete' && confirmation.trim() !== farm.name)
          }
          error={save.error}
          confirmLabel={action === 'restore' ? 'Restore farm' : 'Delete farm'}
          onClose={() => setAction(null)}
          onConfirm={() => {
            if (action === 'delete' && confirmation.trim() !== farm.name) return
            const operation = action
            void save.run(
              () =>
                farmWrite<Farm | FarmDeleted>(
                  `/farms/${id}/${operation}`,
                  'POST',
                  {
                    expected_version: farm.version,
                    ...(operation === 'delete'
                      ? { confirmation_name: confirmation.trim() }
                      : {}),
                  },
                ),
              (next) => {
                setAction(null)
                if ('deleted' in next)
                  navigate('/farms?status=archived', {
                    replace: true,
                    state: { farmDeleted: true },
                  })
                else {
                  resource.replace(next)
                  setNotice(
                    'Farm restored. Separately archived crops remain archived.',
                  )
                }
              },
            )
          }}
        >
          {action === 'delete' && (
            <Field
              label="Type the farm name to confirm"
              hint={farm.name}
              value={confirmation}
              maxLength={120}
              disabled={save.busy || save.blocked}
              onChange={(event) => setConfirmation(event.target.value)}
            />
          )}
        </ConfirmDialog>
      )}
    </div>
  )
}

function Cultivations({ farm }: { farm: Farm }) {
  const [status, setStatus] = useState(
    farm.effective_archived ? 'archived' : 'active',
  )
  const [page, setPage] = useState(1)
  const records = useRecord<Page<Cultivation>>(
    `/farms/${farm.id}/cultivations?status=${status}&page=${page}`,
  )
  return (
    <section className="panel" aria-labelledby="cultivations-heading">
      <div className="title-row">
        <div>
          <p className="eyebrow">Growing here</p>
          <h2 id="cultivations-heading">What you are growing</h2>
          <p className="muted">
            Each crop and planting date makes one cultivation record.
          </p>
        </div>
        {!farm.effective_archived && (
          <Link
            className="primary record-link"
            to={`/farms/${farm.id}/cultivations/new`}
          >
            Add what you are growing
          </Link>
        )}
      </div>
      <label className="filter-label">
        Cultivation status
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
        >
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="all">All records</option>
        </select>
      </label>
      {!records.data ? (
        <ReadState
          loading={records.loading}
          error={records.error}
          retry={records.reload}
        />
      ) : (
        <>
          {!records.data.items.length ? (
            <div className="empty-state">
              <h3>No crop records to show.</h3>
              <p>
                {status === 'active' && !farm.effective_archived
                  ? 'Next step: use “Add what you are growing” to record your crop, planting date and planted area.'
                  : 'Choose another status filter to find earlier records.'}
              </p>
            </div>
          ) : (
            <ul className="record-rows">
              {records.data.items.map((record) => (
                <li key={record.id}>
                  <div>
                    <span
                      className={`status-pill ${record.effective_archived ? 'disabled' : ''}`}
                    >
                      {record.effective_archived
                        ? 'Archived'
                        : record.planned
                          ? 'Planned'
                          : 'Active'}
                    </span>
                    <h3>
                      <Link to={`/farms/${farm.id}/cultivations/${record.id}`}>
                        Cultivation · {record.planting_date}
                      </Link>
                    </h3>
                    <p>
                      {area(record.area_value, record.area_unit)} ·{' '}
                      {record.confirmed_stage ?? 'Stage not confirmed'}
                    </p>
                  </div>
                  <Link
                    className="record-link"
                    aria-label={`Open cultivation planted ${record.planting_date}`}
                    to={`/farms/${farm.id}/cultivations/${record.id}`}
                  >
                    Open <span aria-hidden="true">↗</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Pagination result={records.data} page={page} change={setPage} />
        </>
      )}
    </section>
  )
}

export function NewCultivationPage() {
  const { farmId = '' } = useParams()
  return <NewCultivation key={farmId} id={farmId} />
}
function NewCultivation({ id }: { id: string }) {
  const resource = useRecord<Farm>(`/farms/${id}`)
  const navigate = useNavigate()
  if (!resource.data)
    return (
      <ReadState
        loading={resource.loading}
        error={resource.error}
        retry={resource.reload}
      />
    )
  const farm = resource.data
  return (
    <div className="farm-records">
      <Link className="back-link" to={`/farms/${id}`}>
        ← {farm.name}
      </Link>
      <Intro eyebrow="Farm records / New cultivation" title="Make room to grow">
        Step 2: record a crop, planting date and planted area for {farm.name}.
        This is your cultivation record.
      </Intro>
      {farm.effective_archived ? (
        <Archived />
      ) : (
        <section className="panel record-editor">
          <h2>Cultivation details</h2>
          <CultivationForm
            farm={farm}
            saved={(record) =>
              navigate(`/farms/${id}/cultivations/${record.id}?observe=1`)
            }
            review={`/farms/${id}`}
          />
        </section>
      )}
    </div>
  )
}
