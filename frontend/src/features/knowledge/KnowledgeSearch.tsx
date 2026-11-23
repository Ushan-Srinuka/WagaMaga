import { useState } from 'react'
import Notice from '../../components/Notice'
import { useRecord } from '../farms/record-hooks'

type PageMatch = {
  version_id: string
  title: string
  checksum: string
  number: number
  excerpt: string
}

export default function KnowledgeSearch({
  sourcePath,
}: {
  sourcePath: string
}) {
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')
  const results = useRecord<PageMatch[]>(
    query ? `${sourcePath}/search?q=${encodeURIComponent(query)}` : null,
  )

  return (
    <section className="panel" aria-labelledby="knowledge-search-title">
      <h2 id="knowledge-search-title">Search published PDFs</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          const terms = input.trim()
          if (!terms) return
          if (terms === query) results.reload()
          else setQuery(terms)
        }}
      >
        <div className="field">
          <label htmlFor="knowledge-keywords">Keywords</label>
          <input
            id="knowledge-keywords"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            maxLength={160}
            placeholder="e.g. nursery"
            required
          />
        </div>
        <button disabled={!input.trim() || results.loading}>Search</button>
      </form>
      {results.loading && <p role="status">Searching published PDFs…</p>}
      {results.error !== undefined && (
        <Notice message="Search is unavailable. Try again." />
      )}
      {results.data?.length === 0 && (
        <p role="status">
          No evidence found for “{query}”. Try fewer keywords.
        </p>
      )}
      {results.data?.map((match) => (
        <article className="panel" key={`${match.version_id}:${match.number}`}>
          <h3>{match.title}</h3>
          <p>
            Page {match.number} · Version {match.version_id.slice(0, 8)}
          </p>
          <p style={{ overflowWrap: 'anywhere' }}>{match.excerpt}</p>
          <details>
            <summary>Citation details</summary>
            <p style={{ overflowWrap: 'anywhere' }}>
              Version ID: {match.version_id}
            </p>
            <p style={{ overflowWrap: 'anywhere' }}>
              SHA-256: {match.checksum}
            </p>
          </details>
        </article>
      ))}
    </section>
  )
}
