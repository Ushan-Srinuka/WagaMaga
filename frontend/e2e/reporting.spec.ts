import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from '@playwright/test'
import { randomBytes } from 'node:crypto'
import { apiRoot, webOrigin } from './environment.ts'

const password = process.env.E2E_PASSWORD!
const adminEmail = `browser-admin-${process.env.E2E_RUN_ID}@example.com`
const headers = { Origin: webOrigin, 'X-WagaMaga-Client': 'web' }
async function authenticate(request: APIRequestContext, email: string) {
  const response = await request.post(apiRoot + '/auth/login', {
    headers,
    data: { email, password },
  })
  expect(response.ok()).toBe(true)
  const result = await response.json()
  return {
    user: result.user,
    headers: { ...headers, Authorization: `Bearer ${result.access_token}` },
  }
}
async function actor(request: APIRequestContext) {
  const suffix = randomBytes(5).toString('hex')
  const email = `report-${suffix}@example.com`
  const display_name = `Synthetic reporting farmer ${suffix}`
  expect(
    (
      await request.post(apiRoot + '/auth/register', {
        headers,
        data: { email, password, display_name },
      })
    ).ok(),
  ).toBe(true)
  return { email, display_name, ...(await authenticate(request, email)) }
}
async function login(
  page: Page,
  email: string,
  destination = '/admin/overview',
) {
  await page.goto('/login')
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(destination)
}
async function fit(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
}

test('administrator sees live count summaries without private farm details', async ({
  page,
  request,
}, info) => {
  const admin = await authenticate(request, adminEmail)
  const owner = await actor(request)
  const initialResponse = await request.get(apiRoot + '/admin/overview', {
    headers: admin.headers,
  })
  expect(initialResponse.ok()).toBe(true)
  const initial = await initialResponse.json()
  const makeFarm = async (name: string) => {
    const result = await request.post(apiRoot + '/farms', {
      headers: owner.headers,
      data: { name, location: 'Synthetic private report location' },
    })
    expect(result.ok()).toBe(true)
    return result.json()
  }
  const active = await makeFarm('Private active farm for reporting')
  const archived = await makeFarm('Private archived farm for reporting')
  const deleted = await makeFarm('Private deleted farm for reporting')
  const catalog = await (
    await request.get(apiRoot + '/crop-types', { headers: owner.headers })
  ).json()
  const plant = async (farmId: string) => {
    const result = await request.post(
      apiRoot + `/farms/${farmId}/cultivations`,
      {
        headers: owner.headers,
        data: {
          crop_type_id: catalog.items[0].id,
          planting_date: '2026-01-01',
          area_value: '1',
          area_unit: 'ha',
        },
      },
    )
    expect(result.ok()).toBe(true)
    return result.json()
  }
  await plant(active.id)
  const ownArchive = await plant(active.id)
  await plant(archived.id)
  expect(
    (
      await request.post(
        apiRoot + `/farms/${active.id}/cultivations/${ownArchive.id}/archive`,
        { headers: owner.headers, data: { expected_version: 1 } },
      )
    ).ok(),
  ).toBe(true)
  for (const farm of [archived, deleted])
    expect(
      (
        await request.post(apiRoot + `/farms/${farm.id}/archive`, {
          headers: owner.headers,
          data: { expected_version: 1 },
        })
      ).ok(),
    ).toBe(true)
  expect(
    (
      await request.post(apiRoot + `/farms/${deleted.id}/delete`, {
        headers: owner.headers,
        data: { expected_version: 2, confirmation_name: deleted.name },
      })
    ).ok(),
  ).toBe(true)
  const response = await request.get(apiRoot + '/admin/overview', {
    headers: admin.headers,
  })
  const current = await response.json()
  expect(current.farms.total).toBe(initial.farms.total + 2)
  expect(current.cultivations.total).toBe(initial.cultivations.total + 3)
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await login(page, adminEmail)
  await expect(
    page.getByRole('heading', { name: 'Admin Overview.', exact: true }),
  ).toBeVisible()
  const cards = page.getByRole('region', { name: 'Administration summary' })
  await expect(
    cards
      .getByRole('article')
      .filter({ has: page.getByText('Farm records', { exact: true }) })
      .locator('strong'),
  ).toHaveText(String(current.farms.total))
  await expect(
    cards
      .getByRole('article')
      .filter({ has: page.getByText('Cultivation records', { exact: true }) })
      .locator('strong'),
  ).toHaveText(String(current.cultivations.total))
  await expect(page.getByText(active.name, { exact: false })).toHaveCount(0)
  await expect(
    page.getByText('Synthetic private report location', { exact: false }),
  ).toHaveCount(0)
  await fit(page)
  await page.screenshot({
    path: info.outputPath('admin-overview.png'),
    fullPage: false,
  })
  await page.getByRole('link', { name: 'Manage farmers', exact: true }).click()
  await page.getByLabel('Search accounts').fill(owner.email)
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page
    .getByRole('link', { name: `View ${owner.display_name}`, exact: true })
    .click()
  const summary = page.getByRole('region', {
    name: 'Farm record summary',
    exact: true,
  })
  await expect(summary.locator('dd')).toHaveText(['2', '1', '1', '3', '1', '2'])
  await expect(
    summary.getByText('Counts only.', { exact: false }),
  ).toBeVisible()
  await fit(page)
  await summary.screenshot({
    path: info.outputPath('farmer-count-summary.png'),
  })
  await expect(page.getByText(active.name, { exact: false })).toHaveCount(0)
  const summaryResponse = await request.get(
    apiRoot + `/admin/users/${owner.user.id}/farm-summary`,
    { headers: admin.headers },
  )
  expect(summaryResponse.ok()).toBe(true)
  expect(await summaryResponse.text()).not.toContain(active.name)
  expect(
    (
      await request.get(apiRoot + `/farms/${active.id}`, {
        headers: admin.headers,
      })
    ).status(),
  ).toBe(403)
  await page.goto(`/farms/${active.id}`)
  await expect(
    page.getByRole('heading', { name: 'Access denied' }),
  ).toBeVisible()
  const audit = await (
    await request.get(apiRoot + '/admin/audit-logs?action=report_viewed', {
      headers: admin.headers,
    })
  ).json()
  expect(
    audit.items.some(
      (event: { new_value: string; target_id: string }) =>
        event.new_value === 'farmer_summary' &&
        event.target_id === owner.user.id,
    ),
  ).toBe(true)
  expect(errors).toEqual([])
})

test('report routes deny farmers and clear counts after administrator revocation', async ({
  page,
  request,
}) => {
  const owner = await actor(request)
  const admin = await authenticate(request, adminEmail)
  await login(page, owner.email, '/')
  await page.goto('/admin/overview')
  await expect(
    page.getByRole('heading', { name: 'Access denied' }),
  ).toBeVisible()
  expect(
    (
      await request.get(
        apiRoot + `/admin/users/${owner.user.id}/farm-summary`,
        { headers: owner.headers },
      )
    ).status(),
  ).toBe(403)
  expect(
    (
      await request.patch(apiRoot + `/admin/users/${owner.user.id}/role`, {
        headers: admin.headers,
        data: {
          role: 'administrator',
          expected_version: 1,
          reason: 'Synthetic reporting role test',
        },
      })
    ).ok(),
  ).toBe(true)
  await login(page, owner.email)
  await expect(
    page.getByRole('region', { name: 'Administration summary' }),
  ).toBeVisible()
  expect(
    (
      await request.patch(apiRoot + `/admin/users/${owner.user.id}/status`, {
        headers: admin.headers,
        data: {
          enabled: false,
          expected_version: 2,
          reason: 'Synthetic report revocation',
        },
      })
    ).ok(),
  ).toBe(true)
  await page
    .getByRole('button', { name: 'Refresh overview', exact: true })
    .click()
  await expect(page).toHaveURL('/login')
  await expect(
    page.getByRole('region', { name: 'Administration summary' }),
  ).toHaveCount(0)
})
