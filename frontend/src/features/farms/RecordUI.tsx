import { useId, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import Notice from '../../components/Notice'
import Field from '../../components/Field'
import type { Crop, Cultivation, Farm, Page, Unit } from '../../lib/farms'
import { areaError, farmWrite } from '../../lib/farms'
import { useRecord, useSave } from './record-hooks'
import { districts } from '../../lib/districts'
import ExactLocation from './ExactLocation'

export function ScopeNote() {
  return (
    <p className="record-scope">
      You can keep farm records for any location. Cultivation guidance uses
      selected chilli references for farms recorded in Anuradhapura.
    </p>
  )
}

export function ReadState({
  loading,
  error,
  retry,
}: {
  loading: boolean
  error: unknown
  retry: () => void
}) {
  if (loading)
    return (
      <p className="empty-state" role="status">
        Loading farm records…
      </p>
    )
  const status =
    error && typeof error === 'object' && 'status' in error
      ? error.status
      : null
  return (
    <section className="panel record-state">
      <h2>
        {status === 404
          ? 'Record unavailable'
          : status === 403
            ? 'Access denied'
            : 'Let’s reconnect'}
      </h2>
      <Notice
        message={
          status === 404
            ? 'This record is unavailable or does not belong to your account.'
            : status === 403
              ? 'Farmer access is required for these records.'
              : 'The records could not be loaded. Check your connection and try again.'
        }
      />
      {![403, 404].includes(Number(status)) && (
        <button onClick={retry}>Try again</button>
      )}
      <Link to="/farms">Back to My Farms</Link>
    </section>
  )
}
export function Archived({ inherited = false }: { inherited?: boolean }) {
  return (
    <Notice
      message={
        inherited
          ? 'The parent farm is archived. This cultivation and its observations are read-only; history is still available.'
          : 'Archived record. Details and history remain available; new changes are disabled.'
      }
    />
  )
}
export function Pagination({
  result,
  page,
  change,
}: {
  result: Page<unknown>
  page: number
  change: (page: number) => void
}) {
  return (
    <nav className="record-pagination" aria-label="Record pages">
      <button disabled={page <= 1} onClick={() => change(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} · {result.total} {result.total === 1 ? 'record' : 'records'}
      </span>
      <button
        disabled={page * result.page_size >= result.total}
        onClick={() => change(page + 1)}
      >
        Next
      </button>
    </nav>
  )
}
export function TextArea({
  label,
  value,
  change,
  maxLength,
  required = false,
  disabled,
}: {
  label: string
  value: string
  change: (v: string) => void
  maxLength: number
  required?: boolean
  disabled?: boolean
}) {
  const id = useId()
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => change(e.target.value)}
        maxLength={maxLength}
        required={required}
        disabled={disabled}
        rows={4}
      />
    </div>
  )
}
export function AreaFields({
  value,
  unit,
  change,
  required,
}: {
  value: string
  unit: Unit
  change: (v: string, u: Unit) => void
  required: boolean
}) {
  const id = useId()
  return (
    <div className="record-form-grid">
      <Field
        label={required ? 'Cultivation area' : 'Farm area (optional)'}
        inputMode="decimal"
        value={value}
        required={required}
        onChange={(e) => change(e.target.value, unit)}
        hint="Use a positive number with up to six decimal places."
      />
      <div className="field">
        <label htmlFor={id}>Area unit</label>
        <select
          id={id}
          value={unit}
          onChange={(e) => change(value, e.target.value as Unit)}
        >
          <option value="ha">Hectares (ha)</option>
          <option value="acre">Acres</option>
          <option value="m2">Square metres (m²)</option>
        </select>
      </div>
    </div>
  )
}
export function SaveError({
  error,
  blocked,
  review,
  create = false,
}: {
  error: string
  blocked: boolean
  review: string | (() => void)
  create?: boolean
}) {
  if (!error) return null
  return (
    <div>
      <Notice message={error} />
      {blocked && (
        <p>
          {create
            ? 'Review the existing records before creating another.'
            : 'Your draft remains here. Reloading discards it and opens the latest saved record.'}
        </p>
      )}
      {blocked &&
        (typeof review === 'string' ? (
          <Link className="record-link" to={review}>
            Review records
          </Link>
        ) : (
          <button type="button" onClick={review}>
            Reload latest record
          </button>
        ))}
    </div>
  )
}
export function FarmForm({
  record,
  saved,
  review,
  onBusy,
}: {
  record?: Farm
  saved: (farm: Farm) => void
  review: string | (() => void)
  onBusy?: (busy: boolean) => void
}) {
  const [name, setName] = useState(record?.name ?? '')
  const [location, setLocation] = useState(record?.location ?? '')
  const [locationMode, setLocationMode] = useState(
    record ? 'description' : 'district',
  )
  const [district, setDistrict] = useState('')
  const [village, setVillage] = useState('')
  const [locating, setLocating] = useState(false)
  const locationId = useId()
  const [timezone, setTimezone] = useState(record?.timezone ?? 'Asia/Colombo')
  const [latitude, setLatitude] = useState(record?.latitude ?? '')
  const [longitude, setLongitude] = useState(record?.longitude ?? '')
  const [size, setSize] = useState(record?.area_value ?? '')
  const [unit, setUnit] = useState<Unit>(record?.area_unit ?? 'ha')
  const [invalid, setInvalid] = useState('')
  const save = useSave()
  function submit(event: FormEvent) {
    event.preventDefault()
    if (locating) return
    setInvalid('')
    const farmLocation =
      locationMode === 'district'
        ? village.trim() && district
          ? `${village.trim()}, ${district} District, Sri Lanka`
          : ''
        : location.trim()
    const coordinates = [latitude.trim(), longitude.trim()]
    if (!name.trim() || !farmLocation || !timezone.trim()) {
      setInvalid(
        'Enter a farm name and location. Choose a district and village/town, or describe the location yourself. Check the timezone under additional details.',
      )
      return
    }
    if (farmLocation.length > 200) {
      setInvalid(
        'Shorten the location to 200 characters or fewer, including the district and country.',
      )
      return
    }
    if (
      coordinates.some(Boolean) &&
      (!coordinates.every(Boolean) ||
        !coordinates.every((v) => Number.isFinite(Number(v))) ||
        Math.abs(Number(coordinates[0])) > 90 ||
        Math.abs(Number(coordinates[1])) > 180)
    ) {
      setInvalid(
        'Enter both coordinates: latitude between −90 and 90, longitude between −180 and 180.',
      )
      return
    }
    if (size && areaError(size)) {
      setInvalid(areaError(size))
      return
    }
    const body = {
      name: name.trim(),
      location: farmLocation,
      timezone: timezone.trim(),
      latitude: coordinates[0] || null,
      longitude: coordinates[1] || null,
      area_value: size || null,
      area_unit: size ? unit : null,
      ...(record ? { expected_version: record.version } : {}),
    }
    onBusy?.(true)
    void save
      .run(
        () =>
          farmWrite<Farm>(
            record ? `/farms/${record.id}` : '/farms',
            record ? 'PATCH' : 'POST',
            body,
          ),
        saved,
      )
      .finally(() => onBusy?.(false))
  }
  return (
    <form onSubmit={submit} className="record-form">
      <fieldset disabled={save.busy || save.blocked}>
        <legend className="visually-hidden">Farm details</legend>
        <Field
          label="Farm name"
          required
          maxLength={120}
          value={name}
          onChange={(e) => setName(e.target.value)}
          hint="Choose your own name, for example Home garden or North field."
        />
        <div className="field">
          <label htmlFor={locationId}>
            How would you like to enter the location?
          </label>
          <select
            id={locationId}
            value={locationMode}
            onChange={(e) => setLocationMode(e.target.value)}
          >
            <option value="district">Choose a Sri Lankan district</option>
            <option value="description">Describe the location myself</option>
          </select>
        </div>
        {locationMode === 'district' ? (
          <>
            <div className="field">
              <label htmlFor={`${locationId}-district`}>District</label>
              <select
                id={`${locationId}-district`}
                required
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                aria-describedby={`${locationId}-hint`}
              >
                <option value="">Choose your farm’s district</option>
                {districts.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <small id={`${locationId}-hint`}>
                Choose where the farm is, even if you live elsewhere. No
                district is selected for you.
              </small>
            </div>
            <Field
              label="Village or town"
              required
              maxLength={140}
              value={village}
              onChange={(e) => setVillage(e.target.value)}
              hint="Enter the village, town or nearby place that identifies your farm."
            />
          </>
        ) : (
          <Field
            label="Location"
            required
            maxLength={200}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            hint="Enter your own village, district and country. Existing descriptions are kept as entered."
          />
        )}
        <p className="record-scope">
          Chilli cultivation guidance is available for farms recorded in
          Anuradhapura.
        </p>
        <ExactLocation
          latitude={latitude}
          longitude={longitude}
          change={(lat, lon) => {
            setLatitude(lat)
            setLongitude(lon)
          }}
          onPending={setLocating}
        />
        <details className="record-options">
          <summary>Additional farm details — optional</summary>
          <AreaFields
            value={size}
            unit={unit}
            required={false}
            change={(v, u) => {
              setSize(v)
              setUnit(u)
            }}
          />
          <Field
            label="Farm timezone"
            maxLength={100}
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            hint="Defaults to Sri Lanka (Asia/Colombo). Change this if your farm uses another timezone."
          />
        </details>
        {invalid && <Notice message={invalid} />}
        <button
          className="primary"
          disabled={save.busy || save.blocked || locating}
        >
          {save.busy ? 'Saving…' : record ? 'Save farm' : 'Create farm'}
        </button>
      </fieldset>
      <SaveError {...save} review={review} create={!record} />
    </form>
  )
}
export function CultivationForm({
  farm,
  record,
  saved,
  review,
  onBusy,
}: {
  farm: Farm
  record?: Cultivation
  saved: (record: Cultivation) => void
  review: string | (() => void)
  onBusy?: (busy: boolean) => void
}) {
  const crops = useRecord<Page<Crop>>('/crop-types?page_size=100')
  const [crop, setCrop] = useState(record?.crop_type_id ?? '')
  const [planting, setPlanting] = useState(record?.planting_date ?? '')
  const [size, setSize] = useState(record?.area_value ?? '')
  const [unit, setUnit] = useState<Unit>(record?.area_unit ?? 'ha')
  const [soil, setSoil] = useState(record?.soil_notes ?? '')
  const [invalid, setInvalid] = useState('')
  const selectId = useId()
  const save = useSave()
  if (!crops.data)
    return (
      <ReadState
        loading={crops.loading}
        error={crops.error}
        retry={crops.reload}
      />
    )
  const selected = crop || crops.data.items[0]?.id || ''
  function submit(event: FormEvent) {
    event.preventDefault()
    setInvalid('')
    if (areaError(size)) {
      setInvalid(areaError(size))
      return
    }
    const body = {
      crop_type_id: selected,
      planting_date: planting,
      area_value: size,
      area_unit: unit,
      soil_notes: soil.trim() || null,
      ...(record ? { expected_version: record.version } : {}),
    }
    // Keep retired crop context editable without explicitly reassigning the unsupported ID.
    if (record && selected === record.crop_type_id)
      delete (body as { crop_type_id?: string }).crop_type_id
    const path = `/farms/${farm.id}/cultivations${record ? `/${record.id}` : ''}`
    onBusy?.(true)
    void save
      .run(
        () => farmWrite<Cultivation>(path, record ? 'PATCH' : 'POST', body),
        saved,
      )
      .finally(() => onBusy?.(false))
  }
  return (
    <form onSubmit={submit} className="record-form">
      <fieldset disabled={save.busy || save.blocked}>
        <legend className="visually-hidden">Cultivation details</legend>
        <div className="field">
          <label htmlFor={selectId}>Crop</label>
          <select
            id={selectId}
            required
            value={selected}
            onChange={(e) => setCrop(e.target.value)}
          >
            {record &&
              !crops.data.items.some(
                (item) => item.id === record.crop_type_id,
              ) && (
                <option value={record.crop_type_id}>
                  Previously recorded crop
                </option>
              )}
            {crops.data.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.display_name}
              </option>
            ))}
          </select>
        </div>
        <p className="muted">
          Choose what you are growing. Chilli is the initial supported crop for
          records. Guidance is not available yet.
        </p>
        {crops.data.total === 0 && !record && (
          <Notice message="No supported crops are available. Please try again later." />
        )}
        <Field
          label="Planting date"
          type="date"
          required
          value={planting}
          onChange={(e) => setPlanting(e.target.value)}
          hint="A future date is a planned cultivation, not a crop-stage estimate."
        />
        <AreaFields
          value={size}
          unit={unit}
          required
          change={(v, u) => {
            setSize(v)
            setUnit(u)
          }}
        />
        <TextArea
          label="Soil information (optional)"
          value={soil}
          change={setSoil}
          maxLength={2000}
        />
        {record && (
          <p className="muted">
            Changing the crop or planting date clears the current stage
            confirmation. Earlier versions remain in history.
          </p>
        )}
        {invalid && <Notice message={invalid} />}
        <button
          className="primary"
          disabled={save.busy || save.blocked || !selected}
        >
          {save.busy
            ? 'Saving…'
            : record
              ? 'Save cultivation'
              : 'Create cultivation'}
        </button>
      </fieldset>
      <SaveError {...save} review={review} create={!record} />
    </form>
  )
}
export function Intro({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string
  title: string
  children?: ReactNode
}) {
  return (
    <header className="page-intro">
      <p className="eyebrow">{eyebrow}</p>
      <h1>
        {title}
        <span>.</span>
      </h1>
      {children && <p>{children}</p>}
    </header>
  )
}
