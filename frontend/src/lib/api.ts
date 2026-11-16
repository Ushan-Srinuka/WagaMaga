export async function readFoundationHealth(signal: AbortSignal) {
  const [liveResponse, readyResponse] = await Promise.all([
    fetch('/health/live', { signal }),
    fetch('/health/ready', { signal }),
  ])
  if (!liveResponse.ok || (!readyResponse.ok && readyResponse.status !== 503)) {
    throw new Error('Health check failed')
  }
  const live: unknown = await liveResponse.json()
  const ready: unknown = await readyResponse.json()
  if (
    typeof live !== 'object' ||
    live === null ||
    !('status' in live) ||
    live.status !== 'ok'
  ) {
    throw new Error('Invalid liveness response')
  }
  const databaseReady =
    readyResponse.ok &&
    typeof ready === 'object' &&
    ready !== null &&
    'status' in ready &&
    ready.status === 'ready'
  return { databaseReady }
}
