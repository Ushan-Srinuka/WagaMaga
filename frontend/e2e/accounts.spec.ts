import { expect, test, type Page } from '@playwright/test'
import { randomBytes } from 'node:crypto'
import { apiRoot, webOrigin } from './environment.ts'

const password = process.env.E2E_PASSWORD!
const adminEmail = `browser-admin-${process.env.E2E_RUN_ID}@example.com`
const headers = { Origin: webOrigin, 'X-WagaMaga-Client': 'web' }
function email() {
  return `browser-${randomBytes(6).toString('hex')}@example.com`
}
async function login(page: Page, address: string, secret = password) {
  await page.goto('/login')
  await page.getByLabel('Email address').fill(address)
  await page.getByLabel('Password', { exact: true }).fill(secret)
  const response = page.waitForResponse(
    (result) =>
      new URL(result.url()).pathname === '/api/v1/auth/login' &&
      result.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Sign in', exact: false }).click()
  const { user } = await (await response).json()
  await expect(page).toHaveURL(
    user.role === 'farmer'
      ? '/'
      : user.role === 'administrator'
        ? '/admin/overview'
        : '/advisor',
  )
  await page.goto('/account')
  await expect(page.getByRole('heading', { name: 'My account.' })).toBeVisible()
}
async function fit(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
}
async function openMenu(page: Page) {
  const menu = page.getByRole('button', { name: 'Menu', exact: true })
  if (await menu.isVisible()) await menu.click()
}

test('stale administrator edits reload the record and require a fresh decision', async ({
  page,
  request,
}) => {
  const address = email()
  await request.post(`${apiRoot}/auth/register`, {
    headers,
    data: { email: address, password, display_name: 'Stale browser account' },
  })
  await login(page, adminEmail)
  const authentication = await request.post(`${apiRoot}/auth/login`, {
    headers,
    data: { email: adminEmail, password },
  })
  expect(authentication.ok()).toBe(true)
  const { access_token } = await authentication.json()
  const adminHeaders = { ...headers, Authorization: `Bearer ${access_token}` }
  const found = await request.get(
    `${apiRoot}/admin/users?q=${encodeURIComponent(address)}`,
    { headers: adminHeaders },
  )
  const { items } = await found.json()
  await page.goto(`/admin/users/${items[0].id}`)
  await expect(page.getByLabel('Account role')).toHaveValue('farmer')
  const concurrent = await request.patch(
    `${apiRoot}/admin/users/${items[0].id}/role`,
    {
      headers: adminHeaders,
      data: {
        role: 'administrator',
        expected_version: 1,
        reason: 'Synthetic concurrent edit',
      },
    },
  )
  expect(concurrent.ok()).toBe(true)
  await page.getByLabel('Account role').selectOption('advisor')
  await page.getByLabel('Reason for change').fill('Synthetic stale decision')
  await page.getByRole('button', { name: 'Review role change' }).click()
  await page.getByRole('button', { name: 'Confirm change' }).click()
  await expect(
    page.getByText('This account changed. Reload it before saving.', {
      exact: true,
    }),
  ).toBeVisible()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByLabel('Account role')).toHaveValue('administrator')
  await fit(page)
})

test('farmer registers, signs in, edits profile, reloads and signs out', async ({
  page,
}, testInfo) => {
  const address = email()
  const signupPassword = `a1!${randomBytes(3).toString('hex').slice(0, 5)}`
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/register')
  await expect(
    page.getByRole('heading', { name: 'Create your account' }),
  ).toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath('register.png'),
    fullPage: true,
  })
  await page.getByLabel('Display name').fill('Synthetic farmer')
  await page.getByLabel('Email address').fill(address)
  const registrationRequests: string[] = []
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/api/v1/auth/register')
      registrationRequests.push(request.method())
  })
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute(
    'minlength',
    '8',
  )
  for (const invalid of ['abcdefg1', 'abcdefg!', '1234567!']) {
    await page.getByLabel('Password', { exact: true }).fill(invalid)
    await page.getByLabel('Confirm password', { exact: true }).fill(invalid)
    await page.getByRole('button', { name: /Create account/ }).click()
    await expect(page.getByRole('alert')).toContainText(
      'at least one letter, one number and one symbol',
    )
  }
  expect(registrationRequests).toEqual([])
  await page.getByLabel('Password', { exact: true }).fill(signupPassword)
  await page
    .getByLabel('Confirm password', { exact: true })
    .fill(signupPassword)
  await page.getByRole('button', { name: /Create account/ }).click()
  await expect(page.getByRole('status')).toContainText(
    'Registration request processed',
  )
  await fit(page)
  await login(page, address, signupPassword)
  const changedPassword = `Changed!${randomBytes(8).toString('hex')}`
  await page
    .getByRole('textbox', { name: 'Current password' })
    .fill(signupPassword)
  await page
    .getByRole('textbox', { name: 'New password', exact: true })
    .fill(changedPassword)
  await page
    .getByRole('textbox', { name: 'Confirm new password' })
    .fill(changedPassword)
  await page.getByRole('button', { name: 'Change password' }).click()
  await expect(page.getByRole('status')).toContainText('Password changed')
  await openMenu(page)
  await expect(page.getByLabel('1 unread notifications')).toBeVisible()
  await page.getByRole('link', { name: /Notifications/ }).click()
  await expect(
    page.getByRole('heading', { name: 'Notifications.' }),
  ).toBeVisible()
  await expect(
    page.getByText(
      'Your password was changed. Other sessions have been signed out.',
    ),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Mark read' }).click()
  await expect(page.getByRole('button', { name: 'Mark unread' })).toBeVisible()
  await openMenu(page)
  await expect(page.getByLabel(/unread notifications/)).toHaveCount(0)
  await page.getByRole('link', { name: /My account/ }).click()
  await page.getByLabel('Display name').fill('New synthetic name')
  await page.getByRole('button', { name: /Save changes/ }).click()
  await expect(
    page.getByText('Your display name has been saved.'),
  ).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('Display name')).toHaveValue(
    'New synthetic name',
  )
  const cookie = (await page.context().cookies()).find(
    (item) => item.name === 'wagamaga_refresh',
  )
  expect(cookie?.httpOnly).toBe(true)
  expect(cookie?.sameSite).toBe('Lax')
  expect(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
  ).toBe(0)
  await fit(page)
  await page.screenshot({
    path: testInfo.outputPath('account.png'),
    fullPage: true,
  })
  await page.goto('/admin/users')
  await expect(
    page.getByRole('heading', { name: 'Access denied' }),
  ).toBeVisible()
  await openMenu(page)
  await page.getByRole('button', { name: /Sign out/ }).click()
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
  await page.goto('/account')
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
  await login(page, address, changedPassword)
  await openMenu(page)
  await page.getByRole('button', { name: /Sign out/ }).click()
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
  expect(errors).toEqual([])
})

test('administrator searches accounts and confirms role/status changes', async ({
  page,
  request,
  browser,
}, testInfo) => {
  const address = email()
  const registration = await request.post(`${apiRoot}/auth/register`, {
    headers,
    data: {
      email: address,
      password,
      display_name: 'Synthetic review account',
    },
  })
  expect(registration.ok()).toBe(true)
  const farmerContext = await browser.newContext({
    baseURL: webOrigin,
    viewport: page.viewportSize() ?? undefined,
  })
  const farmerPage = await farmerContext.newPage()
  await login(farmerPage, address)
  await login(page, adminEmail)
  const administratorLogin = await request.post(`${apiRoot}/auth/login`, {
    headers,
    data: { email: adminEmail, password },
  })
  const { access_token: adminToken } = await administratorLogin.json()
  const adminHeaders = { ...headers, Authorization: `Bearer ${adminToken}` }
  const removedBefore = await request.get(
    `${apiRoot}/admin/users?status=deleted`,
    { headers: adminHeaders },
  )
  const deletedBefore = (await removedBefore.json()).total as number
  await openMenu(page)
  await page.getByRole('link', { name: /User management/ }).click()
  await page.getByLabel('Search accounts').fill(address)
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page
    .getByRole('combobox', { name: 'Role', exact: true })
    .selectOption('farmer')
  await expect(page.getByText(address, { exact: true })).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: testInfo.outputPath('users.png'),
    fullPage: true,
  })
  await page
    .getByRole('link', { name: 'View Synthetic review account' })
    .click()
  await page.getByLabel('Account role').selectOption('advisor')
  await page.getByLabel('Reason for change').fill('Synthetic browser role test')
  await page.getByRole('button', { name: 'Review role change' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText(address)
  await expect(
    page.getByRole('button', { name: 'Cancel', exact: true }),
  ).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).not.toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Review role change' }),
  ).toBeFocused()
  await page.getByRole('button', { name: 'Review role change' }).click()
  await page.getByRole('button', { name: 'Confirm change' }).click()
  await expect(page.getByRole('status')).toContainText('Account updated')
  await farmerPage.reload()
  await expect(
    farmerPage.getByRole('heading', { name: 'Log in' }),
  ).toBeVisible()
  await page
    .getByLabel('Reason for change')
    .fill('Synthetic browser disable test')
  await page
    .getByRole('button', { name: 'Disable account', exact: true })
    .click()
  await page.getByRole('button', { name: 'Confirm change' }).click()
  await expect(page.getByText('Disabled', { exact: true })).toBeVisible()
  await page
    .getByLabel('Reason for change')
    .fill('Synthetic browser re-enable test')
  await page
    .getByRole('button', { name: 'Re-enable account', exact: true })
    .click()
  await page.getByRole('button', { name: 'Confirm change' }).click()
  await expect(page.getByText('Active', { exact: true })).toBeVisible()
  await login(farmerPage, address)
  await expect(
    farmerPage.getByRole('heading', { name: 'My account.' }),
  ).toBeVisible()
  await page
    .getByLabel('Reason for change')
    .fill('Synthetic unauthorized account removal')
  await page.getByRole('button', { name: 'Remove account' }).click()
  const removal = page.getByRole('dialog')
  await expect(removal).toContainText('This cannot be undone')
  await page.getByRole('button', { name: 'Confirm change' }).click()
  await expect(page).toHaveURL(/status=deleted/)
  await expect(
    page
      .getByRole('list')
      .getByText('Deleted account', { exact: true })
      .first(),
  ).toBeVisible()
  const removedAfter = await request.get(
    `${apiRoot}/admin/users?status=deleted`,
    { headers: adminHeaders },
  )
  expect((await removedAfter.json()).total).toBe(deletedBefore + 1)
  await openMenu(page)
  await page.getByRole('link', { name: /Audit history/ }).click()
  await expect(
    page.getByRole('heading', { name: 'Audit history.' }),
  ).toBeVisible()
  await expect(
    page
      .getByRole('region', { name: 'Recorded actions' })
      .getByRole('list')
      .getByText('Account removed')
      .first(),
  ).toBeVisible()
  await farmerPage.reload()
  await expect(
    farmerPage.getByRole('heading', { name: 'Log in' }),
  ).toBeVisible()
  await farmerPage.getByLabel('Email address').fill(address)
  await farmerPage.getByLabel('Password', { exact: true }).fill(password)
  await farmerPage
    .getByRole('button', { name: 'Sign in', exact: false })
    .click()
  await expect(farmerPage.getByRole('alert')).toContainText('incorrect')
  await fit(page)
  await farmerContext.close()
})
