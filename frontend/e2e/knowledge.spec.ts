import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from '@playwright/test'
import { execFile } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import { apiRoot, webOrigin } from './environment.ts'

async function openKnowledge(page: Page) {
  await page.goto('/login', { waitUntil: 'domcontentloaded' })
  await page
    .getByLabel('Email address')
    .fill(`browser-admin-${process.env.E2E_RUN_ID}@example.com`)
  await page
    .getByLabel('Password', { exact: true })
    .fill(process.env.E2E_PASSWORD!)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL('/admin/overview')
  const menu = page.getByRole('button', { name: 'Menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('link', { name: 'Knowledge Sources' }).click()
  await expect(
    page.getByRole('heading', { name: 'Knowledge Sources' }),
  ).toBeVisible()
}

function fixturePython() {
  const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
  const python = join(
    backend,
    '.venv',
    process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
  )
  return { backend, python }
}

async function processQueuedPdfs() {
  const { backend, python } = fixturePython()
  await promisify(execFile)(
    python,
    ['tests/browser_server.py', '--process-pdfs'],
    {
      cwd: backend,
      timeout: 20000,
    },
  )
}

async function reviewedExcerptsPdf(quotes: string[]) {
  const { backend, python } = fixturePython()
  const { stdout } = await promisify(execFile)(
    python,
    [
      '-c',
      'import sys\nfrom app.modules.knowledge.preview_fixture import fixture_pdf\nsys.stdout.buffer.write(fixture_pdf(tuple(sys.argv[1:])))',
      ...quotes,
    ],
    { cwd: backend, encoding: 'buffer', timeout: 10_000 },
  )
  return stdout
}

test('administrator assigns a PDF version and the advisor reviews it', async ({
  page,
  request,
  browser,
}) => {
  const web = { Origin: webOrigin, 'X-WagaMaga-Client': 'web' }
  const suffix = randomBytes(6).toString('hex')
  const email = `knowledge-review-${suffix}@example.com`
  const title = `Synthetic review ${suffix}`
  const password = process.env.E2E_PASSWORD!
  const signup = await request.post(`${apiRoot}/auth/register`, {
    headers: web,
    data: { email, password, display_name: 'Synthetic knowledge advisor' },
  })
  expect(signup.ok()).toBe(true)
  const participant = await request.post(`${apiRoot}/auth/login`, {
    headers: web,
    data: { email, password },
  })
  expect(participant.ok()).toBe(true)
  const profile = await request.get(`${apiRoot}/me`, {
    headers: {
      ...web,
      Authorization: `Bearer ${(await participant.json()).access_token}`,
    },
  })
  expect(profile.ok()).toBe(true)
  const person = await profile.json()
  const admin = await request.post(`${apiRoot}/auth/login`, {
    headers: web,
    data: {
      email: `browser-admin-${process.env.E2E_RUN_ID}@example.com`,
      password,
    },
  })
  expect(admin.ok()).toBe(true)
  const promotion = await request.patch(
    `${apiRoot}/admin/users/${person.id}/role`,
    {
      headers: {
        ...web,
        Authorization: `Bearer ${(await admin.json()).access_token}`,
      },
      data: {
        role: 'advisor',
        expected_version: person.version,
        reason: 'Synthetic knowledge review test',
      },
    },
  )
  expect(promotion.ok()).toBe(true)

  await openKnowledge(page)
  await page.getByLabel('Source title').fill(title)
  await page.getByLabel('Synthetic PDF').setInputFiles({
    name: 'review.pdf',
    mimeType: 'application/pdf',
    buffer: await reviewedExcerptsPdf([
      'First synthetic study page.',
      'Second synthetic study page.',
    ]),
  })
  const saved = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/admin/knowledge/sources/pdf') &&
      response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  expect((await saved).status()).toBe(201)
  await processQueuedPdfs()
  await page.getByRole('button', { name: 'Refresh sources' }).click()
  const card = page
    .getByRole('article')
    .filter({ has: page.getByRole('heading', { name: title }) })
  await card.getByText('Advisor review', { exact: true }).click()
  await card.getByLabel('Advisor email').fill(email)
  await card
    .getByRole('button', { name: 'Assign advisor', exact: true })
    .click()
  await expect(
    card.getByText('Awaiting advisor review', { exact: true }),
  ).toBeVisible()

  const advisorContext = await browser.newContext({
    viewport: page.viewportSize(),
  })
  try {
    const advisor = await advisorContext.newPage()
    await advisor.goto(`${webOrigin}/login`)
    await advisor.getByLabel('Email address').fill(email)
    await advisor.getByLabel('Password', { exact: true }).fill(password)
    await advisor.getByRole('button', { name: 'Sign in', exact: true }).click()
    await expect(advisor).toHaveURL(/\/advisor$/)
    await advisor.getByRole('link', { name: title, exact: true }).click()
    const review = advisor
      .getByRole('article')
      .filter({ has: advisor.getByRole('heading', { name: title }) })
    const evidence = review.getByRole('region', { name: 'Extracted PDF text' })
    await expect(
      evidence.getByText('First synthetic study page.'),
    ).toBeVisible()
    const reason = review.getByLabel('Review reason')
    await reason.fill('Checked both pages of the synthetic source.')
    await evidence.getByLabel('Jump to page').fill('2')
    await evidence.getByRole('button', { name: 'Go to page' }).click()
    await expect(
      evidence.getByText('Second synthetic study page.'),
    ).toBeVisible()
    await expect(reason).toHaveValue(
      'Checked both pages of the synthetic source.',
    )
    await review.getByLabel('Review outcome').selectOption('approved')
    await review.getByRole('button', { name: 'Submit decision' }).click()
    await expect(
      review.getByText('Approved by advisor', { exact: true }),
    ).toBeVisible()
    await advisor.getByRole('link', { name: 'All knowledge reviews' }).click()
    await expect(
      advisor.getByText('No PDF versions are assigned to you.'),
    ).toBeVisible()
    await advisor.getByRole('button', { name: 'Recently reviewed' }).click()
    await expect(
      advisor.getByRole('link', { name: title, exact: true }),
    ).toBeVisible()
  } finally {
    await advisorContext.close()
  }
  await page.getByRole('button', { name: 'Refresh sources' }).click()
  await expect(
    card.getByRole('button', { name: 'Mark as reviewed' }),
  ).toBeVisible()
  for (const [label, status] of [
    ['Mark as reviewed', 'reviewed'],
    ['Publish', 'published'],
  ]) {
    await card.getByRole('button', { name: label, exact: true }).click()
    await page
      .getByRole('dialog')
      .getByRole('button', { name: label, exact: true })
      .click()
    await expect(card.getByText(status, { exact: true })).toBeVisible()
  }
})

test('live Gemini demo answers with the published page citation', async ({
  page,
}) => {
  test.skip(
    process.env.E2E_LIVE_GEMINI !== '1',
    'Requires explicit live-provider opt-in',
  )
  await openKnowledge(page)
  const added = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/v1/admin/knowledge/sources' &&
      response.request().method() === 'POST' &&
      response.status() === 201,
  )
  await page
    .getByRole('button', { name: 'Add Gemini demo PDF', exact: true })
    .click()
  const { id } = await (await added).json()
  await processQueuedPdfs()
  await page
    .getByRole('button', { name: 'Refresh sources', exact: true })
    .click()
  const card = page
    .getByRole('article')
    .filter({ hasText: `Version ${id.slice(0, 8)}` })
  for (const [label, status] of [
    ['Mark as reviewed', 'reviewed'],
    ['Publish', 'published'],
  ]) {
    await card.getByRole('button', { name: label, exact: true }).click()
    await page
      .getByRole('dialog')
      .getByRole('button', { name: label, exact: true })
      .click()
    await expect(card.getByText(status, { exact: true })).toBeVisible()
  }
  const preview = page.getByRole('region', { name: 'Gemini answer preview' })
  await preview.getByRole('button', { name: 'Ask Gemini' }).click()
  const answer = preview.getByRole('article', { name: 'Cited answer' })
  await expect(answer).toContainText('DEMO-NURSERY-A')
  await expect(answer).toContainText('Fictional chilli field notebook · Page 1')
  await preview.getByLabel('Demo question').selectOption('forecast')
  await preview.getByRole('button', { name: 'Ask Gemini' }).click()
  await expect(preview.getByRole('status')).toHaveText('No evidence found.')
  await card.getByRole('button', { name: 'Withdraw', exact: true }).click()
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Withdraw', exact: true })
    .click()
  await expect(card.getByText('withdrawn', { exact: true })).toBeVisible()
})

test('Gemini preview returns no evidence for the forecast question', async ({
  page,
}) => {
  await openKnowledge(page)
  const preview = page.getByRole('region', { name: 'Gemini answer preview' })
  await preview.getByLabel('Demo question').selectOption('forecast')
  await preview.getByRole('button', { name: 'Ask Gemini' }).click()
  await expect(preview.getByRole('status')).toHaveText('No evidence found.')
})

test('evaluation saves a missing evidence decision for one of ten questions', async ({
  page,
}) => {
  await openKnowledge(page)
  await page
    .getByRole('link', { name: 'Review the 10 chilli questions' })
    .click()
  await expect(
    page.getByRole('heading', { name: 'Chilli evidence evaluation' }),
  ).toBeVisible()
  const questions = page.getByLabel('Evaluation question')
  await expect(questions.locator('option')).toHaveCount(10)
  await questions.selectOption('CH-08')
  await expect(
    page.getByRole('heading', {
      name: 'How much rain will my field get tomorrow?',
    }),
  ).toBeVisible()
  const note = `Synthetic missing forecast ${randomBytes(4).toString('hex')}`
  await page.getByLabel('Review note (optional)').fill(note)
  await page.getByRole('button', { name: 'Mark evidence missing' }).click()
  await expect(page.getByText(note, { exact: false })).toBeVisible()
  await page.reload()
  await questions.selectOption('CH-08')
  await expect(page.getByText(note, { exact: false })).toBeVisible()
  await page.getByRole('link', { name: 'Open Gemini scoring' }).click()
  const forecast = page.getByRole('article').filter({ hasText: 'CH-08' })
  await forecast.getByRole('button', { name: 'Run check' }).click()
  await expect(forecast.getByText('Passed', { exact: true })).toBeVisible()
  await expect(
    forecast.getByText('No evidence found', { exact: true }),
  ).toBeVisible()
  await expect(page.getByText(/Farmer pilot awaiting checks/)).toBeVisible()
})

async function openTestFarmer(page: Page, request: APIRequestContext) {
  const email = `chilli-${randomBytes(6).toString('hex')}@example.com`
  const password = process.env.E2E_PASSWORD!
  const registered = await request.post(`${apiRoot}/auth/register`, {
    timeout: 10_000,
    headers: { Origin: webOrigin, 'X-WagaMaga-Client': 'web' },
    data: { email, password, display_name: 'Synthetic chilli farmer' },
  })
  expect(registered.ok()).toBe(true)
  await page.goto('/login', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL('/')
}

test('farmer reads a published chilli study and its cited page from home', async ({
  page,
  request,
}) => {
  await openTestFarmer(page, request)
  const ask = page.getByRole('link', { name: 'Ask Chilli AI' })
  await expect(ask).toBeInViewport()
  await ask.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL('/knowledge/chilli')
  const example = 'Where was the dry zone chilli field study conducted?'
  await page.getByRole('button', { name: example, exact: true }).click()
  const question = page.getByLabel('What would you like to ask about chilli?')
  await expect(question).toHaveValue(example)
  await question.fill('Where was the Anuradhapura chili trial?')
  const find = page.getByRole('button', { name: 'Find an answer' })
  await find.click()
  const answer = page.getByRole('article', { name: 'Cited answer' })
  await expect(answer).toContainText('28 farmers')
  await expect(answer).toContainText('Tirappane')
  await expect(answer).toContainText('Journal page 32 · PDF page 3')
  const supporting = answer.getByRole('button', {
    name: 'View source',
  })
  const sourceRoute = '**/api/v1/knowledge/chilli/research/sources/**'
  await page.route(sourceRoute, (route) =>
    route.fulfill({ status: 503, json: {} }),
  )
  await supporting.focus()
  await page.keyboard.press('Enter')
  await expect(
    answer.getByRole('button', { name: 'Hide source' }),
  ).toHaveAttribute('aria-expanded', 'true')
  await expect(answer.getByRole('alert')).toContainText(
    'The supporting passage could not be loaded.',
  )
  await page.unroute(sourceRoute)
  await answer.getByRole('button', { name: 'Retry supporting passage' }).click()
  await expect(
    answer.getByRole('region', { name: 'Supporting passage' }),
  ).toContainText('Tirappane')
  await expect(
    answer.getByRole('link', { name: 'Read the published study' }),
  ).toHaveAttribute('href', 'https://doi.org/10.4038/ta.v173i1.128')
  await page
    .getByRole('button', {
      name: 'What should I check when choosing a chilli nursery site?',
    })
    .click()
  await find.click()
  await expect(answer).toContainText('sunny spot')
  await expect(answer).toContainText('Nursery preparation')
  await expect(
    answer.getByRole('link', {
      name: 'Read the Department of Agriculture source (Sinhala)',
    }),
  ).toHaveAttribute('href', 'https://doa.gov.lk/field-crops-chilli-si/')
  await question.fill(
    'Which factors affect the watering interval for field chillies?',
  )
  await find.click()
  await expect(answer).toContainText('soil texture')
  await question.fill('How much fertilizer should I apply?')
  await find.click()
  await expect(page.getByText('No evidence found.')).toBeVisible()
  await expect(answer).toHaveCount(0)
})

test('farmer sees the pending chilli pilot and can try the local demo', async ({
  page,
  request,
}) => {
  await openTestFarmer(page, request)
  await page.goto('/knowledge/chilli')
  await expect(
    page.getByRole('heading', { name: 'Ask Chilli AI' }),
  ).toBeVisible()
  await page.getByRole('link', { name: 'Chilli farm guidance' }).click()
  await expect(
    page.getByText('Scope · Chilli cultivations in Anuradhapura District.'),
  ).toBeVisible()
  await expect(
    page.getByText('Chilli answers are still being reviewed.'),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Find an answer' }),
  ).toHaveCount(0)

  await page.getByRole('link', { name: 'Back to Ask Chilli AI' }).click()
  if (process.env.E2E_BUILT_FRONTEND === '1') {
    await expect(
      page.getByRole('heading', { name: 'Ask Chilli AI' }),
    ).toBeVisible()
    await expect(
      page.getByRole('link', { name: 'Try the local demo' }),
    ).toHaveCount(0)
    return
  }
  await page.getByRole('link', { name: 'Try the local demo' }).click()
  await expect(
    page.getByRole('heading', { name: 'Chilli questions demo' }),
  ).toBeVisible()
  const question = page.getByLabel('What would you like to ask about chilli?')
  const find = page.getByRole('button', { name: 'Find an answer' })
  const answer = page.getByRole('article', { name: 'Cited answer' })
  const readPage = answer.getByRole('button', { name: 'Read cited page' })
  await expect(find).toBeDisabled()
  const nurseryExample = 'What label does the fictional nursery use?'
  await page.getByRole('button', { name: nurseryExample, exact: true }).click()
  await expect(question).toHaveValue(nurseryExample)
  await question.fill('Which label is on the seedling tray?')
  await find.click()
  await expect(answer).toContainText('DEMO-NURSERY-A')
  await expect(answer).toContainText(
    'Fictional chilli farmer notebook · Page 1',
  )
  await readPage.click()
  await expect(answer.getByText(/DEMO-NURSERY-A/)).toHaveCount(2)

  await question.fill('How often should I water chilli?')
  await expect(answer).toHaveCount(0)
  await find.click()
  await expect(page.getByText('No evidence found.')).toBeVisible()
  await expect(answer).toHaveCount(0)

  for (const [typed, quote, number] of [
    ['What information is recorded in the watering log?', 'watering date', 3],
    ['What fields are in the fertiliser log?', 'soil test reference', 4],
  ] as const) {
    await question.fill(typed)
    await find.click()
    await expect(answer).toContainText(
      `Fictional chilli farmer notebook · Page ${number}`,
    )
    await readPage.click()
    await expect(answer.getByText(quote, { exact: false })).toHaveCount(2)
  }

  await page.getByRole('link', { name: 'Back to Ask Chilli AI' }).click()
  await expect(
    page.getByRole('heading', { name: 'Ask Chilli AI', exact: true }),
  ).toBeVisible()
})

test('farmer searches reviewed excerpts locally', async ({ page, request }) => {
  if (process.env.E2E_BUILT_FRONTEND === '1') {
    await openTestFarmer(page, request)
    await page.goto('/knowledge/chilli')
    await expect(
      page.getByRole('heading', { name: 'Ask Chilli AI' }),
    ).toBeVisible()
    await expect(
      page.getByRole('link', { name: 'Search reviewed excerpts locally' }),
    ).toHaveCount(0)
    return
  }
  page.setDefaultTimeout(10_000)
  page.setDefaultNavigationTimeout(12_000)
  const web = { Origin: webOrigin, 'X-WagaMaga-Client': 'web' }
  const admin =
    await test.step('Authenticate the evidence manager', async () => {
      const login = await request.post(`${apiRoot}/auth/login`, {
        headers: web,
        timeout: 10_000,
        data: {
          email: `browser-admin-${process.env.E2E_RUN_ID}@example.com`,
          password: process.env.E2E_PASSWORD!,
        },
      })
      expect(login.ok()).toBe(true)
      return {
        ...web,
        Authorization: `Bearer ${(await login.json()).access_token}`,
      }
    })
  const root = `${apiRoot}/admin/knowledge`
  const fixtures = [
    [
      'CH-01',
      'How do I choose a site for a chilli nursery?',
      'The fictional nursery review records the conditions for its example site.',
    ],
    [
      'CH-04',
      'What should I check before watering newly planted chilli?',
      'The fictional irrigation review checks field conditions in a sample plot.',
    ],
    [
      'CH-05',
      'Should I test the soil before choosing basal fertiliser?',
      'The fictional fertilizer review uses a sample soil test reference.',
    ],
  ] as const
  const pdf = await test.step('Generate the synthetic three-page PDF', () =>
    reviewedExcerptsPdf(fixtures.map(([, , quote]) => quote)))
  const { id } = await test.step('Upload synthetic evidence', async () => {
    const upload = await request.post(`${root}/sources/pdf`, {
      headers: { ...admin, 'Content-Type': 'application/pdf' },
      data: pdf,
      timeout: 12_000,
    })
    expect(upload.status()).toBe(201)
    return await upload.json()
  })
  await test.step('Extract the uploaded PDF', processQueuedPdfs)

  await test.step(
    'Open the local excerpts as a farmer',
    async () => {
      await openTestFarmer(page, request)
      await page.goto('/knowledge/chilli', { waitUntil: 'domcontentloaded' })
      await page
        .getByRole('link', { name: 'Search reviewed excerpts locally' })
        .click()
      await expect(page).toHaveURL('/knowledge/chilli/local')
      await expect(
        page.getByRole('heading', { name: 'Search reviewed chilli excerpts' }),
      ).toBeVisible()
    },
    { timeout: 25_000 },
  )
  const question = page.getByLabel('What would you like to ask about chilli?')
  const find = page.getByRole('button', { name: 'Find an answer' })
  await test.step('Unreviewed evidence is unavailable', async () => {
    await question.fill(fixtures[0][1])
    await find.click()
    await expect(page.getByText('No evidence found.')).toBeVisible()
  })

  await test.step('Review and publish the source', async () => {
    for (const [action, revision] of [
      ['review', 1],
      ['publish', 2],
    ] as const) {
      const changed = await request.post(`${root}/sources/${id}/${action}`, {
        headers: admin,
        timeout: 10_000,
        data: { expected_revision: revision },
      })
      expect(changed.ok()).toBe(true)
    }
  })
  for (const [index, [caseId, typed, quote]] of fixtures.entries()) {
    const sourcePage = index + 1
    await test.step(
      `Approve and verify excerpt ${caseId}`,
      async () => {
        const current = await request.get(`${root}/evaluation/${caseId}`, {
          headers: admin,
        })
        expect(current.ok()).toBe(true)
        const approval = await request.post(
          `${root}/evaluation/${caseId}/decisions`,
          {
            headers: admin,
            data: {
              expected_revision: (await current.json()).revision,
              outcome: 'suitable',
              version_id: id,
              page_number: sourcePage,
              approved_excerpt: quote,
            },
          },
        )
        expect(approval.status()).toBe(201)
        await question.fill(typed)
        await find.click()
        const answer = page.getByRole('article', { name: 'Cited answer' })
        await expect(answer).toContainText(quote)
        await expect(answer).toContainText(`Page ${sourcePage}`)
        await answer.getByRole('button', { name: 'Read cited page' }).click()
        await expect(answer.getByText(quote, { exact: false })).toHaveCount(2)
      },
      { timeout: 18_000 },
    )
  }
  await test.step('Withdrawal removes the cited excerpts', async () => {
    const withdrawn = await request.post(`${root}/sources/${id}/withdraw`, {
      headers: admin,
      timeout: 10_000,
      data: { expected_revision: 3 },
    })
    expect(withdrawn.ok()).toBe(true)
    await question.fill(fixtures[0][1])
    await find.click()
    await expect(page.getByText('No evidence found.')).toBeVisible()
  })
})

test('admin can remove a queued PDF after confirming', async ({
  page,
  context,
}) => {
  const document = await context.newPage()
  await document.setContent('<p>Fictional PDF to remove</p>')
  const buffer = await document.pdf()
  await document.close()
  await openKnowledge(page)
  await page.getByLabel('Synthetic PDF').setInputFiles({
    name: 'remove.pdf',
    mimeType: 'application/pdf',
    buffer,
  })
  const added = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname ===
        '/api/v1/admin/knowledge/sources/pdf' &&
      response.request().method() === 'POST' &&
      response.status() === 201,
  )
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  const { id } = await (await added).json()
  const card = page
    .getByRole('article')
    .filter({ hasText: `Version ${id.slice(0, 8)}` })
  await card.getByRole('button', { name: 'Remove PDF', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(
    dialog.getByText(/stored original and decision history/),
  ).toBeVisible()
  await dialog.getByRole('button', { name: 'Remove PDF', exact: true }).click()
  await expect(
    page
      .getByRole('status', { name: '' })
      .filter({ hasText: 'Loading source versions' }),
  ).toHaveCount(0)
  await expect(card).toHaveCount(0)
  await page.reload()
  await expect(
    page.getByRole('heading', { name: 'Knowledge Sources' }),
  ).toBeVisible()
  await expect(card).toHaveCount(0)
})

test('admin reviews, publishes and withdraws a synthetic guide', async ({
  page,
}) => {
  await openKnowledge(page)
  const added = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/v1/admin/knowledge/sources' &&
      response.request().method() === 'POST' &&
      response.status() === 201,
  )
  await page.getByRole('button', { name: 'Add synthetic guide' }).click()
  const { id } = await (await added).json()
  const card = page
    .getByRole('article')
    .filter({ hasText: `Version ${id.slice(0, 8)}` })
  await expect(card.getByText('draft', { exact: true })).toBeVisible()
  for (const [label, status] of [
    ['Mark as reviewed', 'reviewed'],
    ['Publish', 'published'],
    ['Withdraw', 'withdrawn'],
  ]) {
    await card.getByRole('button', { name: label, exact: true }).click()
    await page
      .getByRole('dialog')
      .getByRole('button', { name: label, exact: true })
      .click()
    await expect(card.getByText(status, { exact: true })).toBeVisible()
  }
  await page.reload()
  await expect(card.getByText('withdrawn', { exact: true })).toBeVisible()
})

test('uploaded PDF shows page text after the worker runs', async ({
  page,
  context,
}) => {
  const narrow = page.viewportSize()?.width === 360
  if (narrow) await page.setViewportSize({ width: 320, height: 760 })
  const document = await context.newPage()
  const keyword = `pilot${randomBytes(6).toString('hex')}`
  await document.setContent(
    `<p>Fictional first page</p><p style="break-before: page">Fictional second page ${keyword}</p>`,
  )
  const buffer = await document.pdf()
  await document.close()
  await openKnowledge(page)
  await page.getByLabel('Include in the reviewed PDF library').check()
  await page.getByLabel('Publisher').fill('Synthetic publisher')
  await page
    .getByLabel('Library access after publication')
    .selectOption('farmers')
  await page.getByLabel('Synthetic PDF').setInputFiles({
    name: 'synthetic.pdf',
    mimeType: 'application/pdf',
    buffer,
  })
  const added = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname ===
        '/api/v1/admin/knowledge/sources/pdf' &&
      response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  const response = await added
  expect(response.status()).toBe(201)
  const { id, rag_metadata } = await response.json()
  expect(rag_metadata).toMatchObject({
    publisher: 'Synthetic publisher',
    crop: 'chilli',
    region: 'anuradhapura',
    access: 'farmers',
  })
  const card = page
    .getByRole('article')
    .filter({ hasText: `Version ${id.slice(0, 8)}` })
  await expect(card.getByText(/Waiting for text extraction/)).toBeVisible()
  await card.getByText('Version details', { exact: true }).click()
  await expect(card.getByText(`Source version · ${id}`)).toBeVisible()
  expect(
    await page.evaluate(
      () => window.document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
  await expect(
    card.getByRole('button', { name: 'Mark as reviewed' }),
  ).toHaveCount(0)

  await processQueuedPdfs()
  await page.getByRole('button', { name: 'Refresh sources' }).click()
  await card.getByRole('button', { name: 'View extracted text' }).click()
  for (const [number, body] of [
    [1, 'Fictional first page'],
    [2, `Fictional second page ${keyword}`],
  ]) {
    await expect(
      card.getByRole('heading', { name: `Page ${number}` }),
    ).toBeVisible()
    await expect(card.getByText(body.toString(), { exact: true })).toBeVisible()
  }
  for (const [label, status] of [
    ['Mark as reviewed', 'reviewed'],
    ['Publish', 'published'],
  ]) {
    await card.getByRole('button', { name: label, exact: true }).click()
    await page
      .getByRole('dialog')
      .getByRole('button', { name: label, exact: true })
      .click()
    await expect(card.getByText(status, { exact: true })).toBeVisible()
  }
  const search = page.getByRole('region', { name: 'Search published PDFs' })
  const keywords = search.getByLabel('Keywords')
  const matchingPage = search
    .getByRole('article')
    .filter({ hasText: `Page 2 · Version ${id.slice(0, 8)}` })
  await keywords.fill(keyword)
  await search.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(matchingPage).toBeVisible()
  await matchingPage.getByText('Citation details', { exact: true }).click()
  await expect(
    matchingPage.getByText(`Version ID: ${id}`, { exact: true }),
  ).toBeVisible()
  await keywords.fill('nonesuchkeyword')
  await search.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(search.getByRole('status')).toContainText('No evidence found')
  await card.getByRole('button', { name: 'Upload replacement PDF' }).click()
  const revisedKeyword = `revision${randomBytes(12).toString('hex')}`
  const revisedTitle = `Revised chilli reference ${revisedKeyword}`
  await page.getByLabel('Source title').fill(revisedTitle)
  await page.getByLabel('Synthetic PDF').setInputFiles({
    name: 'replacement.pdf',
    mimeType: 'application/pdf',
    buffer: await reviewedExcerptsPdf([`Revised notes ${revisedKeyword}`]),
  })
  const replacementUpload = page.waitForResponse(
    (item) =>
      new URL(item.url()).pathname === '/api/v1/admin/knowledge/sources/pdf' &&
      item.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  const replacement = await replacementUpload
  expect(replacement.status()).toBe(201)
  expect((await replacement.json()).replaces_version_id).toBe(id)
  await expect(card.getByText('published', { exact: true })).toBeVisible()
  await processQueuedPdfs()
  await page.getByRole('button', { name: 'Refresh sources' }).click()
  const revised = page.getByRole('article').filter({
    has: page.getByRole('heading', { name: revisedTitle, exact: true }),
  })
  for (const [label, status] of [
    ['Mark as reviewed', 'reviewed'],
    ['Publish', 'published'],
  ]) {
    await revised.getByRole('button', { name: label, exact: true }).click()
    await page
      .getByRole('dialog')
      .getByRole('button', { name: label, exact: true })
      .click()
    await expect(revised.getByText(status, { exact: true })).toBeVisible()
  }
  await expect(card.getByText('withdrawn', { exact: true })).toBeVisible()
  expect(
    await page.evaluate(() => window.document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(page.viewportSize()!.width)
  await keywords.fill(keyword)
  await search.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(search.getByRole('status')).toContainText('No evidence found')
  await expect(matchingPage).toHaveCount(0)
  await keywords.fill(revisedKeyword)
  await search.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(search.getByRole('article')).toContainText(revisedTitle)
})
