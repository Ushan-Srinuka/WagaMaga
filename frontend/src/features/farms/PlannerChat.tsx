import { useState } from 'react'
import { Link } from 'react-router'
import Notice from '../../components/Notice'
import {
  farmWrite,
  timestamp,
  weeklyPlanStatus,
  type PlannerWeek,
  type WeeklyPlan,
  type WeekTask,
} from '../../lib/farms'
import { useSave } from './record-hooks'
import WeeklySuggestion from './WeeklySuggestion'

const questions = [
  'What’s due this week?',
  'What did I miss?',
  'Why was a date suggested?',
]

type Answer = {
  message: string
  tasks: PlannerWeek | null
  plan: WeeklyPlan | null
}

export default function PlannerChat({
  path,
  planPath,
  timezone,
  archived,
  blocked,
  changed,
}: {
  path: string
  planPath: string
  timezone: string
  archived: boolean
  blocked: boolean
  changed: () => void
}) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [review, setReview] = useState<WeekTask | null>(null)
  const [notice, setNotice] = useState('')
  const save = useSave()

  function ask(text: string, taskId?: string) {
    if (!text.trim() || save.busy || save.blocked) return
    setQuestion(text)
    setReview(null)
    setNotice('')
    setAnswer(null)
    void save.run(
      () =>
        farmWrite<Answer>(`${path}/week/ask`, 'POST', {
          question: text.trim(),
          task_id: taskId,
        }),
      setAnswer,
    )
  }

  return (
    <section className="record-inset" aria-label="Ask about my tasks">
      <h3>Ask about my tasks</h3>
      <p className="muted">
        Ask what is due, what you missed, or why a task date was suggested.
      </p>
      <form
        className="record-form"
        onSubmit={(event) => {
          event.preventDefault()
          ask(question)
        }}
      >
        <label htmlFor="planner-question">Your planner question</label>
        <input
          id="planner-question"
          value={question}
          maxLength={240}
          required
          disabled={save.busy}
          onChange={(event) => {
            setQuestion(event.target.value)
            setAnswer(null)
            setReview(null)
            setNotice('')
            save.reset()
          }}
        />
        <button disabled={!question.trim() || save.busy || save.blocked}>
          Ask planner
        </button>
      </form>
      <div
        className="button-row"
        role="group"
        aria-label="Planner example questions"
      >
        {questions.map((example) => (
          <button
            type="button"
            key={example}
            disabled={save.busy || save.blocked}
            onClick={() => ask(example)}
          >
            {example}
          </button>
        ))}
      </div>
      {save.busy && <p role="status">Reading your saved planner…</p>}
      {save.error && <Notice message={save.error} />}
      {save.blocked && (
        <button type="button" onClick={save.reset}>
          Try again
        </button>
      )}
      {notice && <p role="status">{notice}</p>}
      {answer && (
        <div aria-label="Planner answer" role="region">
          <p role="status">{answer.message}</p>
          {answer.tasks && answer.tasks.items.length > 0 && (
            <>
              <ul>
                {answer.tasks.items.map((task) => (
                  <li key={task.id}>
                    <strong>{task.title}</strong> · {task.due_date}
                    {task.status !== 'pending' && <> · {task.status}</>}
                    <div className="button-row">
                      <button
                        type="button"
                        onClick={() => ask(questions[2], task.id)}
                      >
                        Explain suggested date
                      </button>
                      {!archived && task.rain_alert && (
                        <button
                          type="button"
                          disabled={blocked}
                          onClick={() => setReview(task)}
                        >
                          Review date options
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
              {answer.tasks.total > answer.tasks.items.length && (
                <p>
                  Showing {answer.tasks.items.length} tasks. Open the seven-day
                  planner for the full list.
                </p>
              )}
            </>
          )}
          {answer.plan && (
            <>
              <p>
                <strong>{answer.plan.title}</strong> ·{' '}
                {answer.plan.current_due_date} → {answer.plan.proposed_due_date}
              </p>
              <p>
                {weeklyPlanStatus[answer.plan.state]}
                {answer.plan.forecast_fetched_at &&
                  ` · Forecast saved ${timestamp(answer.plan.forecast_fetched_at, timezone)}`}
              </p>
              <Link to={`/plan-reviews/${answer.plan.id}`}>
                Open plan review
              </Link>
            </>
          )}
        </div>
      )}
      {review && !archived && !blocked && (
        <WeeklySuggestion
          key={review.id}
          task={review}
          taskPath={`${path}/tasks`}
          planPath={planPath}
          timezone={timezone}
          close={() => setReview(null)}
          changed={(outcome) => {
            setReview(null)
            setAnswer(null)
            setNotice(
              outcome === 'accepted'
                ? 'Task date updated.'
                : 'Suggestion declined.',
            )
            changed()
          }}
        />
      )}
    </section>
  )
}
