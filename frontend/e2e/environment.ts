// Separate loopback ports let browser checks coexist with a developer's app.
function port(value: string | undefined, fallback: number) {
  const parsed = Number(value ?? fallback)
  if (!Number.isInteger(parsed) || parsed < 1024 || parsed > 65535)
    throw new Error('E2E ports must be integers between 1024 and 65535')
  return parsed
}
export const apiPort = port(process.env.E2E_API_PORT, 8000)
export const webPort = port(process.env.E2E_WEB_PORT, 5173)
export const webOrigin = `http://127.0.0.1:${webPort}`
export const apiRoot = `http://127.0.0.1:${apiPort}/api/v1`
