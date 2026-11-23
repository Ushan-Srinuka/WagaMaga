import { useState } from 'react'
import { Link } from 'react-router'
import ConfirmDialog from '../../components/ConfirmDialog'
import Notice from '../../components/Notice'
import { ApiError, forgetSession, request } from '../../lib/accounts'
import { farmWrite } from '../../lib/farms'
import { useRecord, useSave } from '../farms/record-hooks'
import KnowledgeAnswerPreview from './KnowledgeAnswerPreview'
import KnowledgeSearch from './KnowledgeSearch'

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
  content: string
  checksum: string
  status: keyof typeof actions
  revision: number
  processing: 'queued' | 'ready' | 'failed' | 'deleted'
  processing_error: string | null
}
type SourcePage = { items: Source[]; has_more: boolean }
type PdfPage = { number: number; text: string }

const pdfErrors: Record<string, string> = {
  encrypted: 'Use a PDF without password protection.',
  page_limit: 'Use a PDF with 1–100 pages.',
  text_limit: 'The extracted text exceeds the demo limit. Use a shorter PDF.',
  no_text: 'No selectable text was found. Scanned PDFs need OCR.',
  invalid_pdf: 'The worker could not read this PDF.',
  timed_out: 'Extraction took too long. Try a simpler PDF.',
}

const labels = {
  review: 'Mark as reviewed',
  publish: 'Publish',
  withdraw: 'Withdraw',
  discard: 'Remove PDF',
  delete: 'Delete PDF',
}
const descriptions = {
  review:
    'Record that you reviewed the displayed version of this synthetic guide.',
  publish: 'Publish this reviewed version within the demonstration.',
  withdraw: 'Change this version to Withdrawn and keep its review history.',
  discard:
    'Remove this unpublished PDF from Knowledge Sources. The stored original and decision history are retained.',
  delete:
    'Permanently delete the uploaded PDF and extracted pages. The source title, checksum and deletion history remain in the audit record; existing review decisions and approved excerpts are retained. This source will disappear from Knowledge Sources.',
}

function saveError(error: unknown) {
  if (error instanceof ApiError && error.status === 409)
    return 'The source status changed. Refresh the list before continuing.'
  if (error instanceof ApiError && [408, 413, 415, 422].includes(error.status))
    return error.status === 422 ? 'Choose a valid PDF file.' : error.message
  return 'The change could not be confirmed. Refresh the list before trying again.'
}

async function uploadPdf(file: File) {
  if (file.size > 6 * 1024 * 1024)
    throw new ApiError(413, 'Use a PDF no larger than 6 MiB.')
  try {
    return await request<Source>(
      `${path}/pdf`,
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
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [searchVersion, setSearchVersion] = useState(0)
  const sources = useRecord<SourcePage>(`${path}?page=${page}`)
  const save = useSave(saveError)
  const action = selected?.action

  function refresh() {
    setSelected(null)
    save.reset()
    sources.reload()
    setSearchVersion((version) => version + 1)
  }

  return (
    <>
      <div className="page-intro">
        <h1>Knowledge Sources</h1>
        <p>Add a fictional guide or upload a synthetic PDF for review.</p>
        <Link to="/admin/knowledge/evaluation">
          Review the 10 chilli questions
        </Link>
      </div>
      <KnowledgeSearch sourcePath={path} key={`search-${searchVersion}`} />
      <KnowledgeAnswerPreview
        sourcePath={path}
        key={`answer-${searchVersion}`}
      />
      <section className="panel" aria-label="Synthetic source versions">
        <div className="button-row">
          <button
            className="primary"
            disabled={save.busy || save.blocked || sources.loading}
            onClick={() => {
              void save.run(
                () =>
                  farmWrite<Source>(path, 'POST', { template: 'chilli-demo' }),
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
          <button disabled={save.busy} onClick={refresh}>
            Refresh sources
          </button>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!file) return
            const form = event.currentTarget
            void save.run(
              () => uploadPdf(file),
              () => {
                form.reset()
                setFile(null)
                setPage(1)
                sources.reload()
              },
            )
          }}
        >
          <div className="field">
            <label htmlFor="knowledge-pdf">Synthetic PDF</label>
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
        {!selected && save.error && <Notice message={save.error} />}
        {sources.loading && <p role="status">Loading source versions…</p>}
        {sources.error !== undefined && (
          <Notice message="Source versions could not be loaded." />
        )}
        {sources.data?.items.length === 0 && (
          <p>Add a synthetic guide to start.</p>
        )}
        {sources.data?.items.map((source) => {
          const next =
            source.processing === 'ready' ? actions[source.status] : null
          return (
            <article className="panel" key={source.id}>
              <h2>{source.title}</h2>
              <p>
                Status: <strong>{source.status}</strong> · Version{' '}
                {source.id.slice(0, 8)}
              </p>
              {source.content ? (
                <p>{source.content}</p>
              ) : source.processing === 'queued' ? (
                <p>
                  Waiting for text extraction. Refresh sources to check
                  progress.
                </p>
              ) : source.processing === 'failed' ? (
                <Notice
                  message={
                    pdfErrors[source.processing_error ?? ''] ??
                    'Text extraction failed. Try a new synthetic PDF.'
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
                <p style={{ overflowWrap: 'anywhere' }}>
                  SHA-256: {source.checksum}
                </p>
              </details>
              {next && (
                <button
                  className="primary"
                  disabled={save.busy || save.blocked}
                  onClick={() => setSelected({ source, action: next })}
                >
                  {labels[next]}
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
          description={descriptions[action]}
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
