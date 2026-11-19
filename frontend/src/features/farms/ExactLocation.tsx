import { useEffect, useRef, useState } from 'react'
import Field from '../../components/Field'

export default function ExactLocation({
  latitude,
  longitude,
  change,
  onPending,
}: {
  latitude: string
  longitude: string
  change: (latitude: string, longitude: string) => void
  onPending: (pending: boolean) => void
}) {
  const generation = useRef(0)
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(
    () => () => {
      generation.current++
    },
    [],
  )
  function cancel() {
    generation.current++
    setPending(false)
    onPending(false)
    setMessage('')
  }
  function locate() {
    const current = ++generation.current
    if (!window.isSecureContext || !navigator.geolocation) {
      setMessage(
        'Device location is unavailable here. You can enter coordinates manually or continue without them.',
      )
      return
    }
    setPending(true)
    onPending(true)
    setMessage('Finding your device location…')
    const finish = (
      position?: GeolocationPosition,
      error?: GeolocationPositionError,
    ) => {
      if (generation.current !== current) return
      setPending(false)
      onPending(false)
      if (
        position &&
        Number.isFinite(position.coords.latitude) &&
        Number.isFinite(position.coords.longitude) &&
        Math.abs(position.coords.latitude) <= 90 &&
        Math.abs(position.coords.longitude) <= 180
      ) {
        change(
          String(position.coords.latitude),
          String(position.coords.longitude),
        )
        const accuracy = position.coords.accuracy
        setMessage(
          `Device location added${Number.isFinite(accuracy) && accuracy > 0 ? ` (approximate accuracy: ${Math.ceil(accuracy)} metres)` : ''}. Check that you are at your farm before saving. You can change or remove it.`,
        )
      } else {
        setMessage(
          error?.code === 1
            ? 'Location permission was denied. Your existing coordinates have not changed. Enter them manually or continue without them.'
            : 'Your device location could not be found. Your existing coordinates have not changed. Try again, enter them manually or continue without them.',
        )
      }
    }
    try {
      navigator.geolocation.getCurrentPosition(
        (position) => finish(position),
        (error) => finish(undefined, error),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
      )
    } catch {
      finish()
    }
  }
  return (
    <details className="record-options">
      <summary>Add exact farm location — optional</summary>
      <p>
        Only use your current location while you are at the farm. Your browser
        may ask for permission. Nothing is saved until you save the farm.
      </p>
      <div className="record-toolbar">
        <button type="button" disabled={pending} onClick={locate}>
          Use my current location
        </button>
        {pending && (
          <button type="button" onClick={cancel}>
            Cancel location lookup
          </button>
        )}
        {(latitude || longitude) && (
          <button
            type="button"
            onClick={() => {
              cancel()
              change('', '')
            }}
          >
            Remove coordinates
          </button>
        )}
      </div>
      <p role="status">{message}</p>
      <div className="record-form-grid">
        <Field
          label="Latitude (optional)"
          inputMode="decimal"
          value={latitude}
          onChange={(e) => {
            cancel()
            change(e.target.value, longitude)
          }}
        />
        <Field
          label="Longitude (optional)"
          inputMode="decimal"
          value={longitude}
          onChange={(e) => {
            cancel()
            change(latitude, e.target.value)
          }}
        />
      </div>
      <p className="muted">
        Leave both blank if you do not know them. A district selection does not
        fill or verify exact coordinates.
      </p>
    </details>
  )
}
