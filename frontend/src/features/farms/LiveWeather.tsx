import { useEffect } from 'react'
import { Link } from 'react-router'
import Notice from '../../components/Notice'
import type { FarmWeather } from '../../lib/farms'
import { farmWrite, timestamp } from '../../lib/farms'
import { useRecord, useSave } from './record-hooks'

export default function LiveWeather({
  record,
  path,
  farmPath,
}: {
  record: ReturnType<typeof useRecord<FarmWeather>>
  path: string
  farmPath: string
}) {
  const { data, loading, reload, replace } = record
  const save = useSave((error) =>
    error instanceof Error ? error.message : 'Could not fetch the forecast.',
  )
  const staleAt =
    data?.status === 'fresh' ? data.forecast?.fresh_until : undefined
  const checkedAt = data?.checked_at

  useEffect(() => {
    if (!staleAt || !checkedAt) return
    const elapsed = Math.max(
      1000,
      Date.parse(staleAt) - Date.parse(checkedAt) + 50,
    )
    const timer = window.setTimeout(reload, elapsed)
    return () => window.clearTimeout(timer)
  }, [checkedAt, reload, staleAt])

  return (
    <section
      className="panel record-inset"
      aria-labelledby="live-weather-heading"
    >
      <h3 id="live-weather-heading">Weather forecast</h3>
      {loading && <p role="status">Loading saved forecast…</p>}
      {record.error !== undefined && (
        <>
          <p role="status">Could not load the saved forecast.</p>
          <button type="button" onClick={reload}>
            Retry
          </button>
        </>
      )}
      {data && (
        <>
          <p className="muted record-note">
            {data.location} · {data.timezone}
          </p>
          {data.status === 'needs_coordinates' && (
            <>
              <p>Save your farm coordinates to get a forecast for this area.</p>
              <Link to={farmPath}>Open farm to add coordinates</Link>
            </>
          )}
          {data.status === 'unfetched' && (
            <p>No forecast has been fetched for this farm.</p>
          )}
          {data.status === 'provider_disabled' && (
            <p>Live weather is unavailable.</p>
          )}
          {data.status === 'stale' && (
            <p role="status">
              The saved forecast is out of date. Refresh to get current values.
            </p>
          )}
          {data.forecast && (
            <>
              <p className="muted">
                <a
                  href="https://open-meteo.com/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Weather data by Open-Meteo
                </a>
                {' · '}
                <a
                  href="https://creativecommons.org/licenses/by/4.0/"
                  target="_blank"
                  rel="noreferrer"
                >
                  CC BY 4.0
                </a>
                {' · Fetched '}
                <time dateTime={data.forecast.fetched_at}>
                  {timestamp(data.forecast.fetched_at, data.timezone)}
                </time>
              </p>
              <ul className="record-rows" aria-label="Daily forecast">
                {data.forecast.days.map((day) => (
                  <li key={day.date}>
                    <div>
                      <time dateTime={day.date}>{day.date}</time>
                      <p className="muted">
                        Low {day.minimum_c} °C · High {day.maximum_c} °C
                      </p>
                    </div>
                    <span>{day.precipitation_mm} mm precipitation</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {data.can_refresh && !save.blocked && (
            <>
              <p className="muted">
                Fetching shares approximate farm coordinates with Open-Meteo.
              </p>
              <button
                type="button"
                disabled={save.busy}
                onClick={() =>
                  void save.run(
                    () => farmWrite<FarmWeather>(path + '/refresh', 'POST', {}),
                    replace,
                  )
                }
              >
                {save.busy
                  ? 'Fetching forecast…'
                  : data.forecast
                    ? 'Refresh forecast'
                    : 'Fetch forecast'}
              </button>
            </>
          )}
          {save.error && <Notice message={save.error} />}
          {save.blocked && (
            <button
              type="button"
              onClick={() => {
                save.reset()
                reload()
              }}
            >
              Check saved forecast
            </button>
          )}
        </>
      )}
    </section>
  )
}
