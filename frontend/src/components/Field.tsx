import { useId, useState, type ComponentPropsWithRef } from 'react'

type Props = ComponentPropsWithRef<'input'> & {
  label: string
  hint?: string
}
export default function Field({ label, hint, type, ...props }: Props) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        <input
          {...props}
          id={id}
          type={type === 'password' && visible ? 'text' : type}
          aria-describedby={hint ? `${id}-hint` : undefined}
        />
        {type === 'password' && (
          <button
            type="button"
            className="password-toggle"
            aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
            aria-pressed={visible}
            onClick={() => setVisible(!visible)}
          >
            {visible ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </div>
  )
}
