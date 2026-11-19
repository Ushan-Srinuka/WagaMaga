import { useEffect, useRef, type ReactNode } from 'react'

export default function ConfirmDialog({
  title,
  description,
  busy,
  error,
  onConfirm,
  onClose,
  eyebrow = 'Confirm account change',
  confirmLabel = 'Confirm change',
  confirmDisabled = false,
  children,
}: {
  title: string
  description: string
  busy: boolean
  error: string
  onConfirm: () => void
  onClose: () => void
  eyebrow?: string
  confirmLabel?: string
  confirmDisabled?: boolean
  children?: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const dialog = ref.current
    dialog?.showModal()
    return () => {
      dialog?.close()
      previous?.focus()
    }
  }, [])
  return (
    <dialog
      ref={ref}
      className="confirm-dialog"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-description"
      onCancel={(event) => {
        event.preventDefault()
        if (!busy) onClose()
      }}
    >
      <span className="eyebrow">{eyebrow}</span>
      <h2 id="confirm-title">{title}</h2>
      <p id="confirm-description">{description}</p>
      {children}
      {error && (
        <p role="alert" className="form-notice">
          {error}
        </p>
      )}
      <div className="button-row">
        <button type="button" disabled={busy} onClick={onClose}>
          Cancel
        </button>
        <button
          className="primary"
          disabled={busy || confirmDisabled}
          onClick={onConfirm}
        >
          {busy ? 'Saving…' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
