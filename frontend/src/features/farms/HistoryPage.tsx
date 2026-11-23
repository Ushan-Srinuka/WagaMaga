import { Link, useParams, useSearchParams } from 'react-router'
import { useSession } from '../../app/session-context'
import type { Crop, Cultivation, Farm, Page, Revision } from '../../lib/farms'
import { area, cropName, timestamp } from '../../lib/farms'
import { Archived, Intro, Pagination, ReadState } from './RecordUI'
import { useRecord } from './record-hooks'
import { TaskHistory } from './TaskPanel'
import { PlanHistory } from './SuggestedPlans'

export default function HistoryPage() {
  const { farmId = '', cultivationId, observationId } = useParams()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Math.min(10000, Number(params.get('page')) || 1))
  return (
    <History
      key={`${farmId}:${cultivationId}:${observationId}:${page}`}
      farmId={farmId}
      cultivationId={cultivationId}
      observationId={observationId}
      page={page}
      change={(value) => setParams({ page: String(value) })}
    />
  )
}
function History({
  farmId,
  cultivationId,
  observationId,
  page,
  change,
}: {
  farmId: string
  cultivationId?: string
  observationId?: string
  page: number
  change: (page: number) => void
}) {
  const { user } = useSession()
  const farmPath = `/farms/${farmId}`
  const cultivationPath = `${farmPath}/cultivations/${cultivationId}`
  const kind = observationId
    ? 'Observation'
    : cultivationId
      ? 'Cultivation'
      : 'Farm'
  const back = cultivationId ? cultivationPath : farmPath
  const farm = useRecord<Farm>(farmPath)
  const cultivation = useRecord<Cultivation>(
    cultivationId ? cultivationPath : null,
  )
  const crops = useRecord<Page<Crop>>('/crop-types?page_size=100')
  const contextReady = Boolean(
    farm.data && (!cultivationId || cultivation.data),
  )
  const path = observationId
    ? `/cultivations/${cultivationId}/observations/${observationId}`
    : back
  const history = useRecord<Page<Revision>>(
    contextReady ? `${path}/history?page=${page}` : null,
  )
  const error = farm.error ?? cultivation.error ?? history.error
  if (error || !farm.data || !history.data)
    return (
      <ReadState
        loading={
          !error && (farm.loading || cultivation.loading || history.loading)
        }
        error={error}
        retry={() => {
          farm.reload()
          cultivation.reload()
          history.reload()
        }}
      />
    )
  const archived =
    farm.data.effective_archived || cultivation.data?.effective_archived
  const timezone = farm.data.timezone
  return (
    <div className="farm-records">
      <Link className="back-link" to={back}>
        ← Back to {cultivationId ? 'cultivation' : farm.data.name}
      </Link>
      <Intro
        eyebrow={`${farm.data.name} / Record history`}
        title={`${kind} history`}
      >
        Earlier versions stay readable. Editing a record does not erase what was
        recorded before.
      </Intro>
      {archived && (
        <Archived
          inherited={Boolean(farm.data.effective_archived && cultivationId)}
        />
      )}
      <section aria-label={`${kind} revisions`} className="record-history">
        {history.data.items.length === 0 ? (
          <section className="panel empty-state">
            <h2>No history to show.</h2>
          </section>
        ) : (
          history.data.items.map((revision, index) => {
            const snapshot = revision.snapshot
            const fields: [string, string][] =
              kind === 'Farm'
                ? [
                    ['name', 'Farm name'],
                    ['location', 'Location'],
                    ['timezone', 'Timezone'],
                    ['latitude', 'Latitude'],
                    ['longitude', 'Longitude'],
                  ]
                : kind === 'Cultivation'
                  ? [
                      ['crop_type_id', 'Crop'],
                      ['planting_date', 'Planting date'],
                      ['soil_notes', 'Soil information'],
                      ['estimated_stage', 'Estimated stage'],
                      ['confirmed_stage', 'Reported stage'],
                      ['confirmed_by', 'Confirmed by'],
                      ['confirmed_at', 'Confirmed at'],
                    ]
                  : [
                      ['observed_at', 'Observed at'],
                      ['notes', 'Notes'],
                      ['soil_moisture', 'Soil moisture'],
                      ['recorded_by', 'Originally recorded by'],
                    ]
            function value(key: string) {
              const item = snapshot[key]
              if (item === null || item === undefined)
                return key.includes('soil') || key.includes('stage')
                  ? 'Unknown'
                  : 'Not recorded'
              if (key === 'crop_type_id')
                return cropName(String(item), crops.data?.items ?? [])
              if (key === 'confirmed_by' || key === 'recorded_by')
                return item === user?.id ? 'You' : 'The recorded account'
              if (key === 'confirmed_at' || key === 'observed_at')
                return timestamp(String(item), timezone)
              return String(item)
            }
            return (
              <article className="panel" key={revision.id}>
                <div className="record-card-top">
                  <h2>Version {revision.version}</h2>
                  <span className="status-pill">
                    {snapshot.archived_at ? 'Archived' : 'Saved record'}
                  </span>
                </div>
                <p className="muted">
                  {timestamp(revision.changed_at, timezone)} · {timezone} ·{' '}
                  {revision.changed_by === user?.id
                    ? 'Saved by you'
                    : 'Saved by the recorded account'}
                </p>
                <details open={index === 0}>
                  <summary>View recorded details</summary>
                  <dl className="record-history-fields">
                    {fields.map(([key, label]) => (
                      <div key={key}>
                        <dt>{label}</dt>
                        <dd className="record-note">{value(key)}</dd>
                      </div>
                    ))}
                    {kind !== 'Observation' && (
                      <>
                        <div>
                          <dt>Area</dt>
                          <dd>
                            {area(
                              snapshot.area_value,
                              String(snapshot.area_unit ?? ''),
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Archived at</dt>
                          <dd>
                            {snapshot.archived_at
                              ? timestamp(
                                  String(snapshot.archived_at),
                                  timezone,
                                )
                              : 'Not archived in this version'}
                          </dd>
                        </div>
                      </>
                    )}
                  </dl>
                </details>
              </article>
            )
          })
        )}
      </section>
      <Pagination result={history.data} page={page} change={change} />
      {cultivationId && !observationId && (
        <>
          <TaskHistory path={cultivationPath + '/tasks'} timezone={timezone} />
          <PlanHistory
            path={cultivationPath + '/task-plans'}
            timezone={timezone}
          />
        </>
      )}
    </div>
  )
}
