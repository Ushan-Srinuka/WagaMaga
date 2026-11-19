import { useState } from 'react'
import { Link } from 'react-router'
import type { Cultivation, Farm, Observation, Page } from '../../lib/farms'
import { useRecord } from '../farms/record-hooks'

export default function FarmActionBar() {
  const farms = useRecord<Page<Farm>>('/farms?status=active&page_size=100')
  const [selected, setSelected] = useState('')
  const farm =
    farms.data?.items.find((item) => item.id === selected) ??
    farms.data?.items[0]
  return (
    <div className="home-farm-start" id="farm-start">
      <p className="home-launcher-caption">Your farm workspace</p>
      {!farms.data ? (
        <div className="home-launcher home-launcher-state">
          {farms.loading ? (
            <p role="status">Finding your farm records…</p>
          ) : (
            <>
              <p role="alert">
                Your farm list could not be loaded. Try again or open your
                records.
              </p>
              <button type="button" onClick={farms.reload}>
                Try again
              </button>
              <Link to="/farms">Open farm records</Link>
            </>
          )}
        </div>
      ) : farm ? (
        <div className="home-launcher">
          <div className="home-launcher-field">
            <label htmlFor="home-farm-select">Choose your farm</label>
            <select
              id="home-farm-select"
              value={farm.id}
              onChange={(event) => setSelected(event.target.value)}
            >
              {farms.data.items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <span className="home-launcher-detail">{farm.location}</span>
          </div>
          <FarmContinuation key={farm.id} farm={farm} />
        </div>
      ) : (
        <FirstFarm signedIn />
      )}
      <div className="home-launcher-links">
        <Link to="/farms">
          View all farm records <span aria-hidden="true">↗</span>
        </Link>
        {farm ? (
          <Link to="/farms/new">＋ Add another farm</Link>
        ) : (
          <Link to="/farms?status=archived">View archived farms</Link>
        )}
        {farms.data && farms.data.total > farms.data.items.length && (
          <span>
            Showing the first {farms.data.items.length} active farms. View all
            records for more.
          </span>
        )}
      </div>
    </div>
  )
}

function FarmContinuation({ farm }: { farm: Farm }) {
  const crops = useRecord<Page<Cultivation>>(
    `/farms/${farm.id}/cultivations?status=active&page_size=1`,
  )
  const crop = crops.data?.items[0]
  const notes = useRecord<Page<Observation>>(
    crop ? `/cultivations/${crop.id}/observations?page_size=1` : null,
  )
  const pending = crops.loading || notes.loading
  const failed = crops.error || notes.error
  const ready = Boolean(crops.data && (!crop || notes.data))
  const hasNotes = Boolean(notes.data?.total)
  const cropPath = crop ? `/farms/${farm.id}/cultivations/${crop.id}` : ''
  const target = !ready
    ? `/farms/${farm.id}`
    : !crop
      ? `/farms/${farm.id}/cultivations/new`
      : `${cropPath}${hasNotes ? '' : '?observe=1'}`
  const label = !ready
    ? 'Open farm'
    : !crop
      ? 'Add what you are growing'
      : !hasNotes
        ? 'Record first observation'
        : 'Open crop records'
  return (
    <>
      <div className="home-launcher-field home-launcher-next">
        <span className="home-launcher-label">Your next step</span>
        <strong>
          {!ready
            ? 'Your farm records'
            : !crop
              ? 'What are you growing?'
              : !hasNotes
                ? 'Start your field notes'
                : 'Pick up where you left off'}
        </strong>
        {failed ? (
          <span role="alert" className="home-launcher-detail">
            Next step unavailable.{' '}
            <button
              type="button"
              className="home-inline-retry"
              onClick={() => {
                crops.reload()
                notes.reload()
              }}
            >
              Retry
            </button>
          </span>
        ) : (
          <span
            className="home-launcher-detail"
            role={pending ? 'status' : undefined}
          >
            {pending
              ? 'Checking saved records…'
              : !crop
                ? 'Add a crop, planting date and planted area.'
                : !hasNotes
                  ? 'Add a note about what you see in your field.'
                  : `Planting date ${crop.planting_date} · Your saved observations`}
          </span>
        )}
      </div>
      <Link className="home-launcher-button" to={target}>
        {label} <span aria-hidden="true">↗</span>
      </Link>
    </>
  )
}

export function FirstFarm({ signedIn = false }: { signedIn?: boolean }) {
  return (
    <div className="home-launcher">
      <div className="home-launcher-field">
        <span className="home-launcher-label">Start with your farm</span>
        <strong>Add your first farm</strong>
        <span className="home-launcher-detail">
          Your own farm name and village. No coordinates needed.
        </span>
      </div>
      <div className="home-launcher-field home-launcher-next">
        <span className="home-launcher-label">Then make it yours</span>
        <strong>Crops &amp; field notes</strong>
        <span className="home-launcher-detail">
          Keep your planting details and observations together.
        </span>
      </div>
      <Link
        className="home-launcher-button"
        to={signedIn ? '/farms/new' : '/register'}
      >
        {signedIn ? 'Add my farm' : 'Get started'}{' '}
        <span aria-hidden="true">↗</span>
      </Link>
    </div>
  )
}
