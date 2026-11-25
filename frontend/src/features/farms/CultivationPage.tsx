import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { useSession } from '../../app/session-context'
import Field from '../../components/Field'
import Notice from '../../components/Notice'
import ConfirmDialog from '../../components/ConfirmDialog'
import type {
  Crop,
  Cultivation,
  Farm,
  Observation,
  Page,
  SoilMoisture,
} from '../../lib/farms'
import { area, cropName, farmWrite, timestamp } from '../../lib/farms'
import {
  Archived,
  CultivationForm,
  Intro,
  Pagination,
  ReadState,
  SaveError,
  TextArea,
} from './RecordUI'
import CultivationGuidance from './CultivationGuidance'
import ChilliPdfChat from './ChilliPdfChat'
import ReviewedSources from './ReviewedSources'
import { useRecord, useSave } from './record-hooks'
import TaskPanel from './TaskPanel'

export default function CultivationPage() {
  const { farmId = '', cultivationId = '' } = useParams()
  return (
    <CultivationDetail
      key={`${farmId}:${cultivationId}`}
      farmId={farmId}
      id={cultivationId}
    />
  )
}
function CultivationDetail({ farmId, id }: { farmId: string; id: string }) {
  const { user } = useSession()
  const [params] = useSearchParams()
  const startObservation = params.get('observe') === '1'
  const farm = useRecord<Farm>(`/farms/${farmId}`)
  const path = `/farms/${farmId}/cultivations/${id}`
  const record = useRecord<Cultivation>(path)
  const crops = useRecord<Page<Crop>>('/crop-types?page_size=100')
  const [editing, setEditing] = useState(false)
  const [editorBusy, setEditorBusy] = useState(false)
  const [observationDraft, setObservationDraft] = useState(startObservation)
  const [archive, setArchive] = useState(false)
  const [stage, setStage] = useState('')
  const [notice, setNotice] = useState('')
  const [guidanceRevision, setGuidanceRevision] = useState(0)
  const save = useSave()
  function reload() {
    setEditing(false)
    setArchive(false)
    setStage('')
    setNotice('')
    setObservationDraft(false)
    setGuidanceRevision((revision) => revision + 1)
    save.reset()
    farm.reload()
    record.reload()
  }
  const error = farm.error ?? record.error
  if (error || !farm.data || !record.data)
    return (
      <ReadState
        loading={!error && (farm.loading || record.loading)}
        error={error}
        retry={reload}
      />
    )
  const cultivation = record.data
  const isChilli = crops.data?.items.some(
    (crop) => crop.id === cultivation.crop_type_id && crop.code === 'chilli',
  )
  function saved(next: Cultivation) {
    record.replace(next)
    setEditing(false)
    setStage('')
    setNotice('Cultivation record saved.')
  }
  function confirm(event: FormEvent) {
    event.preventDefault()
    if (!stage.trim()) return
    void save.run(
      () =>
        farmWrite<Cultivation>(path + '/stage-confirmation', 'POST', {
          expected_version: cultivation.version,
          stage: stage.trim(),
        }),
      saved,
    )
  }
  return (
    <div className="farm-records">
      <Link className="back-link" to={`/farms/${farmId}`}>
        ← {farm.data.name}
      </Link>
      <Intro
        eyebrow="Farm records / Cultivation details"
        title={cropName(cultivation.crop_type_id, crops.data?.items ?? [])}
      >
        {farm.data.name} · Planting date {cultivation.planting_date}
      </Intro>
      {isChilli && !cultivation.effective_archived && (
        <CultivationGuidance
          key={`${farm.data.version}:${cultivation.version}:${guidanceRevision}`}
          path={path + '/chilli-guidance'}
        />
      )}
      {notice && <Notice success message={notice} />}
      {cultivation.effective_archived && (
        <Archived inherited={!cultivation.archived_at} />
      )}
      <div className="record-toolbar">
        <span
          className={`status-pill ${cultivation.effective_archived ? 'disabled' : ''}`}
        >
          {cultivation.effective_archived
            ? 'Archived'
            : cultivation.planned
              ? 'Planned cultivation'
              : 'Active cultivation'}
        </span>
        <Link to={path + '/history'}>Cultivation history</Link>
        {!cultivation.effective_archived && (
          <>
            <button
              onClick={() => setEditing(!editing)}
              disabled={
                save.busy || editorBusy || observationDraft || Boolean(stage)
              }
            >
              {editing ? 'Cancel editing' : 'Edit cultivation'}
            </button>
            <button
              className="danger-action"
              disabled={
                save.busy ||
                save.blocked ||
                editing ||
                observationDraft ||
                Boolean(stage)
              }
              onClick={() => setArchive(true)}
            >
              Archive cultivation
            </button>
          </>
        )}
      </div>
      {!archive && <SaveError {...save} review={reload} />}
      {editing && !cultivation.effective_archived ? (
        <section className="panel record-editor">
          <h2>Edit cultivation</h2>
          <CultivationForm
            farm={farm.data}
            record={cultivation}
            onBusy={setEditorBusy}
            saved={saved}
            review={reload}
          />
        </section>
      ) : (
        <section
          className="panel record-summary"
          aria-label="Cultivation details"
        >
          <dl>
            <div>
              <dt>Planting date</dt>
              <dd>{cultivation.planting_date}</dd>
            </div>
            <div>
              <dt>Cultivation area</dt>
              <dd>{area(cultivation.area_value, cultivation.area_unit)}</dd>
            </div>
            <div>
              <dt>Soil information</dt>
              <dd className="record-note">
                {cultivation.soil_notes ?? 'Unknown'}
              </dd>
            </div>
            <div>
              <dt>Estimated stage</dt>
              <dd>
                {cultivation.estimated_stage ??
                  'Unknown — no estimate available'}
              </dd>
            </div>
          </dl>
        </section>
      )}
      <section className="panel" aria-labelledby="stage-heading">
        <p className="eyebrow">What you have observed</p>
        <h2 id="stage-heading">Reported crop stage</h2>
        <p className="record-note">
          {cultivation.confirmed_stage ?? 'Not confirmed'}
        </p>
        {cultivation.confirmed_at && (
          <p className="muted">
            Confirmed by{' '}
            {cultivation.confirmed_by === user?.id
              ? 'you'
              : 'the recorded account'}{' '}
            on {timestamp(cultivation.confirmed_at, farm.data.timezone)} ·{' '}
            {farm.data.timezone}
          </p>
        )}
        <p className="muted">
          A reported stage is your observation, not a recommendation to take an
          agricultural action.
        </p>
        {!cultivation.effective_archived && (
          <form onSubmit={confirm} className="record-stage-form">
            <Field
              label="Reported stage"
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              required
              maxLength={80}
              disabled={
                save.busy || save.blocked || editing || observationDraft
              }
              hint="Enter only a stage you can confirm from your own observation."
            />
            <button
              className="primary"
              disabled={
                save.busy || save.blocked || editing || observationDraft
              }
            >
              {save.busy ? 'Saving…' : 'Confirm stage'}
            </button>
            {stage && (
              <button
                type="button"
                disabled={save.busy}
                onClick={() => setStage('')}
              >
                Cancel stage entry
              </button>
            )}
          </form>
        )}
      </section>
      <ReviewedSources path={path} />
      {isChilli && (
        <ChilliPdfChat
          path={path}
          timezone={farm.data.timezone}
          archived={cultivation.effective_archived}
        />
      )}
      <TaskPanel
        path={path + '/tasks'}
        planPath={path + '/task-plans'}
        cultivationPath={path}
        farmPath={`/farms/${farmId}`}
        timezone={farm.data.timezone}
        archived={cultivation.effective_archived}
        chilli={isChilli}
        review={reload}
      />
      <Observations
        key={`${id}:${cultivation.version}`}
        farm={farm.data}
        cultivation={cultivation}
        canEdit={!editing && !stage && !save.busy && !save.blocked}
        onDraft={setObservationDraft}
        onSaved={() => setGuidanceRevision((revision) => revision + 1)}
        startAdding={startObservation && !cultivation.effective_archived}
      />
      {archive && (
        <ConfirmDialog
          eyebrow="Farm records / Archive"
          title="Archive this cultivation?"
          description="Its details, tasks and history will remain readable. New activity and changes will be disabled. Restoration is not available."
          busy={save.busy}
          confirmDisabled={save.blocked}
          error={save.error}
          confirmLabel="Archive cultivation"
          onClose={() => setArchive(false)}
          onConfirm={() =>
            void save.run(
              () =>
                farmWrite<Cultivation>(path + '/archive', 'POST', {
                  expected_version: cultivation.version,
                }),
              (next) => {
                record.replace(next)
                setEditing(false)
                setArchive(false)
                setNotice('Cultivation archived. History remains available.')
              },
            )
          }
        />
      )}
    </div>
  )
}

function Observations({
  farm,
  cultivation,
  canEdit,
  onDraft,
  onSaved,
  startAdding = false,
}: {
  farm: Farm
  cultivation: Cultivation
  canEdit: boolean
  onDraft: (open: boolean) => void
  onSaved: () => void
  startAdding?: boolean
}) {
  const [page, setPage] = useState(1)
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [editing, setEditing] = useState<Observation | null>(null)
  const [adding, setAdding] = useState(startAdding)
  const [, setParams] = useSearchParams()
  useEffect(() => {
    if (!startAdding) return
    document.getElementById('observations-heading')?.focus()
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous)
        next.delete('observe')
        return next
      },
      { replace: true },
    )
  }, [startAdding, setParams])
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const path = `/cultivations/${cultivation.id}/observations`
  const query = new URLSearchParams({ page: String(page) })
  if (from) query.set('from_date', from)
  if (to) query.set('to_date', to)
  const list = useRecord<Page<Observation>>(`${path}?${query}`)
  function review() {
    setAdding(false)
    setEditing(null)
    setNotice('')
    onDraft(false)
    list.reload()
  }
  return (
    <section className="panel" aria-labelledby="observations-heading">
      <div className="title-row">
        <div>
          <p className="eyebrow">Your field notebook</p>
          <h2 id="observations-heading" tabIndex={-1}>
            Observations
          </h2>
        </div>
        {!cultivation.effective_archived && !adding && !editing && (
          <button
            className="primary"
            disabled={!canEdit}
            onClick={() => {
              setNotice('')
              setAdding(true)
              onDraft(true)
            }}
          >
            Add observation
          </button>
        )}
      </div>
      {notice && <Notice success message={notice} />}
      {(adding || editing) && !cultivation.effective_archived && (
        <div className="record-inset">
          <h3>{editing ? 'Edit observation' : 'New observation'}</h3>
          <ObservationForm
            key={editing?.id ?? 'new'}
            record={editing ?? undefined}
            path={path}
            timezone={farm.timezone}
            review={review}
            onBusy={setBusy}
            saved={() => {
              setAdding(false)
              setEditing(null)
              onDraft(false)
              list.reload()
              onSaved()
              setNotice('Observation saved.')
            }}
          />
          <button
            className="record-cancel"
            disabled={busy}
            onClick={() => {
              setAdding(false)
              setEditing(null)
              onDraft(false)
            }}
          >
            Cancel observation editing
          </button>
        </div>
      )}
      <div className="record-filters">
        <Field
          label="From date (UTC)"
          type="date"
          value={from}
          onChange={(e) => {
            setFrom(e.target.value)
            setPage(1)
          }}
        />
        <Field
          label="To date (UTC)"
          type="date"
          value={to}
          onChange={(e) => {
            setTo(e.target.value)
            setPage(1)
          }}
        />
      </div>
      {from && to && from > to ? (
        <Notice message="The end date must be on or after the start date." />
      ) : !list.data ? (
        <ReadState
          loading={list.loading}
          error={list.error}
          retry={list.reload}
        />
      ) : (
        <>
          {!list.data.items.length ? (
            <div className="empty-state">
              <h3>No observations to show.</h3>
              <p>
                Keep a note of what you observe, without guessing unknown
                conditions.
              </p>
            </div>
          ) : (
            <ul className="record-observations">
              {list.data.items.map((item) => (
                <li key={item.id}>
                  <div className="record-card-top">
                    <h3>{timestamp(item.observed_at, farm.timezone)}</h3>
                    <span className="muted">{farm.timezone}</span>
                  </div>
                  <p className="record-note">{item.notes}</p>
                  {item.soil_moisture && (
                    <p>Soil moisture: {item.soil_moisture}</p>
                  )}
                  <div className="button-row">
                    {!cultivation.effective_archived && (
                      <button
                        aria-label={`Edit observation from ${timestamp(item.observed_at, farm.timezone)}`}
                        disabled={!canEdit || adding || Boolean(editing)}
                        onClick={() => {
                          setNotice('')
                          setEditing(item)
                          onDraft(true)
                        }}
                      >
                        Edit observation
                      </button>
                    )}
                    <Link
                      to={`/farms/${farm.id}/cultivations/${cultivation.id}/observations/${item.id}/history`}
                    >
                      Observation history
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <Pagination result={list.data} page={page} change={setPage} />
        </>
      )}
    </section>
  )
}

function deviceTime(value: string) {
  const d = new Date(value)
  const pad = (v: number) => String(v).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${String(d.getMilliseconds()).padStart(3, '0')}`
}
function ObservationForm({
  record,
  path,
  timezone,
  saved,
  review,
  onBusy,
}: {
  record?: Observation
  path: string
  timezone: string
  saved: () => void
  review: () => void
  onBusy: (busy: boolean) => void
}) {
  const initialTime = record ? deviceTime(record.observed_at) : ''
  const [observed, setObserved] = useState(initialTime)
  const [notes, setNotes] = useState(record?.notes ?? '')
  const [soilMoisture, setSoilMoisture] = useState<SoilMoisture | ''>(
    record?.soil_moisture ?? '',
  )
  const [invalid, setInvalid] = useState('')
  const save = useSave()
  function submit(event: FormEvent) {
    event.preventDefault()
    setInvalid('')
    const date = new Date(observed)
    if (
      !notes.trim() ||
      !observed ||
      !Number.isFinite(date.getTime()) ||
      date.getTime() > Date.now()
    ) {
      setInvalid(
        'Enter a note and a valid observation time that is not in the future.',
      )
      return
    }
    const instant =
      record && observed === initialTime
        ? record.observed_at
        : date.toISOString()
    const body = {
      observed_at: instant,
      notes: notes.trim(),
      ...(soilMoisture || record?.soil_moisture
        ? { soil_moisture: soilMoisture || null }
        : {}),
      ...(record ? { expected_version: record.version } : {}),
    }
    onBusy(true)
    void save
      .run(
        () =>
          farmWrite<Observation>(
            record ? `${path}/${record.id}` : path,
            record ? 'PATCH' : 'POST',
            body,
          ),
        saved,
      )
      .finally(() => onBusy(false))
  }
  return (
    <form onSubmit={submit} className="record-form">
      <fieldset disabled={save.busy || save.blocked}>
        <legend className="visually-hidden">Observation details</legend>
        <Field
          label="Observed at (device time)"
          type="datetime-local"
          step="0.001"
          value={observed}
          onChange={(e) => setObserved(e.target.value)}
          required
          hint={`Using ${Intl.DateTimeFormat().resolvedOptions().timeZone} on this device. Saved notes are displayed in ${timezone}.`}
        />
        <button
          type="button"
          onClick={() => setObserved(deviceTime(new Date().toISOString()))}
        >
          Use current time
        </button>
        <TextArea
          label="Observation notes"
          required
          value={notes}
          change={setNotes}
          maxLength={4000}
        />
        <div className="field">
          <label htmlFor="observation-soil-moisture">
            Soil moisture (optional)
          </label>
          <select
            id="observation-soil-moisture"
            value={soilMoisture}
            onChange={(event) =>
              setSoilMoisture(event.target.value as SoilMoisture | '')
            }
          >
            <option value="">Not recorded</option>
            <option value="dry">Dry</option>
            <option value="moist">Moist</option>
            <option value="waterlogged">Waterlogged</option>
          </select>
        </div>
        {invalid && <Notice message={invalid} />}
        <button className="primary" disabled={save.busy || save.blocked}>
          {save.busy
            ? 'Saving…'
            : record
              ? 'Save observation'
              : 'Record observation'}
        </button>
      </fieldset>
      <SaveError {...save} review={review} create={!record} />
    </form>
  )
}
