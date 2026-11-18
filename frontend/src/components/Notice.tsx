export default function Notice({
  message,
  success = false,
}: {
  message: string
  success?: boolean
}) {
  return (
    <p
      className={`form-notice ${success ? 'success' : ''}`}
      role={success ? 'status' : 'alert'}
    >
      {message}
    </p>
  )
}
