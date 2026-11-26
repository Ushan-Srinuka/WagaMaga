import { useState } from 'react'
import { Link } from 'react-router'
import ConfirmDialog from '../../components/ConfirmDialog'
import Notice from '../../components/Notice'
import { ApiError, forgetSession, request } from '../../lib/accounts'
import { farmWrite } from '../../lib/farms'
import { useRecord, useSave } from '../farms/record-hooks'
import KnowledgeAnswerPreview from './KnowledgeAnswerPreview'
import KnowledgeSearch from './KnowledgeSearch'
import PdfMetadataFields, { type PdfMetadata } from './PdfMetadataFields'
import type { SourcePassage } from './ResearchPassage'
import SourceReviewAssignment from './SourceReviewAssignment'

const path = '/admin/knowledge/sources'
const actions = {
  draft: 'review',
  reviewed: 'publish',
  published: 'withdraw',
  withdrawn: null,
  discarded: null,
  deleted: null,
} as const
type Source = {
  id: string
  title: string
  replaces_version_id?: string | null
  rag_metadata?: PdfMetadata | null
  content: string
  checksum: string
  status: keyof typeof actions
  revision: number
  processing: 'queued' | 'ready' | 'failed' | 'deleted'
  processing_error: string | null
  retryable?: boolean
  screening_required: boolean
}
type SourcePage = {
  items: Source[]
  has_more: boolean
  screened_uploads: boolean
  upload_available: boolean
}
type PdfPage = { number: number; text: string }

const pdfErrors: Record<string, string> = {
  encrypted: 'Use a PDF without password protection.',
  page_limit: 'Use a PDF with 1–100 pages.',
  text_limit: 'The extracted text exceeds the limit. Use a shorter PDF.',
  no_text: 'No selectable text was found. Scanned PDFs need OCR.',
  invalid_pdf: 'The worker could not read this PDF.',
  timed_out: 'Extraction took too long. Try a simpler PDF.',
  scan_unavailable:
    'PDF screening is temporarily unavailable. Retry after the scanner is restored.',
  scan_rejected: 'PDF screening rejected this file.',
}

const labels = {
  review: 'Mark as reviewed',
  publish: 'Publish',
  withdraw: 'Withdraw',
  discard: 'Remove PDF',
  delete: 'Delete PDF',
}
const descriptions = {
  review: 'Record that you reviewed this version and its extracted text.',
  publish: 'Publish this reviewed version in the source library.',
  withdraw: 'Change this version to Withdrawn and keep its review history.',
  discard:
    'Remove this unpublished PDF from Knowledge Sources. The stored original and decision history are retained.',
  delete:
    'Permanently delete the uploaded PDF and extracted pages. The source title, checksum and deletion history remain in the audit record; existing review decisions and approved excerpts are retained. This source will disappear from Knowledge Sources.',
}

function saveError(error: unknown) {
  if (
    error instanceof ApiError &&
    [
      'ADVISOR_REVIEW_REQUIRED',
      'PDF_SCREENING_REQUIRED',
      'PDF_SCREENING_UNAVAILABLE',
    ].includes(error.code)
  )
    return error.message
  if (error instanceof ApiError && error.status === 409)
    return 'The source status changed. Refresh the list before continuing.'
  if (
    error instanceof ApiError &&
    [408, 413, 415, 422, 429].includes(error.status)
  )
    return error.message
  return 'The change could not be confirmed. Refresh the list before trying again.'
}

function readPdfMetadata(form: HTMLFormElement): PdfMetadata | undefined {
  const fields = new FormData(form)
  if (!fields.has('publisher')) return
  return {
    publisher: String(fields.get('publisher')),
    language: String(fields.get('language')),
    crop: String(fields.get('crop')),
    region: String(fields.get('region')),
    published_on: String(fields.get('published_on') ?? '') || null,
    valid_until: String(fields.get('valid_until') ?? '') || null,
    access: fields.get('access') === 'farmers' ? 'farmers' : 'admin',
    ...(fields.has('source_url') && {
      source_url: String(fields.get('source_url')),
      reuse_basis: String(fields.get('reuse_basis')),
    }),
  }
}

async function uploadPdf(
  file: File,
  title: string,
  replaces?: string,
  metadata?: PdfMetadata,
) {
  if (file.size > 6 * 1024 * 1024)
    throw new ApiError(413, 'Use a PDF no larger than 6 MiB.')
  const params = new URLSearchParams()
  if (title.trim()) params.set('title', title.trim())
  if (replaces) params.set('replaces', replaces)
  if (metadata) params.set('metadata', JSON.stringify(metadata))
  const query = params.size ? `?${params}` : ''
  try {
    return await request<Source>(
      `${path}/pdf${query}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/pdf' },
        body: file,
      },
      { retryUnauthorized: false },
    )
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      forgetSession()
      window.dispatchEvent(new Event('account-expired'))
    }
    throw error
  }
}

function ExtractedPages({ sourceId }: { sourceId: string }) {
  const pages = useRecord<PdfPage[]>(`${path}/${sourceId}/pages`)
  if (pages.loading) return <p role="status">Loading extracted text…</p>
  if (pages.error)
    return (
      <>
        <Notice message="The extracted text could not be loaded." />
        <button onClick={pages.reload}>Try again</button>
      </>
    )
  return pages.data?.map((page) => (
    <section key={page.number}>
      <h3>Page {page.number}</h3>
      <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
        {page.text || 'No text on this page.'}
      </p>
    </section>
  ))
}

export default function KnowledgeSourcesPage() {
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<{
    source: Source
    action: keyof typeof labels
  } | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [replacement, setReplacement] = useState<Source | null>(null)
  const [metadataEnabled, setMetadataEnabled] = useState(false)
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [reviewId, setReviewId] = useState<string | null>(null)
  const [searchVersion, setSearchVersion] = useState(0)
  const sources = useRecord<SourcePage>(`${path}?page=${page}`)
  const references = useRecord<SourcePassage[]>(`${path}/references`)
  const save = useSave(saveError)
  const action = selected?.action
  const screened = Boolean(sources.data?.screened_uploads)
  const uploadAvailable = sources.data?.upload_available !== false

  function refresh() {
    setSelected(null)
    setReviewId(null)
    save.reset()
    sources.reload()
    setSearchVersion((version) => version + 1)
  }

  return (
    <>
      <div className="page-intro">
        <h1>Knowledge Sources</h1>
        <p>
          Browse the published chilli references and manage PDF source versions.
        </p>
        <Link to="/admin/knowledge/evaluation">
          Review the 10 chilli questions
        </Link>
      </div>
      <section className="panel" aria-label="Published chilli references">
        <h2>Published chilli references</h2>
        {references.loading && <p role="status">Loading reference passages…</p>}
        {references.error !== undefined && (
          <Notice message="The published references could not be loaded." />
        )}
        {references.data?.map(
          ({ id, question, citation, source_note, corpus_version }) => (
            <details key={id}>
              <summary>{question}</summary>
              <p>{source_note}</p>
              <p>
                <a href={citation.url} target="_blank" rel="noreferrer">
                  {citation.title}
                </a>
                {' · '}
                {citation.publisher}
                {' · '}
                {'section' in citation
                  ? citation.section
                  : `PDF page ${citation.pdf_page}`}
              </p>
              <small>
                {corpus_version} · {id}
              </small>
            </details>
          ),
        )}
      </section>
      <KnowledgeSearch sourcePath={path} key={`search-${searchVersion}`} />
      {!screened && (
        <KnowledgeAnswerPreview
          sourcePath={path}
          key={`answer-${searchVersion}`}
        />
      )}
      <section
        className="panel"
        aria-label={screened ? 'Source versions' : 'Synthetic source versions'}
      >
        <div className="button-row">
          {!screened && (
            <>
              <button
                className="primary"
                disabled={save.busy || save.blocked || sources.loading}
                onClick={() => {
                  void save.run(
                    () =>
                      farmWrite<Source>(path, 'POST', {
                        template: 'chilli-demo',
                      }),
                    () => {
                      setPage(1)
                      sources.reload()
                    },
                  )
                }}
              >
                Add synthetic guide
              </button>
              <button
                disabled={save.busy || save.blocked || sources.loading}
                onClick={() => {
                  void save.run(
                    () =>
                      farmWrite<Source>(path, 'POST', {
                        template: 'gemini-preview-pdf',
                      }),
                    () => {
                      setPage(1)
                      sources.reload()
                    },
                  )
                }}
              >
                Add Gemini demo PDF
              </button>
            </>
          )}
          <button disabled={save.busy} onClick={refresh}>
            Refresh sources
          </button>
        </div>
        {!uploadAvailable && (
          <Notice message="PDF screening is not configured for this installation." />
        )}
        {uploadAvailable && (
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (!file) return
              const form = event.currentTarget
              const metadata = readPdfMetadata(form)
              void save.run(
                () => uploadPdf(file, title, replacement?.id, metadata),
                () => {
                  form.reset()
                  setFile(null)
                  setTitle('')
                  setReplacement(null)
                  setMetadataEnabled(false)
                  setPage(1)
                  sources.reload()
                },
              )
            }}
          >
            {replacement && (
              <p role="status">
                Replacing <strong>{replacement.title}</strong>. The current PDF
                stays published until the replacement is reviewed and published.{' '}
                <button
                  type="button"
                  disabled={save.busy}
                  onClick={() => {
                    setReplacement(null)
                    setTitle('')
                    setMetadataEnabled(false)
                  }}
                >
                  Cancel replacement
                </button>
              </p>
            )}
            <div className="field">
              <label htmlFor="knowledge-title">Source title</label>
              <input
                id="knowledge-title"
                value={title}
                maxLength={120}
                required={screened}
                disabled={save.busy}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>
            {!screened && (
              <label className="field">
                <input
                  type="checkbox"
                  checked={metadataEnabled}
                  disabled={save.busy}
                  onChange={(event) => setMetadataEnabled(event.target.checked)}
                />
                Include in the reviewed PDF library
              </label>
            )}
            {(screened || metadataEnabled) && (
              <PdfMetadataFields
                key={replacement?.id}
                previous={replacement?.rag_metadata}
                screened={screened}
              />
            )}
            <div className="field">
              <label htmlFor="knowledge-pdf">
                {screened ? 'Source PDF' : 'Synthetic PDF'}
              </label>
              <input
                id="knowledge-pdf"
                type="file"
                accept=".pdf,application/pdf"
                disabled={save.busy}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <small>
                Up to 6 MiB and 100 pages. Use a PDF with selectable text.
              </small>
            </div>
            <button disabled={!file || save.busy || save.blocked}>
              Upload PDF
            </button>
          </form>
        )}
        {!selected && save.error && <Notice message={save.error} />}
        {sources.loading && <p role="status">Loading source versions…</p>}
        {sources.error !== undefined && (
          <Notice message="Source versions could not be loaded." />
        )}
        {sources.data?.items.length === 0 && (
          <p>
            {screened
              ? 'Upload a source PDF to start.'
              : 'Add a synthetic guide to start.'}
          </p>
        )}
        {sources.data?.items.map((source) => {
          const screenedVersion = !source.content && source.screening_required
          const canReview =
            !screened || Boolean(source.content) || screenedVersion
          const next =
            source.processing === 'ready' &&
            (canReview || source.status === 'published')
              ? actions[source.status]
              : null
          return (
            <article className="panel knowledge-source-version" key={source.id}>
              <h2>{source.title}</h2>
              <p>
                Status: <strong>{source.status}</strong> · Version{' '}
                {source.id.slice(0, 8)}
              </p>
              {source.content ? (
                <p>{source.content}</p>
              ) : source.processing === 'queued' ? (
                <p>
                  {screenedVersion
                    ? 'Waiting for screening and text extraction.'
                    : 'Waiting for text extraction.'}{' '}
                  Refresh sources to check progress.
                </p>
              ) : source.processing === 'failed' ? (
                <Notice
                  message={
                    pdfErrors[source.processing_error ?? ''] ??
                    'Text extraction failed. Try a new PDF.'
                  }
                />
              ) : (
                <>
                  <button
                    aria-expanded={previewId === source.id}
                    onClick={() =>
                      setPreviewId(previewId === source.id ? null : source.id)
                    }
                  >
                    {previewId === source.id
                      ? 'Hide extracted text'
                      : 'View extracted text'}
                  </button>
                  {previewId === source.id && (
                    <ExtractedPages sourceId={source.id} />
                  )}
                  {source.status === 'draft' && (
                    <p>
                      <Link
                        to={`/admin/knowledge/evaluation?draft=${source.id}`}
                      >
                        Preview Sinhala matches for chilli questions
                      </Link>
                    </p>
                  )}
                </>
              )}
              <details>
                <summary>Version details</summary>
                <p className="record-note">Source version · {source.id}</p>
                {source.replaces_version_id && (
                  <p>
                    Replaces version {source.replaces_version_id.slice(0, 8)}
                  </p>
                )}
                {source.rag_metadata && (
                  <dl>
                    <dt>Publisher</dt>
                    <dd>{source.rag_metadata.publisher}</dd>
                    <dt>Language</dt>
                    <dd>{source.rag_metadata.language}</dd>
                    <dt>Crop and region</dt>
                    <dd>
                      {source.rag_metadata.crop} · {source.rag_metadata.region}
                    </dd>
                    <dt>Publication date</dt>
                    <dd>{source.rag_metadata.published_on ?? 'Unknown'}</dd>
                    <dt>Valid until</dt>
                    <dd>{source.rag_metadata.valid_until ?? 'Unspecified'}</dd>
                    {source.rag_metadata.reuse_basis && (
                      <>
                        <dt>Reuse basis</dt>
                        <dd>{source.rag_metadata.reuse_basis}</dd>
                      </>
                    )}
                    {source.rag_metadata.source_url && (
                      <>
                        <dt>Original source</dt>
                        <dd>
                          <a
                            href={source.rag_metadata.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open publisher source
                          </a>
                        </dd>
                      </>
                    )}
                    <dt>Library access</dt>
                    <dd>
                      {source.rag_metadata.access === 'farmers'
                        ? 'Matching cultivations'
                        : 'Administrators only'}
                    </dd>
                  </dl>
                )}
                <p style={{ overflowWrap: 'anywhere' }}>
                  SHA-256: {source.checksum}
                </p>
              </details>
              {!source.content &&
                source.processing === 'ready' &&
                source.status === 'draft' &&
                canReview && (
                  <details
                    open={reviewId === source.id}
                    onToggle={(event) => {
                      const open = event.currentTarget.open
                      setReviewId((current) =>
                        open
                          ? source.id
                          : current === source.id
                            ? null
                            : current,
                      )
                    }}
                  >
                    <summary>Advisor review</summary>
                    {screenedVersion && (
                      <p>
                        Assign an advisor before marking this version as
                        reviewed.
                      </p>
                    )}
                    {reviewId === source.id && (
                      <SourceReviewAssignment
                        path={`${path}/${source.id}/advisor-review`}
                      />
                    )}
                  </details>
                )}
              {next && (
                <button
                  className="primary"
                  disabled={save.busy || save.blocked}
                  onClick={() => setSelected({ source, action: next })}
                >
                  {labels[next]}
                </button>
              )}
              {source.retryable && (
                <button
                  type="button"
                  disabled={save.busy || save.blocked}
                  onClick={() =>
                    void save.run(
                      () =>
                        farmWrite<Source>(
                          `${path}/${source.id}/retry-pdf`,
                          'POST',
                          {},
                        ),
                      sources.reload,
                    )
                  }
                >
                  {screenedVersion
                    ? 'Retry PDF screening and extraction'
                    : 'Retry PDF extraction'}
                </button>
              )}
              {uploadAvailable &&
                !source.content &&
                source.status === 'published' && (
                  <button
                    type="button"
                    disabled={save.busy || save.blocked}
                    onClick={() => {
                      setReplacement(source)
                      setTitle(source.title)
                      setMetadataEnabled(Boolean(source.rag_metadata))
                      document.getElementById('knowledge-title')?.focus()
                    }}
                  >
                    Upload replacement PDF
                  </button>
                )}
              {!source.content &&
                ['draft', 'reviewed'].includes(source.status) && (
                  <button
                    className="danger-button"
                    disabled={save.busy || save.blocked}
                    onClick={() => setSelected({ source, action: 'discard' })}
                  >
                    Remove PDF
                  </button>
                )}
              {!source.content && source.status === 'withdrawn' && (
                <button
                  className="danger-button"
                  disabled={save.busy || save.blocked}
                  onClick={() => setSelected({ source, action: 'delete' })}
                >
                  Delete PDF
                </button>
              )}
            </article>
          )
        })}
        <div className="button-row" aria-label="Source pages">
          {page > 1 && (
            <button disabled={save.busy} onClick={() => setPage(page - 1)}>
              Previous
            </button>
          )}
          {sources.data?.has_more && (
            <button disabled={save.busy} onClick={() => setPage(page + 1)}>
              Next
            </button>
          )}
        </div>
      </section>
      {selected && action && (
        <ConfirmDialog
          eyebrow="Knowledge source"
          title={labels[action]}
          description={
            action === 'publish' && selected.source.replaces_version_id
              ? 'Publish this reviewed PDF and withdraw the previous version in the same operation.'
              : descriptions[action]
          }
          confirmLabel={labels[action]}
          busy={save.busy}
          error={save.error}
          confirmDisabled={save.blocked}
          onClose={() => setSelected(null)}
          onConfirm={() => {
            void save.run(
              () =>
                farmWrite<Source>(
                  `${path}/${selected.source.id}/${action}`,
                  'POST',
                  {
                    expected_revision: selected.source.revision,
                  },
                ),
              () => {
                if (action === 'discard') setPreviewId(null)
                setSelected(null)
                sources.reload()
                setSearchVersion((version) => version + 1)
              },
            )
          }}
        />
      )}
    </>
  )
}
