import { Link, useNavigate, useParams } from 'react-router'
import type { PlanReviewLink } from '../../lib/farms'
import { AssignedReview } from './AdvisorCasesPage'
import { ReadState } from './RecordUI'
import WeeklySuggestion from './WeeklySuggestion'
import { useRecord } from './record-hooks'

export default function PlanReviewPage() {
  const { planId = '' } = useParams()
  const sourcePath = `/plan-reviews/${planId}`
  const record = useRecord<PlanReviewLink>(sourcePath)
  const navigate = useNavigate()
  const review = record.data
  if (!review)
    return (
      <ReadState
        loading={record.loading}
        error={record.error}
        retry={record.reload}
      />
    )
  if (review.role === 'advisor')
    return (
      <div className="farm-records">
        <h1>Assigned plan review</h1>
        <Link to="/advisor/cases">All assigned reviews</Link>
        <AssignedReview
          key={review.case.id}
          item={review.case}
          reload={record.reload}
          replace={(decision) =>
            record.replace({
              ...review,
              case: { ...review.case, review: decision },
            })
          }
        />
      </div>
    )
  const path = `/farms/${review.farm_id}/cultivations/${review.cultivation_id}`
  return (
    <div className="farm-records">
      <h1>Weekly plan review</h1>
      <Link to={path}>Open cultivation</Link>
      <WeeklySuggestion
        key={planId}
        task={review.task}
        sourcePath={sourcePath}
        taskPath={`${path}/tasks`}
        planPath={`${path}/task-plans`}
        timezone={review.timezone}
        changed={record.reload}
        onRevised={(id) => navigate(`/plan-reviews/${id}`)}
      />
    </div>
  )
}
