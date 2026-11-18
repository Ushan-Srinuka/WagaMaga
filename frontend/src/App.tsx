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
import './App.css'
import './user-management.css'

function Protected({ admin = false }: { admin?: boolean }) {
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
          <Route element={<Protected admin />}>
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
