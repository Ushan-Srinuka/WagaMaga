import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../../App'
import { SessionContext } from '../../app/session-context'
import { ApiError, request, type Account } from '../../lib/accounts'
import type { Cultivation, Farm, Observation, Page } from '../../lib/farms'
import FarmsPage, { FarmDetailPage } from './FarmPages'
import CultivationPage from './CultivationPage'
import HistoryPage from './HistoryPage'
import { FarmForm } from './RecordUI'
import FarmActionBar from '../home/FarmActionBar'

const user: Account = {
  id: 'owner',
  display_name: 'Synthetic farmer',
  email: 'owner@example.com',
  role: 'farmer',
  disabled_at: null,
  deleted_at: null,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
}
const farm: Farm = {
  id: 'farm-one',
  farmer_id: 'owner',
  name: 'Synthetic private farm',
  location: 'Synthetic location',
  timezone: 'Asia/Colombo',
  latitude: null,
  longitude: null,
  area_value: '1.123456',
  area_unit: 'ha',
  archived_at: null,
  effective_archived: false,
  version: 4,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}
const cultivation: Cultivation = {
  id: 'cult-one',
  farm_id: farm.id,
  crop_type_id: 'chilli',
  planting_date: '2099-01-01',
  area_value: '1',
  area_unit: 'ha',
  soil_notes: null,
  estimated_stage: null,
  confirmed_stage: null,
  confirmed_by: null,
  confirmed_at: null,
  archived_at: null,
  effective_archived: false,
  planned: true,
  version: 2,
  created_at: farm.created_at,
  updated_at: farm.updated_at,
}
const observation: Observation = {
  id: 'obs-one',
  cultivation_id: cultivation.id,
  observed_at: '2026-01-01T05:00:00.123456Z',
  notes: '<b>Literal field note</b>',
  recorded_by: user.id,
  version: 3,
  effective_archived: false,
  created_at: farm.created_at,
  updated_at: farm.updated_at,
}
function page<T>(items: T[], total = items.length): Page<T> {
  return { items, total, page: 1, page_size: 20 }
}
function reads(path: string): unknown {
  const route = path.split('?')[0]
  if (route === '/notifications') return { ...page([]), unread_count: 0 }
  if (route === '/crop-types')
    return page([
      { id: 'chilli', code: 'chilli', display_name: 'Chilli', supported: true },
    ])
  if (route === '/farms') return page([farm])
  if (route === '/farms/farm-one') return farm
  if (route === '/farms/farm-one/cultivations') return page([cultivation])
  if (route === '/farms/farm-one/cultivations/cult-one') return cultivation
  if (route === '/farms/farm-one/cultivations/cult-one/tasks') return page([])
  if (route === '/farms/farm-one/cultivations/cult-one/chilli-chats')
    return page([])
  if (route === '/farms/farm-one/cultivations/cult-one/task-plans')
    return { plan: null }
  if (route === '/farms/farm-one/cultivations/cult-one/weather')
    return {
      status: 'needs_coordinates',
      location: farm.location,
      timezone: farm.timezone,
      can_refresh: false,
      forecast: null,
    }
  if (route === '/farms/farm-one/cultivations/cult-one/weather/alerts')
    return {
      ...page([]),
      rule: { threshold_mm: null, version: 0 },
      can_edit: true,
      forecast_fresh: false,
    }
  if (route === '/farms/farm-one/cultivations/cult-one/demo-weather')
    return {
      source: 'fixture',
      location: farm.location,
      timezone: farm.timezone,
      forecast_date: '2099-01-01',
      rainfall_mm: 18,
      review_due_on: '2099-01-01',
    }
  if (route === '/cultivations/cult-one/observations')
    return page([observation])
  throw new Error(`Unexpected synthetic request: ${path}`)
}
let handle: (path: string, init?: RequestInit) => unknown = reads
vi.mock('../../lib/accounts', async (original) => ({
  ...(await original<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
  restoreSession: vi.fn().mockImplementation(async () => ({
    access_token: 'synthetic',
    expires_in: 900,
    user,
  })),
}))
beforeEach(() => {
  vi.clearAllMocks()
  handle = reads
  vi.mocked(request).mockImplementation(
    async <T,>(path: string, init?: RequestInit) =>
      (await handle(path, init)) as T,
  )
})
afterEach(() => vi.unstubAllGlobals())
function wrap(element: React.ReactNode, initial = '/') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <SessionContext.Provider
        value={{ user, phase: 'ready', setUser: vi.fn(), restore: vi.fn() }}
      >
        {element}
      </SessionContext.Provider>
    </MemoryRouter>,
  )
}
function cultPage(query = '') {
  return wrap(
    <Routes>
      <Route
        path="/farms/:farmId/cultivations/:cultivationId"
        element={<CultivationPage />}
      />
    </Routes>,
    `/farms/farm-one/cultivations/cult-one${query}`,
  )
}

it('keeps task editing available when the demo forecast cannot load', async () => {
  handle = (path) => {
    if (path.endsWith('/demo-weather')) throw new ApiError(503, 'Unavailable')
    return reads(path)
  }
  cultPage()
  fireEvent.click(
    await screen.findByRole('button', { name: 'Show demo weather' }),
  )
  expect(await screen.findByText('Demo weather is unavailable.')).toBeVisible()
  const addTask = screen.getByRole('button', { name: 'Add task' })
  await waitFor(() => expect(addTask).toBeEnabled())
  fireEvent.click(addTask)
  expect(screen.getByLabelText('Task title')).toBeVisible()
  expect(
    screen.queryByRole('button', { name: 'Review this task' }),
  ).not.toBeInTheDocument()
})

it('shows a task validation error and sends only one write for repeated submits', async () => {
  let rejectSave: (reason: ApiError) => void = () => {}
  const pendingSave = new Promise((_, reject) => {
    rejectSave = reject
  })
  handle = (path, init) =>
    init?.method === 'POST' && path.endsWith('/tasks')
      ? pendingSave
      : reads(path)
  cultPage()
  const add = await screen.findByRole('button', { name: 'Add task' })
  await waitFor(() => expect(add).toBeEnabled())
  fireEvent.click(add)
  const title = screen.getByLabelText('Task title')
  fireEvent.change(title, { target: { value: 'Check plot markers' } })
  fireEvent.change(screen.getByLabelText('Due date'), {
    target: { value: '2099-01-16' },
  })
  const form = title.closest('form')!
  fireEvent.submit(form)
  fireEvent.submit(form)
  const writes = vi
    .mocked(request)
    .mock.calls.filter(
      ([path, init]) => path.endsWith('/tasks') && init?.method === 'POST',
    )
  expect(writes).toHaveLength(1)
  rejectSave(new ApiError(422, 'Check the form fields.'))
  expect(await screen.findByText('Check the form fields.')).toBeVisible()
  expect(title).toHaveValue('Check plot markers')
  expect(screen.getByRole('button', { name: 'Save task' })).toBeEnabled()
})

function chooseCrop() {
  return wrap(
    <Routes>
      <Route path="/" element={<FarmActionBar action="note" />} />
      <Route
        path="/farms/:farmId/cultivations/:cultivationId"
        element={<CultivationPage />}
      />
    </Routes>,
  )
}
it('offers farm setup when there are no active farms', async () => {
  handle = () => page([])
  chooseCrop()
  expect(
    await screen.findByRole('link', { name: 'Add your first farm' }),
  ).toHaveAttribute('href', '/farms/new')
})
it('retries a failed farm read before offering setup', async () => {
  handle = () => {
    throw new ApiError(503, 'Unavailable')
  }
  chooseCrop()
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'could not be loaded',
  )
  handle = () => page([])
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(
    await screen.findByRole('link', { name: 'Add your first farm' }),
  ).toBeVisible()
})
it('opens the next field note even when the crop already has notes', async () => {
  chooseCrop()
  await waitFor(() =>
    expect(screen.getByLabelText('What did you see?')).toHaveFocus(),
  )
  expect(screen.getByLabelText('Observed at (device time)')).not.toHaveValue('')
  expect(screen.queryByRole('heading', { name: 'Farm tasks' })).toBeNull()
})
it('asks which farm and crop to use when there are several', async () => {
  handle = (path) =>
    path.split('?')[0] === '/farms'
      ? page([farm, { ...farm, id: 'two', name: 'Second farm' }])
      : path.startsWith('/farms/two/cultivations')
        ? page([
            cultivation,
            { ...cultivation, id: 'second', planting_date: '2026-01-02' },
          ])
        : reads(path)
  chooseCrop()
  fireEvent.click(await screen.findByRole('button', { name: /Second farm/ }))
  expect(
    await screen.findByRole('link', { name: /2026-01-02/ }),
  ).toHaveAttribute(
    'href',
    '/farms/two/cultivations/second?view=notes&observe=1',
  )
})
it('creates a district/village description without guessing coordinates or requesting device location', async () => {
  const geolocation = { getCurrentPosition: vi.fn() }
  vi.stubGlobal('navigator', { geolocation })
  handle = () => farm
  wrap(<FarmForm saved={vi.fn()} review="/farms" />)
  expect(screen.getByLabelText('District')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Farm name'), {
    target: { value: 'My own field name' },
  })
  fireEvent.change(screen.getByLabelText('District'), {
    target: { value: 'Kandy' },
  })
  fireEvent.change(screen.getByLabelText('Village or town'), {
    target: { value: 'Synthetic village' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Create farm' }))
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  expect(
    JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body)),
  ).toMatchObject({
    name: 'My own field name',
    location: 'Synthetic village, Kandy District, Sri Lanka',
    latitude: null,
    longitude: null,
    timezone: 'Asia/Colombo',
  })
  expect(geolocation.getCurrentPosition).not.toHaveBeenCalled()
})

it('preserves an existing free-text location and timezone on unrelated edits', async () => {
  handle = () => farm
  wrap(
    <FarmForm
      record={{ ...farm, timezone: 'UTC' }}
      saved={vi.fn()}
      review="/farms"
    />,
  )
  expect(screen.getByLabelText('Location')).toHaveValue(farm.location)
  fireEvent.click(screen.getByRole('button', { name: 'Save farm' }))
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  expect(
    JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body)),
  ).toMatchObject({
    location: farm.location,
    timezone: 'UTC',
    expected_version: farm.version,
  })
})

function openExactLocation() {
  fireEvent.click(screen.getByText('Add exact farm location — optional'))
}

it('requires an explicit location request, reviews the result, and saves only on submit', async () => {
  let locate!: PositionCallback
  const getCurrentPosition = vi.fn((success: PositionCallback) => {
    locate = success
  })
  vi.stubGlobal('isSecureContext', true)
  vi.stubGlobal('navigator', { geolocation: { getCurrentPosition } })
  handle = () => farm
  wrap(<FarmForm record={farm} saved={vi.fn()} review="/farms" />)
  openExactLocation()
  fireEvent.click(
    screen.getByRole('button', { name: 'Use my current location' }),
  )
  expect(screen.getByRole('button', { name: 'Save farm' })).toBeDisabled()
  expect(request).not.toHaveBeenCalled()
  act(() =>
    locate({
      coords: { latitude: 8.3114, longitude: 80.4037, accuracy: 25 },
    } as GeolocationPosition),
  )
  expect(screen.getByLabelText('Latitude (optional)')).toHaveValue('8.3114')
  expect(screen.getByRole('status')).toHaveTextContent('25 metres')
  expect(screen.getByRole('status')).toHaveTextContent(
    'Check that you are at your farm',
  )
  expect(request).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Save farm' }))
  await waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  expect(
    JSON.parse(String(vi.mocked(request).mock.calls[0][1]?.body)),
  ).toMatchObject({ latitude: '8.3114', longitude: '80.4037' })
})

it.each([1, 2, 3])(
  'keeps existing coordinates and allows saving after location error %s',
  (code) => {
    vi.stubGlobal('isSecureContext', true)
    vi.stubGlobal('navigator', {
      geolocation: {
        getCurrentPosition: (
          _success: PositionCallback,
          error: PositionErrorCallback,
        ) => error({ code } as GeolocationPositionError),
      },
    })
    wrap(
      <FarmForm
        record={{ ...farm, latitude: '8.3', longitude: '80.4' }}
        saved={vi.fn()}
        review="/farms"
      />,
    )
    openExactLocation()
    fireEvent.click(
      screen.getByRole('button', { name: 'Use my current location' }),
    )
    expect(screen.getByRole('status')).toHaveTextContent(
      'coordinates have not changed',
    )
    expect(screen.getByLabelText('Latitude (optional)')).toHaveValue('8.3')
    expect(screen.getByRole('button', { name: 'Save farm' })).toBeEnabled()
  },
)

it('ignores a cancelled device lookup after manual coordinate entry', () => {
  let locate!: PositionCallback
  vi.stubGlobal('isSecureContext', true)
  vi.stubGlobal('navigator', {
    geolocation: {
      getCurrentPosition: (success: PositionCallback) => {
        locate = success
      },
    },
  })
  wrap(<FarmForm record={farm} saved={vi.fn()} review="/farms" />)
  openExactLocation()
  fireEvent.click(
    screen.getByRole('button', { name: 'Use my current location' }),
  )
  fireEvent.click(
    screen.getByRole('button', { name: 'Cancel location lookup' }),
  )
  fireEvent.change(screen.getByLabelText('Latitude (optional)'), {
    target: { value: '7.1' },
  })
  fireEvent.change(screen.getByLabelText('Longitude (optional)'), {
    target: { value: '79.9' },
  })
  act(() =>
    locate({
      coords: { latitude: 8.3, longitude: 80.4, accuracy: 20 },
    } as GeolocationPosition),
  )
  expect(screen.getByLabelText('Latitude (optional)')).toHaveValue('7.1')
  expect(screen.getByLabelText('Longitude (optional)')).toHaveValue('79.9')
  expect(screen.getByRole('button', { name: 'Save farm' })).toBeEnabled()
})

it('allows manual entry when device location is unavailable and validates pairs', async () => {
  vi.stubGlobal('isSecureContext', false)
  wrap(<FarmForm record={farm} saved={vi.fn()} review="/farms" />)
  openExactLocation()
  fireEvent.click(
    screen.getByRole('button', { name: 'Use my current location' }),
  )
  expect(screen.getByRole('status')).toHaveTextContent('unavailable here')
  fireEvent.change(screen.getByLabelText('Latitude (optional)'), {
    target: { value: '8.3' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save farm' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Enter both coordinates',
  )
  expect(request).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Remove coordinates' }))
  expect(screen.getByLabelText('Latitude (optional)')).toHaveValue('')
})

it('preserves a stale draft, sends its exact version and requires explicit reload', async () => {
  handle = () => {
    throw new ApiError(409, 'Changed', 'RECORD_VERSION_CONFLICT')
  }
  const review = vi.fn()
  wrap(<FarmForm record={farm} saved={vi.fn()} review={review} />)
  fireEvent.change(screen.getByLabelText('Farm name'), {
    target: { value: 'Unsaved draft name' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save farm' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Your draft has not been saved',
  )
  expect(screen.getByLabelText('Farm name')).toHaveValue('Unsaved draft name')
  expect(screen.getByRole('button', { name: 'Save farm' })).toBeDisabled()
  const [path, init, options] = vi.mocked(request).mock.calls[0]
  expect(path).toBe('/farms/farm-one')
  expect(JSON.parse(String(init?.body))).toMatchObject({
    expected_version: 4,
    area_value: '1.123456',
  })
  expect(options).toEqual({ retryUnauthorized: false })
  expect(request).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Reload latest record' }))
  expect(review).toHaveBeenCalledTimes(1)
})

it('does not claim success or replay an uncertain creation', async () => {
  handle = () => {
    throw new ApiError(0, 'Connection interrupted')
  }
  const saved = vi.fn()
  wrap(<FarmForm saved={saved} review="/farms" />)
  fireEvent.change(screen.getByLabelText('Farm name'), {
    target: { value: 'Synthetic draft' },
  })
  fireEvent.change(screen.getByLabelText('District'), {
    target: { value: 'Anuradhapura' },
  })
  fireEvent.change(screen.getByLabelText('Village or town'), {
    target: { value: 'Synthetic village' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Create farm' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'may already have been saved',
  )
  expect(screen.getByRole('link', { name: 'Review records' })).toHaveAttribute(
    'href',
    '/farms',
  )
  expect(saved).not.toHaveBeenCalled()
  expect(request).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('button', { name: 'Create farm' })).toBeDisabled()
})

it('validates positive precise areas before a write', async () => {
  wrap(<FarmForm record={farm} saved={vi.fn()} review={vi.fn<() => void>()} />)
  fireEvent.change(screen.getByLabelText('Farm area (optional)'), {
    target: { value: '0.0000001' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save farm' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'six decimal places',
  )
  expect(request).not.toHaveBeenCalled()
})

it('offers loading, retry, empty and bounded pagination states', async () => {
  let first = true
  handle = () => {
    if (first) {
      first = false
      throw new ApiError(503, 'Unavailable')
    }
    return page([], 21)
  }
  wrap(<FarmsPage />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'could not be loaded',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('No farms here yet.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() =>
    expect(
      vi.mocked(request).mock.calls.some(([path]) => path.includes('page=2')),
    ).toBe(true),
  )
})

it('shows a generic inaccessible state with no editable record', async () => {
  handle = () => {
    throw new ApiError(404, 'Record not found')
  }
  wrap(
    <Routes>
      <Route path="/farms/:farmId" element={<FarmDetailPage />} />
    </Routes>,
    '/farms/foreign',
  )
  expect(
    await screen.findByRole('heading', { name: 'Record unavailable' }),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Edit farm' }),
  ).not.toBeInTheDocument()
  expect(screen.queryByText(farm.name)).not.toBeInTheDocument()
})

it('keeps archived cultivation details and history readable without write controls', async () => {
  handle = (path) =>
    path.split('?')[0] === '/farms/farm-one/cultivations/cult-one'
      ? {
          ...cultivation,
          effective_archived: true,
          archived_at: farm.created_at,
        }
      : reads(path)
  cultPage()
  expect(
    await screen.findByRole('heading', { name: 'Chilli.' }),
  ).toBeInTheDocument()
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'history remain available',
  )
  expect(
    screen.queryByRole('button', { name: 'Edit cultivation' }),
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Confirm stage' }),
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Add a field note' }),
  ).not.toBeInTheDocument()
  expect(
    screen.getByRole('link', { name: 'Cultivation history' }),
  ).toBeInTheDocument()
  expect(await screen.findByText(observation.notes)).toBeInTheDocument()
  expect(document.querySelector('.record-note b')).toBeNull()
})

it('opens published chilli research from a chilli cultivation record', async () => {
  cultPage()
  expect(
    await screen.findByRole('link', { name: 'Ask a chilli question' }),
  ).toHaveAttribute('href', '/knowledge/chilli')
})

it('keeps observation drafts separate from parent edits and preserves timestamp precision', async () => {
  let next = observation
  handle = (path, init) => {
    if (init?.method === 'PATCH') {
      next = { ...observation, notes: 'Corrected synthetic note', version: 4 }
      return next
    }
    if (path.startsWith('/cultivations/cult-one/observations'))
      return page([next])
    return reads(path)
  }
  cultPage()
  fireEvent.click(
    await screen.findByRole('button', { name: /Edit field note from/ }),
  )
  expect(
    screen.getByRole('button', { name: 'Archive cultivation' }),
  ).toBeDisabled()
  expect(
    screen.getByRole('button', { name: 'Edit cultivation' }),
  ).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Confirm stage' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('What did you see?'), {
    target: { value: 'Corrected synthetic note' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save note' }))
  expect(await screen.findByText('Note saved.')).toBeInTheDocument()
  const mutation = vi
    .mocked(request)
    .mock.calls.find(([, init]) => init?.method === 'PATCH')!
  expect(JSON.parse(String(mutation[1]?.body))).toEqual({
    expected_version: 3,
    notes: 'Corrected synthetic note',
    observed_at: observation.observed_at,
  })
  expect(
    screen.getByRole('button', { name: 'Archive cultivation' }),
  ).toBeEnabled()
})

it('renders previous observation versions as plain text with provenance', async () => {
  handle = (path) =>
    path.includes('/history')
      ? page([
          {
            id: 'revision',
            version: 2,
            changed_at: farm.created_at,
            changed_by: user.id,
            snapshot: { ...observation },
          },
        ])
      : reads(path)
  wrap(
    <Routes>
      <Route
        path="/farms/:farmId/cultivations/:cultivationId/observations/:observationId/history"
        element={<HistoryPage />}
      />
    </Routes>,
    '/farms/farm-one/cultivations/cult-one/observations/obs-one/history',
  )
  expect(
    await screen.findByRole('heading', { name: 'Version 2' }),
  ).toBeInTheDocument()
  expect(screen.getByText(observation.notes)).toBeInTheDocument()
  expect(screen.getByText(/Saved by you/)).toBeInTheDocument()
  expect(document.querySelector('.record-history-fields b')).toBeNull()
})

it.each(['/farms', '/dashboard'])(
  'gates %s for administrators without issuing a farm request',
  async (path) => {
    const { restoreSession } = await import('../../lib/accounts')
    vi.mocked(restoreSession).mockResolvedValueOnce({
      user: { ...user, role: 'administrator' },
      access_token: 'synthetic',
      expires_in: 900,
    })
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>,
    )
    expect(
      await screen.findByRole('heading', { name: 'Access denied' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'My Farms' }),
    ).not.toBeInTheDocument()
    expect(
      vi.mocked(request).mock.calls.some(([path]) => path.startsWith('/farms')),
    ).toBe(false)
  },
)

it('opens the observation entry from onboarding and consumes the one-time intent', async () => {
  cultPage('?observe=1')
  expect(await screen.findByLabelText('What did you see?')).toBeVisible()
  expect(
    screen.getByRole('button', { name: 'Archive cultivation' }),
  ).toBeDisabled()
  expect(
    screen.getByRole('button', { name: 'Edit cultivation' }),
  ).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Cancel editing note' }))
  expect(screen.queryByLabelText('What did you see?')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Edit cultivation' })).toBeEnabled()
})

it('does not open an onboarding write form for an archived crop', async () => {
  handle = (path) =>
    path.split('?')[0] === '/farms/farm-one/cultivations/cult-one'
      ? {
          ...cultivation,
          effective_archived: true,
          archived_at: farm.created_at,
        }
      : reads(path)
  cultPage('?observe=1')
  expect(
    await screen.findByText('Archived record.', { exact: false }),
  ).toBeVisible()
  expect(screen.queryByLabelText('What did you see?')).not.toBeInTheDocument()
})

it('ignores a late private response after the account changes', async () => {
  let resolveOld!: (value: Farm) => void
  let count = 0
  handle = (path) => {
    if (path === '/farms/farm-one') {
      count++
      if (count === 1)
        return new Promise<Farm>((resolve) => {
          resolveOld = resolve
        })
      throw new ApiError(404, 'Unavailable')
    }
    return reads(path)
  }
  render(
    <MemoryRouter initialEntries={['/farms/farm-one']}>
      <App />
    </MemoryRouter>,
  )
  await waitFor(() => expect(count).toBe(1))
  act(() =>
    window.dispatchEvent(
      new CustomEvent('account-session', {
        detail: { ...user, id: 'new-owner' },
      }),
    ),
  )
  expect(
    await screen.findByRole('heading', { name: 'Record unavailable' }),
  ).toBeInTheDocument()
  await act(async () => {
    resolveOld(farm)
  })
  expect(screen.queryByText(farm.name)).not.toBeInTheDocument()
})
