import { useState } from 'react'
import Notice from '../../components/Notice'
import { farmWrite } from '../../lib/farms'
import PdfAttribution, { type PdfProvenance } from '../knowledge/PdfAttribution'
import { useSave } from './record-hooks'

type Matches = {
  method: 'keyword' | 'hybrid'
  items: (PdfProvenance & {
    id: string
    version_id: string
    title: string
    publisher: string
    language: string
    page_number: number
    body: string
  })[]
}

export default function ReviewedSources({ path }: { path: string }) {
  const [question, setQuestion] = useState('')
  const [semantic, setSemantic] = useState(false)
  const [result, setResult] = useState<Matches | null>(null)
  const save = useSave()
  return (
    <section className="panel" aria-labelledby="reviewed-sources-heading">
      <h2 id="reviewed-sources-heading">Search reviewed PDF passages</h2>
      <form
        className="record-form"
        onSubmit={(event) => {
          event.preventDefault()
          if (!question.trim() || save.busy || save.blocked) return
          setResult(null)
          void save.run(
            () =>
              farmWrite<Matches>(`${path}/reviewed-sources/search`, 'POST', {
                question: question.trim(),
                semantic,
              }),
            setResult,
          )
        }}
      >
        <label className="field">
          Search terms or question
          <input
            value={question}
            required
            maxLength={240}
            disabled={save.busy}
            onChange={(event) => {
              setQuestion(event.target.value)
              setResult(null)
              save.reset()
            }}
          />
        </label>
        <label className="field">
          <input
            type="checkbox"
            checked={semantic}
            disabled={save.busy}
            onChange={(event) => {
              setSemantic(event.target.checked)
              setResult(null)
              save.reset()
            }}
          />
          Include semantic matches by sending the search text to Gemini
        </label>
        <button disabled={save.busy || save.blocked || !question.trim()}>
          Find passages
        </button>
      </form>
      {save.busy && <p role="status">Searching the reviewed library…</p>}
      {save.error && <Notice message={save.error} />}
      {save.blocked && <button onClick={save.reset}>Try again</button>}
      {result && (
        <div aria-label="Reviewed PDF matches" role="region">
          <p role="status">
            {result.items.length
              ? `${result.items.length} matching passages`
              : 'No matching passages found.'}
            {semantic &&
              result.method === 'keyword' &&
              ' Showing keyword results. Semantic search is currently unavailable for this search.'}
          </p>
          {result.items.map((item) => (
            <details key={item.id}>
              <summary>
                {item.title} · PDF page {item.page_number}
              </summary>
              <p className="record-note" lang={item.language}>
                {item.body}
              </p>
              <p>
                {item.publisher} · Version {item.version_id}
              </p>
              <PdfAttribution source={item} />
            </details>
          ))}
        </div>
      )}
    </section>
  )
}
