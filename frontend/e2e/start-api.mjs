import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
const python = path.join(
  backend,
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
)
const child = spawn(python, ['tests/browser_server.py'], {
  cwd: backend,
  stdio: 'inherit',
  env: process.env,
})
child.on('error', () => {
  console.error(
    'Browser API could not start. Install backend dependencies first.',
  )
  process.exitCode = 1
})
child.on('exit', (code) => {
  process.exitCode = code ?? 1
})
for (const signal of ['SIGTERM', 'SIGINT'])
  process.on(signal, () => child.kill(signal))
