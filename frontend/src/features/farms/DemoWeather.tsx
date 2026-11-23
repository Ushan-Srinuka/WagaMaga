import type { DemoForecast } from '../../lib/farms'

export default function DemoWeather({
  forecast,
  loading,
  retry,
}: {
  forecast?: DemoForecast
  loading: boolean
  retry: () => void
}) {
  return (
    <section
      className="panel record-inset"
      aria-labelledby="demo-weather-heading"
    >
      <h3 id="demo-weather-heading">Demo weather</h3>
      {forecast?.source === 'fixture' ? (
        <>
          <p className="muted record-note">
            Simulated forecast for {forecast.location} · {forecast.timezone}
          </p>
          <p>
            <time dateTime={forecast.forecast_date}>
              {forecast.forecast_date}
            </time>
            {' · Rain · '}
            {forecast.rainfall_mm} mm sample rainfall
          </p>
        </>
      ) : loading ? (
        <p role="status">Loading demo weather…</p>
      ) : (
        <>
          <p role="status">Demo weather is unavailable.</p>
          <button type="button" onClick={retry}>
            Retry demo weather
          </button>
        </>
      )}
    </section>
  )
}
