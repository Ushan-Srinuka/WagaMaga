import { useState } from 'react'
import Notice from '../../components/Notice'
import { farmWrite } from '../../lib/farms'
import { useRecord, useSave } from '../farms/record-hooks'

import {
  reviewLabels,
  sourceReviewError,
  type SourceReview,
} from './source-review'

export default function SourceReviewAssignment({ path }: { path: string }) {
  const assignment = useRecord<{ review: SourceReview | null }>(path)
  const save = useSave(sourceReviewError)
  const [email, setEmail] = useState('')
  const review = assignment.data?.review

  function update(advisorEmail: string | null) {
    void save.run(
      () =>
        farmWrite<SourceReview>(path, 'PATCH', {
          expected_sequence: review?.sequence ?? 0,
          advisor_email: advisorEmail,
        }),
      (result) => {
        assignment.replace({ review: result })
        setEmail('')
      },
    )
  }

  function reload() {
    save.reset()
    assignment.reload()
  }

  return (
    <section aria-label="Advisor assignment">
      {assignment.loading && <p role="status">Loading advisor assignment…</p>}
      {Boolean(assignment.error) && (
        <Notice message="The advisor assignment could not be loaded." />
      )}
      {assignment.data && (
        <>
          <p role="status">
            {review ? reviewLabels[review.event] : 'No advisor assigned'}
          </p>
          {review?.reason && <p className="record-note">{review.reason}</p>}
          {(!review ||
            review.event === 'assigned' ||
            review.event === 'revoked') && (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                update(email.trim())
              }}
            >
              <label className="field">
                Advisor email
                <input
                  type="email"
                  required
                  maxLength={254}
                  value={email}
                  disabled={save.busy || save.blocked}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <div className="button-row">
                <button disabled={save.busy || save.blocked || !email.trim()}>
                  {review?.event === 'assigned'
                    ? 'Reassign advisor'
                    : 'Assign advisor'}
                </button>
                {review?.event === 'assigned' && (
                  <button
                    type="button"
                    disabled={save.busy || save.blocked}
                    onClick={() => update(null)}
                  >
                    Revoke assignment
                  </button>
                )}
              </div>
            </form>
          )}
        </>
      )}
      {save.error && <Notice message={save.error} />}
      {(Boolean(assignment.error) || save.blocked) && (
        <button type="button" onClick={reload}>
          Reload advisor assignment
        </button>
      )}
    </section>
  )
}
