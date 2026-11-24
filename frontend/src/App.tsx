import { Navigate, Outlet, Route, Routes } from 'react-router'
import AccountShell from './app/AccountShell'
import FoundationPage from './app/FoundationPage'
import SessionProvider from './app/SessionProvider'
import { useSession } from './app/session-context'
import AccountPage from './features/account/AccountPage'
import AuthPage from './features/auth/AuthPage'
import AuditPage from './features/audit/AuditPage'
import HomePage from './features/home/HomePage'
import NotificationsPage from './features/notifications/NotificationsPage'
import UserDetailPage from './features/users/UserDetailPage'
import UsersPage from './features/users/UsersPage'
import FarmsPage, {
  FarmDetailPage,
  NewCultivationPage,
  NewFarmPage,
} from './features/farms/FarmPages'
import CultivationPage from './features/farms/CultivationPage'
import HistoryPage from './features/farms/HistoryPage'
import HelpPage from './features/support/HelpPage'
import OverviewPage from './features/reporting/OverviewPage'
import KnowledgeSourcesPage from './features/knowledge/KnowledgeSourcesPage'
import KnowledgeEvaluationPage from './features/knowledge/KnowledgeEvaluationPage'
import KnowledgeScoringPage from './features/knowledge/KnowledgeScoringPage'
import ChilliQuestionsPage from './features/knowledge/ChilliQuestionsPage'
import AdvisorCasesPage from './features/farms/AdvisorCasesPage'
import PlanReviewPage from './features/farms/PlanReviewPage'
import {
  NewSupportPage,
  SupportDetailPage,
  SupportListPage,
} from './features/support/SupportPages'
import './App.css'
import './user-management.css'
import './features/farms/farms.css'

function Protected({
  admin = false,
  farmer = false,
  advisor = false,
}: {
  admin?: boolean
  farmer?: boolean
  advisor?: boolean
}) {
  const { user, phase, restore } = useSession()
  if (phase === 'loading')
    return (
      <main className="session-state" role="status">
        Restoring your session…
      </main>
    )
  if (phase === 'offline')
    return (
      <main className="session-state">
        <h1>Let’s reconnect.</h1>
        <p role="alert">
          Your account could not be reached. Check your connection.
        </p>
        <button
          onClick={() => {
            void restore()
          }}
        >
          Try again
        </button>
      </main>
    )
  if (!user) return <Navigate to="/login" replace />
  if (admin && user.role !== 'administrator')
    return (
      <section className="panel">
        <h1>Access denied</h1>
        <p>Administrator access is required to manage other accounts.</p>
      </section>
    )
  if (farmer && user.role !== 'farmer')
    return (
      <section className="panel">
        <h1>Access denied</h1>
        <p>Farmer access is required for private farm records.</p>
      </section>
    )
  if (advisor && user.role !== 'advisor')
    return (
      <section className="panel">
        <h1>Access denied</h1>
        <p>Advisor access is required for assigned plan reviews.</p>
      </section>
    )
  return <Outlet />
}

function ProductRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage key="login" />} />
      <Route path="/register" element={<AuthPage key="register" register />} />
      <Route element={<Protected />}>
        <Route element={<AccountShell />}>
          <Route path="/account" element={<AccountPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/plan-reviews/:planId" element={<PlanReviewPage />} />
          <Route element={<Protected advisor />}>
            <Route path="/advisor/cases" element={<AdvisorCasesPage />} />
          </Route>
          <Route element={<Protected farmer />}>
            <Route path="/knowledge/chilli" element={<ChilliQuestionsPage />} />
            <Route
              path="/knowledge/chilli/guidance"
              element={<ChilliQuestionsPage key="guidance" mode="pilot" />}
            />
            {import.meta.env.DEV && (
              <Route
                path="/knowledge/chilli/demo"
                element={<ChilliQuestionsPage key="demo" mode="demo" />}
              />
            )}
            {import.meta.env.DEV && (
              <Route
                path="/knowledge/chilli/local"
                element={<ChilliQuestionsPage key="local" mode="local" />}
              />
            )}
            <Route path="/support" element={<SupportListPage />} />
            <Route path="/support/new" element={<NewSupportPage />} />
            <Route path="/support/:ticketId" element={<SupportDetailPage />} />
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/farms" element={<FarmsPage />} />
            <Route path="/farms/new" element={<NewFarmPage />} />
            <Route path="/farms/:farmId" element={<FarmDetailPage />} />
            <Route path="/farms/:farmId/history" element={<HistoryPage />} />
            <Route
              path="/farms/:farmId/cultivations/new"
              element={<NewCultivationPage />}
            />
            <Route
              path="/farms/:farmId/cultivations/:cultivationId"
              element={<CultivationPage />}
            />
            <Route
              path="/farms/:farmId/cultivations/:cultivationId/history"
              element={<HistoryPage />}
            />
            <Route
              path="/farms/:farmId/cultivations/:cultivationId/observations/:observationId/history"
              element={<HistoryPage />}
            />
          </Route>
          <Route element={<Protected admin />}>
            <Route path="/admin/overview" element={<OverviewPage />} />
            <Route path="/admin/knowledge" element={<KnowledgeSourcesPage />} />
            <Route
              path="/admin/knowledge/scoring"
              element={<KnowledgeScoringPage />}
            />
            <Route
              path="/admin/knowledge/evaluation"
              element={<KnowledgeEvaluationPage />}
            />
            <Route path="/admin/support" element={<SupportListPage admin />} />
            <Route
              path="/admin/support/:ticketId"
              element={<SupportDetailPage admin />}
            />
            <Route path="/admin/users" element={<UsersPage />} />
            <Route path="/admin/users/:id" element={<UserDetailPage />} />
            <Route path="/admin/audit" element={<AuditPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/account" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <SessionProvider>
            <HomePage />
          </SessionProvider>
        }
      />
      <Route path="/connection" element={<FoundationPage />} />
      <Route
        path="/help"
        element={
          <SessionProvider>
            <HelpPage />
          </SessionProvider>
        }
      />
      <Route
        path="*"
        element={
          <SessionProvider>
            <ProductRoutes />
          </SessionProvider>
        }
      />
    </Routes>
  )
}
