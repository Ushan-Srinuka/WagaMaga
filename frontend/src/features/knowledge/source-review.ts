import { ApiError } from '../../lib/accounts'

export type SourceReview = {
  sequence: number
  event: 'assigned' | 'revoked' | 'approved' | 'changes_requested'
  reason: string
  created_at: string
}

export const reviewLabels = {
  assigned: 'Awaiting advisor review',
  revoked: 'Assignment revoked',
  approved: 'Approved by advisor',
  changes_requested: 'Changes requested by advisor',
}

export function sourceReviewError(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : 'The review could not be saved.'
}
