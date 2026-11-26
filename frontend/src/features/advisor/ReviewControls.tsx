export type ReviewView = 'pending' | 'reviewed'

export function ReviewFilter({
  view,
  change,
}: {
  view: ReviewView
  change: (view: ReviewView) => void
}) {
  return (
    <div className="record-toolbar" aria-label="Review status" role="group">
      <button
        type="button"
        aria-pressed={view === 'pending'}
        onClick={() => change('pending')}
      >
        Needs review
      </button>
      <button
        type="button"
        aria-pressed={view === 'reviewed'}
        onClick={() => change('reviewed')}
      >
        Recently reviewed
      </button>
    </div>
  )
}

export function ReviewTime({ value }: { value: string }) {
  return <time dateTime={value}>{new Date(value).toLocaleString()}</time>
}
