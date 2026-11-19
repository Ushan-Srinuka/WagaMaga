import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from '@playwright/test'
import { randomBytes } from 'node:crypto'
import { apiRoot, webOrigin } from './environment.ts'

const root = apiRoot
const password = process.env.E2E_PASSWORD!
const headers = { Origin: webOrigin, 'X-WagaMaga-Client': 'web' }
const adminEmail = `browser-admin-${process.env.E2E_RUN_ID}@example.com`
async function actor(request: APIRequestContext, name: string) {
  const email = `farm-browser-${randomBytes(6).toString('hex')}@example.com`
  expect(
    (
      await request.post(root + '/auth/register', {
        headers,
        data: { email, display_name: name, password },
      })
    ).ok(),
  ).toBe(true)
  const response = await request.post(root + '/auth/login', {
    headers,
    data: { email, password },
  })
  expect(response.ok()).toBe(true)
  const result = await response.json()
  return {
    email,
    user: result.user,
    headers: { ...headers, Authorization: `Bearer ${result.access_token}` },
  }
}
async function login(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(email === adminEmail ? '/admin/overview' : '/')
}
async function menu(page: Page) {
  await expect(page.getByRole('banner')).toBeVisible()
  const button = page.getByRole('button', { name: 'Menu', exact: true })
  if (
    (await button.isVisible()) &&
    (await button.getAttribute('aria-expanded')) !== 'true'
  )
    await button.click()
}
async function fit(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
}

test('visitor can start from the landing hero without loading private farms', async ({
  page,
}, info) => {
  const farmReads: string[] = []
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/v1/farms'))
      farmReads.push(request.url())
  })
  await page.goto('/')
  await expect(page.getByRole('link', { name: /Get started/ })).toBeVisible()
  await expect(page.getByRole('link', { name: /Get started/ })).toBeInViewport()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('landing-visitor.png'),
    fullPage: false,
  })
  expect(farmReads).toEqual([])
  await page.getByRole('link', { name: /Get started/ }).click()
  await expect(page).toHaveURL('/register')
  await page.goto('/')
  await page.getByRole('link', { name: /Log in to your farms/ }).click()
  await expect(page).toHaveURL('/login')
})

test('farmer keeps farm, cultivation, observation and archive history through connected screens', async ({
  page,
  request,
}, info) => {
  const owner = await actor(request, 'Synthetic records farmer')
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await login(page, owner.email)
  await expect(
    page.getByText('Add your first farm', { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole('banner').getByRole('link', { name: /Add farm/ }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: /Add my farm/ })).toBeInViewport()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('landing-new-farmer.png'),
    fullPage: false,
  })
  await page.getByRole('link', { name: /Add my farm/ }).click()
  await page.getByLabel('Farm name').fill('Synthetic notebook farm')
  await expect(page.getByLabel('District', { exact: true })).toHaveValue('')
  await page
    .getByLabel('District', { exact: true })
    .selectOption('Anuradhapura')
  await page.getByLabel('Village or town').fill('Synthetic village')
  await page.context().grantPermissions(['geolocation'])
  await page
    .context()
    .setGeolocation({ latitude: 8.3114, longitude: 80.4037, accuracy: 25 })
  await page
    .getByText('Add exact farm location — optional', { exact: true })
    .click()
  await page.getByRole('button', { name: 'Use my current location' }).click()
  await expect(page.getByLabel('Latitude (optional)')).toHaveValue('8.3114')
  await expect(page.getByLabel('Longitude (optional)')).toHaveValue('80.4037')
  await page
    .getByText('Additional farm details — optional', { exact: true })
    .click()
  await page.getByLabel('Farm area (optional)').fill('1.234567')
  await fit(page)
  await page.screenshot({
    path: info.outputPath('new-farm.png'),
    fullPage: true,
  })
  await page.getByRole('button', { name: 'Create farm', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Synthetic notebook farm.' }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Edit farm', exact: true }).click()
  await page.getByLabel('Farm name').fill('Synthetic notebook farm revised')
  await expect(
    page.getByRole('button', { name: 'Archive farm', exact: true }),
  ).toBeDisabled()
  await page.getByRole('button', { name: 'Save farm', exact: true }).click()
  await expect(page.getByText('Farm details saved.')).toBeVisible()
  await expect(page.getByText('1.234567 ha', { exact: true })).toBeVisible()
  await page.goto('/')
  await page.getByRole('link', { name: /Add what you are growing/ }).click()
  await page.getByLabel('Planting date').fill('2099-01-15')
  await page.getByLabel('Cultivation area', { exact: true }).fill('1.25')
  await fit(page)
  await page
    .getByRole('button', { name: 'Create cultivation', exact: true })
    .click()
  await expect(page.getByRole('heading', { name: 'Chilli.' })).toBeVisible()
  await expect(
    page.getByText('Planned cultivation', { exact: true }),
  ).toBeVisible()
  const cropURL = page.url()
  await page.goto('/')
  await page.getByRole('link', { name: /Record first observation/ }).click()
  await expect(page.getByLabel('Observation notes')).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Archive cultivation', exact: true }),
  ).toBeDisabled()
  await page.getByLabel('Observed at (device time)').fill('2026-11-01T08:00')
  await page
    .getByLabel('Observation notes')
    .fill('Initial synthetic field note <b>not HTML</b>')
  await fit(page)
  await page
    .getByRole('button', { name: 'Record observation', exact: true })
    .click()
  await expect(
    page.getByText('Observation saved.', { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByText('Initial synthetic field note <b>not HTML</b>', {
      exact: true,
    }),
  ).toBeVisible()
  await page.getByRole('button', { name: /Edit observation from/ }).click()
  await page
    .getByLabel('Observation notes')
    .fill('Corrected synthetic field note')
  await page
    .getByRole('button', { name: 'Save observation', exact: true })
    .click()
  await expect(page.getByLabel('Observation notes')).toHaveCount(0)
  await expect(
    page.getByText('Corrected synthetic field note', { exact: true }),
  ).toBeVisible()
  await page.goto('/')
  await expect(
    page.getByRole('link', { name: /Open crop records/ }),
  ).toBeVisible()
  await expect(page.getByText('Pick up where you left off')).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('landing-returning-farmer.png'),
    fullPage: false,
  })
  await page.goto(cropURL)
  await expect(
    page.getByText('Corrected synthetic field note', { exact: true }),
  ).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('cultivation.png'),
    fullPage: true,
  })
  await page
    .getByRole('link', { name: 'Observation history', exact: true })
    .click()
  await expect(
    page.getByRole('heading', { name: 'Version 2', exact: true }),
  ).toBeVisible()
  const first = page.getByRole('article').filter({
    has: page.getByRole('heading', { name: 'Version 1', exact: true }),
  })
  await first.getByText('View recorded details').click()
  await expect(
    first.getByText('Initial synthetic field note <b>not HTML</b>', {
      exact: true,
    }),
  ).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('observation-history.png'),
    fullPage: true,
  })
  await page
    .getByRole('link', { name: '← Back to cultivation', exact: true })
    .click()
  await page.getByLabel('Reported stage').fill('Owner-reported seedlings')
  await page.getByRole('button', { name: 'Confirm stage', exact: true }).click()
  await expect(
    page.getByText('Owner-reported seedlings', { exact: true }),
  ).toBeVisible()
  await expect(page.getByText(/Confirmed by you on/)).toBeVisible()
  await page
    .getByRole('button', { name: 'Edit cultivation', exact: true })
    .click()
  await page.getByLabel('Planting date').fill('2099-02-01')
  await page
    .getByLabel('Soil information (optional)')
    .fill('Unknown texture; synthetic record')
  await page
    .getByRole('button', { name: 'Save cultivation', exact: true })
    .click()
  await expect(page.getByText('Not confirmed', { exact: true })).toBeVisible()
  await page
    .getByRole('button', { name: 'Archive cultivation', exact: true })
    .click()
  await expect(page.getByRole('dialog')).toContainText(
    'history will remain readable',
  )
  await expect(
    page.getByRole('button', { name: 'Cancel', exact: true }),
  ).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(
    page.getByRole('button', { name: 'Archive cultivation', exact: true }),
  ).toBeFocused()
  await page
    .getByRole('button', { name: 'Archive cultivation', exact: true })
    .click()
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Archive cultivation', exact: true })
    .click()
  await expect(
    page.getByText('Cultivation archived. History remains available.', {
      exact: true,
    }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Add observation', exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByRole('button', { name: 'Edit cultivation', exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByText('Corrected synthetic field note', { exact: true }),
  ).toBeVisible()
  await page
    .getByRole('link', {
      name: '← Synthetic notebook farm revised',
      exact: true,
    })
    .click()
  await page
    .getByRole('combobox', { name: 'Cultivation status', exact: true })
    .selectOption('archived')
  await expect(
    page.getByRole('link', { name: 'Cultivation · 2099-02-01', exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Archive farm', exact: true }).click()
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Archive farm', exact: true })
    .click()
  await expect(
    page.getByText('Farm archived. Its history remains available.', {
      exact: true,
    }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Edit farm', exact: true }),
  ).toHaveCount(0)
  await page.getByRole('link', { name: 'Farm history', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Version 3', exact: true }),
  ).toBeVisible()
  await page
    .getByRole('link', {
      name: '← Back to Synthetic notebook farm revised',
      exact: true,
    })
    .click()
  await page.getByRole('link', { name: '← My Farms', exact: true }).click()
  await page
    .getByRole('combobox', { name: 'Farm status', exact: true })
    .selectOption('archived')
  await expect(
    page.getByRole('heading', {
      name: 'Synthetic notebook farm revised',
      exact: true,
    }),
  ).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('my-farms.png'),
    fullPage: true,
  })
  expect(errors).toEqual([])
  expect(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
  ).toBe(0)
  await menu(page)
  await page.getByRole('button', { name: /Sign out/ }).click()
  await expect(
    page.getByRole('heading', { name: 'Make yourself at home.' }),
  ).toBeVisible()
  await expect(
    page.getByText('Synthetic notebook farm revised', { exact: true }),
  ).toHaveCount(0)
})

test('stale drafts require reload and private record links deny other owners', async ({
  page,
  request,
}, info) => {
  const owner = await actor(request, 'Synthetic conflict owner')
  const other = await actor(request, 'Synthetic other owner')
  const create = await request.post(root + '/farms', {
    headers: owner.headers,
    data: { name: 'Original synthetic farm', location: 'Synthetic location' },
  })
  expect(create.ok()).toBe(true)
  const farm = await create.json()
  const secret = await request.post(root + '/farms', {
    headers: other.headers,
    data: {
      name: 'Other owner private farm',
      location: 'Private synthetic location',
    },
  })
  expect(secret.ok()).toBe(true)
  const foreign = await secret.json()
  await login(page, owner.email)
  await page.goto(`/farms/${farm.id}`)
  await page.getByRole('button', { name: 'Edit farm', exact: true }).click()
  await page.getByLabel('Farm name').fill('Unsaved browser draft')
  const concurrent = await request.patch(root + `/farms/${farm.id}`, {
    headers: owner.headers,
    data: { expected_version: 1, name: 'Concurrent saved farm' },
  })
  expect(concurrent.ok()).toBe(true)
  let writes = 0
  page.on('request', (req) => {
    if (
      new URL(req.url()).pathname === `/api/v1/farms/${farm.id}` &&
      req.method() === 'PATCH'
    )
      writes++
  })
  await page.getByRole('button', { name: 'Save farm', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText(
    'Your draft has not been saved',
  )
  await expect(page.getByLabel('Farm name')).toHaveValue(
    'Unsaved browser draft',
  )
  await expect(
    page.getByRole('button', { name: 'Save farm', exact: true }),
  ).toBeDisabled()
  expect(writes).toBe(1)
  await page
    .getByRole('button', { name: 'Reload latest record', exact: true })
    .click()
  await expect(
    page.getByRole('heading', { name: 'Concurrent saved farm.' }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Edit farm', exact: true }).click()
  await expect(page.getByLabel('Farm name')).toHaveValue(
    'Concurrent saved farm',
  )
  await page.goto(`/farms/${foreign.id}`)
  await expect(
    page.getByRole('heading', { name: 'Record unavailable' }),
  ).toBeVisible()
  await expect(
    page.getByText('Other owner private farm', { exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByRole('button', { name: 'Edit farm', exact: true }),
  ).toHaveCount(0)
  await fit(page)
  await page.screenshot({
    path: info.outputPath('private-record-denied.png'),
    fullPage: true,
  })
  await page.goto('/account')
  await menu(page)
  await page.getByRole('button', { name: /Sign out/ }).click()
  await login(page, other.email)
  await page.goto('/farms')
  await expect(
    page.getByRole('heading', {
      name: 'Other owner private farm',
      exact: true,
    }),
  ).toBeVisible()
  await expect(
    page.getByText('Concurrent saved farm', { exact: true }),
  ).toHaveCount(0)
})

test('session revocation clears a private draft and does not replay a write', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic revoked owner')
  const created = await request.post(root + '/farms', {
    headers: owner.headers,
    data: { name: 'Synthetic revocation farm', location: 'Synthetic place' },
  })
  expect(created.ok()).toBe(true)
  const farm = await created.json()
  await login(page, owner.email)
  await page.goto(`/farms/${farm.id}`)
  await page.getByRole('button', { name: 'Edit farm', exact: true }).click()
  await page.getByLabel('Farm name').fill('Private revoked draft')
  const admin = await request.post(root + '/auth/login', {
    headers,
    data: { email: adminEmail, password },
  })
  expect(admin.ok()).toBe(true)
  const adminHeaders = {
    ...headers,
    Authorization: `Bearer ${(await admin.json()).access_token}`,
  }
  expect(
    (
      await request.patch(root + `/admin/users/${owner.user.id}/status`, {
        headers: adminHeaders,
        data: {
          expected_version: 1,
          enabled: false,
          reason: 'Synthetic browser revocation',
        },
      })
    ).ok(),
  ).toBe(true)
  let writes = 0
  page.on('request', (req) => {
    if (
      new URL(req.url()).pathname === `/api/v1/farms/${farm.id}` &&
      req.method() === 'PATCH'
    )
      writes++
  })
  await page.getByRole('button', { name: 'Save farm', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Make yourself at home.' }),
  ).toBeVisible()
  await expect(page.getByLabel('Farm name')).toHaveCount(0)
  expect(writes).toBe(1)
  expect(
    (
      await request.patch(root + `/admin/users/${owner.user.id}/status`, {
        headers: adminHeaders,
        data: {
          expected_version: 2,
          enabled: true,
          reason: 'Synthetic browser re-enable',
        },
      })
    ).ok(),
  ).toBe(true)
  const fresh = await request.post(root + '/auth/login', {
    headers,
    data: { email: owner.email, password },
  })
  const result = await request.get(root + `/farms/${farm.id}`, {
    headers: {
      ...headers,
      Authorization: `Bearer ${(await fresh.json()).access_token}`,
    },
  })
  expect(result.ok()).toBe(true)
  expect((await result.json()).name).toBe('Synthetic revocation farm')
  await login(page, adminEmail)
  await page.goto('/farms')
  await expect(
    page.getByRole('heading', { name: 'Access denied' }),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'My Farms', exact: true }),
  ).toHaveCount(0)
})

test('owner restores an archived farm and confirms workspace deletion by name', async ({
  page,
  request,
}, info) => {
  const owner = await actor(request, 'Synthetic lifecycle farmer')
  const created = await request.post(root + '/farms', {
    headers: owner.headers,
    data: { name: 'Synthetic lifecycle farm', location: 'Synthetic village' },
  })
  expect(created.ok()).toBe(true)
  const farm = await created.json()
  const farmPath = `/farms/${farm.id}`
  const crop = (
    await (
      await request.get(root + '/crop-types', { headers: owner.headers })
    ).json()
  ).items[0]
  const planted = await request.post(root + farmPath + '/cultivations', {
    headers: owner.headers,
    data: {
      crop_type_id: crop.id,
      planting_date: '2026-01-01',
      area_value: '1',
      area_unit: 'ha',
    },
  })
  expect(planted.ok()).toBe(true)
  const cultivation = await planted.json()
  await login(page, owner.email)
  await page.goto(farmPath)
  await page.getByRole('button', { name: 'Archive farm', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText(
    'You can restore this farm later',
  )
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Archive farm', exact: true })
    .click()
  await expect(
    page.getByRole('button', { name: 'Restore farm', exact: true }),
  ).toBeVisible()
  await page.getByRole('link', { name: '← My Farms', exact: true }).click()
  await page
    .getByRole('combobox', { name: 'Farm status', exact: true })
    .selectOption('archived')
  await page
    .getByRole('link', { name: 'Synthetic lifecycle farm', exact: true })
    .click()
  await page.getByRole('button', { name: 'Restore farm', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText(
    'Separately archived crops stay archived',
  )
  await page.keyboard.press('Escape')
  await expect(
    page.getByRole('button', { name: 'Restore farm', exact: true }),
  ).toBeFocused()
  await page.getByRole('button', { name: 'Restore farm', exact: true }).click()
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Restore farm', exact: true })
    .click()
  await expect(
    page.getByText(
      'Farm restored. Separately archived crops remain archived.',
      { exact: true },
    ),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Edit farm', exact: true }),
  ).toBeVisible()
  const restored = await request.get(
    root + farmPath + `/cultivations/${cultivation.id}`,
    { headers: owner.headers },
  )
  expect((await restored.json()).effective_archived).toBe(false)
  await page.getByRole('button', { name: 'Archive farm', exact: true }).click()
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Archive farm', exact: true })
    .click()
  await page.getByRole('button', { name: 'Delete farm', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('Historical records are retained')
  await expect(dialog).toContainText('does not erase data permanently')
  await expect(
    dialog.getByRole('button', { name: 'Delete farm', exact: true }),
  ).toBeDisabled()
  await page.getByLabel('Type the farm name to confirm').fill('wrong name')
  await expect(
    dialog.getByRole('button', { name: 'Delete farm', exact: true }),
  ).toBeDisabled()
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click()
  await page.getByRole('button', { name: 'Delete farm', exact: true }).click()
  await expect(page.getByLabel('Type the farm name to confirm')).toHaveValue('')
  await page
    .getByLabel('Type the farm name to confirm')
    .fill('Synthetic lifecycle farm')
  await fit(page)
  await page.screenshot({
    path: info.outputPath('delete-farm-confirmation.png'),
    fullPage: false,
  })
  await dialog.getByRole('button', { name: 'Delete farm', exact: true }).click()
  await expect(page).toHaveURL('/farms?status=archived')
  await expect(
    page.getByText('Farm deleted from your workspace.', { exact: false }),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Synthetic lifecycle farm', exact: true }),
  ).toHaveCount(0)
  await page.goto(farmPath)
  await expect(
    page.getByRole('heading', { name: 'Record unavailable' }),
  ).toBeVisible()
  await page.goto(`${farmPath}/cultivations/${cultivation.id}`)
  await expect(
    page.getByRole('heading', { name: 'Record unavailable' }),
  ).toBeVisible()
  await page.goto('/')
  await expect(page.getByRole('link', { name: /Add my farm/ })).toBeVisible()
  await expect(
    page.getByRole('combobox', { name: 'Choose your farm' }),
  ).toHaveCount(0)
})
