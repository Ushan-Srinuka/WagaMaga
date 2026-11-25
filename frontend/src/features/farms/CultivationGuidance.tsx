import { useState } from 'react'
import { Link } from 'react-router'
import Notice from '../../components/Notice'
import { farmWrite, timestamp, type SoilMoisture } from '../../lib/farms'
import ResearchPassage from '../knowledge/ResearchPassage'
import { useSave } from './record-hooks'

const questions = {
  'nursery-setup': 'What should I check for my chilli nursery?',
  'irrigation-checks': 'What should I check before watering this plot?',
  'soil-test': 'What soil testing do I need before choosing fertilizer?',
}
type Topic = keyof typeof questions
type Answer = {
  answer: string | null
  citation: { section: string; url: string } | null
  passage_id: string | null
  corpus_version: string
  confirmed_stage: string | null
  soil_moisture: { value: SoilMoisture; observed_at: string } | null
  missing: string[]
  timezone: string
}

export default function CultivationGuidance({ path }: { path: string }) {
  const [topic, setTopic] = useState<Topic>('irrigation-checks')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const save = useSave()
  return (
    <section className="panel" aria-label="Chilli growing help">
      <h2>Chilli guidance for this cultivation</h2>
      <p className="muted">
        Scope · Chilli cultivations recorded in Anuradhapura District.
      </p>
      <p>
        Check what the published source supports alongside your crop stage and
        observations.
      </p>
      <form
        className="record-form"
        onSubmit={(event) => {
          event.preventDefault()
          if (save.busy) return
          setAnswer(null)
          void save.run(
            () => farmWrite<Answer>(path, 'POST', { topic }),
            setAnswer,
          )
        }}
      >
        <div className="field">
          <label htmlFor="cultivation-guidance-topic">
            Choose a chilli question
          </label>
          <select
            id="cultivation-guidance-topic"
            value={topic}
            disabled={save.busy}
            onChange={(event) => {
              setTopic(event.target.value as Topic)
              setAnswer(null)
              save.reset()
            }}
          >
            {Object.entries(questions).map(([id, question]) => (
              <option key={id} value={id}>
                {question}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={save.busy || save.blocked}>
          Check guidance
        </button>
      </form>
      {save.busy && <p role="status">Checking the cultivation record…</p>}
      {save.error && <Notice message={save.error} />}
      {save.blocked && (
        <button type="button" onClick={save.reset}>
          Try again
        </button>
      )}
      {answer && (
        <article
          className="record-inset"
          aria-label="Cultivation guidance answer"
          aria-live="polite"
        >
          {answer.confirmed_stage && (
            <p>Recorded crop stage: {answer.confirmed_stage}</p>
          )}
          {answer.soil_moisture && (
            <p>
              Recorded soil moisture: {answer.soil_moisture.value} ·{' '}
              {timestamp(answer.soil_moisture.observed_at, answer.timezone)}
            </p>
          )}
          <p>{answer.answer ?? 'No evidence found for this cultivation.'}</p>
          {answer.passage_id && (
            <ResearchPassage
              id={answer.passage_id}
              version={answer.corpus_version}
            />
          )}
          <h3>What to check</h3>
          <ul>
            {answer.missing.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {answer.citation && (
            <a
              href={answer.citation.url}
              target="_blank"
              rel="noreferrer"
              hrefLang="si"
            >
              Department of Agriculture · {answer.citation.section}
            </a>
          )}
        </article>
      )}
      <Link className="record-link" to="/knowledge/chilli">
        Ask a chilli question
      </Link>
    </section>
  )
}
