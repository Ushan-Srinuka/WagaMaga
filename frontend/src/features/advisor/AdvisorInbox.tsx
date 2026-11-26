import { Link } from 'react-router'
import { AdvisorCaseList } from '../farms/AdvisorCasesPage'
import { KnowledgeReviewList } from '../knowledge/AdvisorKnowledgePage'

export default function AdvisorInbox() {
  return (
    <div className="farm-records">
      <div className="page-intro">
        <h1>Advisor inbox</h1>
        <p>Review assigned plans and knowledge sources.</p>
      </div>
      <section aria-label="Plan reviews">
        <h2>Plan reviews</h2>
        <Link to="/advisor/cases">All plan reviews</Link>
        <AdvisorCaseList view="pending" summary />
      </section>
      <section aria-label="Knowledge reviews">
        <h2>Knowledge reviews</h2>
        <Link to="/advisor/knowledge">All knowledge reviews</Link>
        <KnowledgeReviewList view="pending" summary />
      </section>
    </div>
  )
}
