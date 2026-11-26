import { useState } from 'react'
import { Link, useParams } from 'react-router'
import {
  ReviewFilter,
  ReviewTime,
  type ReviewView,
} from '../advisor/ReviewControls'
import Notice from '../../components/Notice'
import { farmWrite } from '../../lib/farms'
import { ReadState, TextArea } from '../farms/RecordUI'
import { useRecord, useSave } from '../farms/record-hooks'
import type { PdfMetadata } from './PdfMetadataFields'
import {
  reviewLabels,
  sourceReviewError,
  type SourceReview,
} from './source-review'

const path = '/advisor/knowledge'
type AssignedSource = {
  id: string
  title: string
  assigned_at: string
  checksum: string
  rag_metadata: PdfMetadata | null
  review: SourceReview
}

function ReviewPagination({
  page,
  more,
  change,
}: {
  page: number
  more: boolean
  change: (page: number) => void
}) {
  return (
    <nav className="record-pagination" aria-label="Review pages">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => change(page - 1)}
      >
        Previous
      </button>
      <button type="button" disabled={!more} onClick={() => change(page + 1)}>
        Next
      </button>
    </nav>
  )
}

function ReviewSource({
  source,
  reload,
  replace,
}: {
  source: AssignedSource
  reload: () => void
  replace: (source: AssignedSource) => void
}) {
  const [page, setPage] = useState(1)
  const [reason, setReason] = useState('')
  const [jump, setJump] = useState('')
  const [outcome, setOutcome] = useState<'' | 'approved' | 'changes_requested'>(
    '',
  )
  const extracted = useRecord<{ number: number; text: string; total: number }>(
    `${path}/${source.id}/pages/${page}`,
  )
  const save = useSave(sourceReviewError)
  const metadata = source.rag_metadata

  function decide(outcome: 'approved' | 'changes_requested') {
    void save.run(
      () =>
        farmWrite<SourceReview>(`${path}/${source.id}/decision`, 'POST', {
          expected_sequence: source.review.sequence,
          outcome,
          reason: reason.trim(),
        }),
      (review) => replace({ ...source, review }),
    )
  }

  return (
    <div aria-busy={save.busy}>
      {metadata && (
        <dl>
          <dt>Publisher</dt>
          <dd>{metadata.publisher}</dd>
          <dt>Language</dt>
          <dd>{metadata.language}</dd>
          <dt>Crop and region</dt>
          <dd>
            {metadata.crop} · {metadata.region}
          </dd>
          <dt>Publication date</dt>
          <dd>{metadata.published_on ?? 'Unknown'}</dd>
          <dt>Valid until</dt>
          <dd>{metadata.valid_until ?? 'Unspecified'}</dd>
          <dt>Reuse basis</dt>
          <dd className="record-note">
            {metadata.reuse_basis ?? 'Unspecified'}
          </dd>
          {metadata.source_url && (
            <>
              <dt>Original source</dt>
              <dd>
                <a href={metadata.source_url} target="_blank" rel="noreferrer">
                  Open publisher source
                </a>
              </dd>
            </>
          )}
        </dl>
      )}
      <details>
        <summary>Technical details</summary>
        <p style={{ overflowWrap: 'anywhere' }}>SHA-256 {source.checksum}</p>
      </details>
      <ReadState
        loading={extracted.loading}
        error={extracted.error}
        retry={extracted.reload}
        advisor
      />
      {extracted.data && (
        <section aria-label="Extracted PDF text">
          <h3>
            Page {page} of {extracted.data.total}
          </h3>
          <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            {extracted.data.text || 'No text on this page.'}
          </p>
          <form
            className="record-toolbar"
            onSubmit={(event) => {
              event.preventDefault()
              setPage(Number(jump))
              setJump('')
            }}
          >
            <label className="field">
              Jump to page
              <input
                type="number"
                min={1}
                max={extracted.data.total}
                required
                value={jump}
                onChange={(event) => setJump(event.target.value)}
              />
            </label>
            <button type="submit">Go to page</button>
          </form>
          <ReviewPagination
            page={page}
            more={page < extracted.data.total}
            change={setPage}
          />
        </section>
      )}
      {source.review.event === 'assigned' && (
        <>
          <TextArea
            label="Review reason"
            value={reason}
            change={setReason}
            maxLength={500}
            required
            disabled={save.busy || save.blocked}
          />
          <label className="field">
            Review outcome
            <select
              value={outcome}
              disabled={save.busy || save.blocked}
              onChange={(event) =>
                setOutcome(event.target.value as typeof outcome)
              }
            >
              <option value="">Choose an outcome</option>
              <option value="approved">Approve this version</option>
              <option value="changes_requested">Request changes</option>
            </select>
          </label>
          <button
            type="button"
            disabled={
              !outcome ||
              !extracted.data ||
              !reason.trim() ||
              save.busy ||
              save.blocked
            }
            onClick={() => {
              if (outcome) decide(outcome)
            }}
          >
            Submit decision
          </button>
        </>
      )}
      {source.review.reason && (
        <>
          <p className="record-note">{source.review.reason}</p>
          <p>
            Submitted <ReviewTime value={source.review.created_at} />
          </p>
        </>
      )}
      {save.error && <Notice message={save.error} />}
      {save.blocked && (
        <button type="button" onClick={reload}>
          Reload assigned sources
        </button>
      )}
    </div>
  )
}

export default function AdvisorKnowledgePage() {
  const { versionId } = useParams()
  const [view, setView] = useState<ReviewView>('pending')
  if (versionId)
    return <KnowledgeReviewDetail key={versionId} versionId={versionId} />
  return (
    <div className="farm-records">
      <div className="page-intro">
        <h1>Knowledge review</h1>
        <p>
          Review the extracted text, applicability and reuse details of your
          assigned PDFs.
        </p>
      </div>
      <ReviewFilter view={view} change={setView} />
      <KnowledgeReviewList key={view} view={view} />
    </div>
  )
}

function KnowledgeReviewDetail({ versionId }: { versionId: string }) {
  const record = useRecord<AssignedSource>(`${path}/${versionId}`)
  const source = record.data
  return (
    <div className="farm-records">
      <Link to={path}>All knowledge reviews</Link>
      <ReadState
        loading={record.loading}
        error={record.error}
        retry={record.reload}
        advisor
      />
      {source && (
        <article className="panel">
          <h1>{source.title}</h1>
          <p>
            Assigned <ReviewTime value={source.assigned_at} />
          </p>
          <p role="status">{reviewLabels[source.review.event]}</p>
          <ReviewSource
            source={source}
            reload={record.reload}
            replace={record.replace}
          />
        </article>
      )}
    </div>
  )
}

export function KnowledgeReviewList({
  view,
  summary = false,
}: {
  view: ReviewView
  summary?: boolean
}) {
  const [page, setPage] = useState(1)
  const sources = useRecord<{ items: AssignedSource[]; has_more: boolean }>(
    `${path}?page=${page}&view=${view}`,
  )
  return (
    <>
      <ReadState
        loading={sources.loading}
        error={sources.error}
        retry={sources.reload}
        advisor
      />
      {sources.data?.items.length === 0 && (
        <p role="status">
          {view === 'pending'
            ? 'No PDF versions are assigned to you.'
            : 'No reviewed PDFs are currently available.'}
        </p>
      )}
      {sources.data?.items.map((source) => (
        <article className="panel" key={source.id}>
          <h3>
            <Link to={`${path}/${source.id}`}>{source.title}</Link>
          </h3>
          <p>
            Assigned <ReviewTime value={source.assigned_at} />
          </p>
          <p>{reviewLabels[source.review.event]}</p>
        </article>
      ))}
      {!summary && sources.data && (
        <ReviewPagination
          more={sources.data.has_more}
          page={page}
          change={setPage}
        />
      )}
    </>
  )
}
