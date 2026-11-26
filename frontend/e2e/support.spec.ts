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
async function actor(request: APIRequestContext) {
  const email = `support-${randomBytes(6).toString('hex')}@example.com`
  expect(
    (
      await request.post(apiRoot + '/auth/register', {
        headers,
        data: { email, password, display_name: 'Synthetic support farmer' },
      })
    ).ok(),
  ).toBe(true)
  const response = await request.post(apiRoot + '/auth/login', {
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
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
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

test('public Help leads to private farmer requests, admin replies and resolution', async ({
  page,
  request,
  browser,
}, info) => {
  const farmer = await actor(request)
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  const homeMenu = page.getByRole('button', { name: 'Menu', exact: true })
  if (await homeMenu.isVisible()) await homeMenu.click()
  await page
    .getByRole('banner')
    .getByRole('link', { name: 'Help', exact: true })
    .click()
  await expect(
    page.getByRole('heading', { name: 'How can we help?', exact: true }),
  ).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('help-introduction.png'),
    fullPage: false,
  })
  await page.getByText('Where are my archived farms?', { exact: true }).click()
  await expect(
    page.getByText('Open My Farms and choose Farm status', { exact: false }),
  ).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('public-help.png'),
    fullPage: false,
  })
  await page
    .getByRole('link', { name: 'Log in to send a request', exact: true })
    .click()
  await expect(page).toHaveURL('/login')
  await expect(
    page.getByRole('link', { name: 'Need help signing in?' }),
  ).toHaveAttribute('href', '/help#sign-in')
  await login(page, farmer.email)
  await page.goto('/help')
  await page.getByRole('link', { name: /Contact website support/ }).click()
  const subject = `Synthetic support ${randomBytes(4).toString('hex')}`
  await page
    .getByLabel('What do you need help with?')
    .selectOption('farm_records')
  await page.getByLabel('Subject', { exact: true }).fill(subject)
  await page
    .getByLabel('Your message', { exact: true })
    .fill('I need help saving my farm. <b>Literal submitted text</b>')
  await expect(
    page.getByText(
      'No farm details or observations are attached automatically.',
      { exact: false },
    ),
  ).toBeVisible()
  await fit(page)
  await page.screenshot({
    path: info.outputPath('new-support-request.png'),
    fullPage: true,
  })
  const sent = page.waitForRequest(
    (r) =>
      new URL(r.url()).pathname === '/api/v1/support/tickets' &&
      r.method() === 'POST',
  )
  await page.getByRole('button', { name: 'Send request', exact: true }).click()
  expect(Object.keys((await sent).postDataJSON()).sort()).toEqual([
    'body',
    'category',
    'subject',
  ])
  await expect(
    page.getByRole('heading', { name: subject + '.', exact: true }),
  ).toBeVisible()
  const ticketId = new URL(page.url()).pathname.split('/').at(-1)!
  await expect(
    page.getByText(
      'I need help saving my farm. <b>Literal submitted text</b>',
      { exact: true },
    ),
  ).toBeVisible()
  await expect(page.locator('.support-messages b')).toHaveCount(0)
  const adminContext = await browser.newContext({
    baseURL: webOrigin,
    viewport: page.viewportSize() ?? undefined,
  })
  const office = await adminContext.newPage()
  office.on('pageerror', (error) => errors.push(error.message))
  try {
    await login(office, adminEmail)
    await menu(office)
    await office
      .getByRole('link', { name: 'Support inbox', exact: true })
      .click()
    await office
      .getByRole('combobox', { name: 'Request status', exact: true })
      .selectOption('open')
    await fit(office)
    await office.screenshot({
      path: info.outputPath('admin-support-inbox.png'),
      fullPage: true,
    })
    await office.getByRole('link', { name: subject, exact: true }).click()
    await office
      .getByRole('button', { name: 'Mark in progress', exact: true })
      .click()
    await expect(office.getByText('In progress', { exact: true })).toBeVisible()
    await office
      .getByLabel('Your reply', { exact: true })
      .fill(
        'Please review the required fields. <b>Support text stays literal</b>',
      )
    await office
      .getByRole('button', { name: 'Send reply', exact: true })
      .click()
    await expect(office.getByText('Reply sent.', { exact: true })).toBeVisible()
    await fit(office)
    await office.screenshot({
      path: info.outputPath('admin-support-conversation.png'),
      fullPage: true,
    })
    await page
      .getByRole('button', { name: 'Refresh conversation', exact: true })
      .click()
    await expect(
      page.getByText(
        'Please review the required fields. <b>Support text stays literal</b>',
        { exact: true },
      ),
    ).toBeVisible()
    await expect(page.locator('.support-messages b')).toHaveCount(0)
    await fit(page)
    await page.screenshot({
      path: info.outputPath('farmer-support-conversation.png'),
      fullPage: true,
    })
    await menu(page)
    await page.getByRole('link', { name: /Notifications/ }).click()
    await expect(
      page.getByText('Support replied to your request', { exact: true }),
    ).toBeVisible()
    await expect(
      page.getByText('Please review the required fields.', { exact: false }),
    ).toHaveCount(0)
    await page
      .getByRole('link', { name: 'Open My support requests', exact: true })
      .first()
      .click()
    await page.getByRole('link', { name: subject, exact: true }).click()
    await page
      .getByLabel('Your reply', { exact: true })
      .fill('Thank you, that worked.')
    await expect(
      page.getByRole('button', { name: 'Mark resolved', exact: true }),
    ).toBeDisabled()
    await page.getByRole('button', { name: 'Send reply', exact: true }).click()
    await expect(page.getByText('Reply sent.', { exact: true })).toBeVisible()
    await page
      .getByRole('button', { name: 'Mark resolved', exact: true })
      .click()
    await expect(
      page.getByRole('button', { name: 'Reopen request', exact: true }),
    ).toBeVisible()
    await page
      .getByRole('button', { name: 'Reopen request', exact: true })
      .click()
    await expect(page.getByText('Open', { exact: true })).toBeVisible()
    await page.reload()
    await expect(
      page.getByText('Thank you, that worked.', { exact: true }),
    ).toBeVisible()
    expect(new URL(page.url()).pathname).toBe(`/support/${ticketId}`)
    expect(
      await page.evaluate(() => localStorage.length + sessionStorage.length),
    ).toBe(0)
    expect(errors).toEqual([])
  } finally {
    await adminContext.close()
  }
})

test('support foreign links, stale replies and revoked sessions preserve privacy', async ({
  page,
  request,
}) => {
  const owner = await actor(request)
  const other = await actor(request)
  const create = async (auth: typeof owner, subject: string) => {
    const result = await request.post(apiRoot + '/support/tickets', {
      headers: auth.headers,
      data: {
        category: 'technical',
        subject,
        body: 'Synthetic submitted message',
      },
    })
    expect(result.ok()).toBe(true)
    return result.json()
  }
  const own = await create(owner, 'Synthetic own support request')
  const foreign = await create(other, 'Other owner private support subject')
  const adminResponse = await request.post(apiRoot + '/auth/login', {
    headers,
    data: { email: adminEmail, password },
  })
  const admin = {
    ...headers,
    Authorization: `Bearer ${(await adminResponse.json()).access_token}`,
  }
  await login(page, owner.email)
  await page.goto(`/support/${foreign.id}`)
  await expect(
    page.getByRole('heading', { name: 'Request unavailable', exact: true }),
  ).toBeVisible()
  await expect(page.getByText(foreign.subject, { exact: false })).toHaveCount(0)
  await page.goto('/admin/support')
  await expect(
    page.getByRole('heading', { name: 'Access denied', exact: true }),
  ).toBeVisible()
  await page.goto(`/support/${own.id}`)
  await page
    .getByLabel('Your reply', { exact: true })
    .fill('My unsent stale reply')
  expect(
    (
      await request.post(
        apiRoot + `/admin/support/tickets/${own.id}/messages`,
        {
          headers: admin,
          data: { expected_version: 1, body: 'Concurrent support response' },
        },
      )
    ).ok(),
  ).toBe(true)
  await page.getByRole('button', { name: 'Send reply', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText(
    'Your message has not been sent',
  )
  await expect(page.getByLabel('Your reply', { exact: true })).toHaveValue(
    'My unsent stale reply',
  )
  await expect(
    page.getByRole('button', { name: 'Send reply', exact: true }),
  ).toBeDisabled()
  await page
    .getByRole('button', { name: 'Reload latest conversation', exact: true })
    .click()
  await expect(
    page.getByText('Concurrent support response', { exact: true }),
  ).toBeVisible()
  await expect(page.getByLabel('Your reply', { exact: true })).toHaveValue('')
  await page
    .getByLabel('Your reply', { exact: true })
    .fill('Private revoked draft')
  expect(
    (
      await request.patch(apiRoot + `/admin/users/${owner.user.id}/status`, {
        headers: admin,
        data: {
          enabled: false,
          expected_version: 1,
          reason: 'Synthetic support revocation check',
        },
      })
    ).ok(),
  ).toBe(true)
  let attempted = 0
  page.on('request', (r) => {
    if (
      new URL(r.url()).pathname ===
        `/api/v1/support/tickets/${own.id}/messages` &&
      r.method() === 'POST'
    )
      attempted++
  })
  await page.getByRole('button', { name: 'Send reply', exact: true }).click()
  await expect(page).toHaveURL('/login')
  await expect(
    page.getByText('Private revoked draft', { exact: false }),
  ).toHaveCount(0)
  expect(attempted).toBe(1)
})
