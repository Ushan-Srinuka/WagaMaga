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

async function taskCultivation(
  request: APIRequestContext,
  owner: Awaited<ReturnType<typeof actor>>,
) {
  const createdFarm = await request.post(root + '/farms', {
    headers: owner.headers,
    data: { name: 'Synthetic task farm', location: 'Synthetic village' },
  })
  expect(createdFarm.ok()).toBe(true)
  const farm = await createdFarm.json()
  const crops = await request.get(root + '/crop-types', {
    headers: owner.headers,
  })
  expect(crops.ok()).toBe(true)
  const { items } = await crops.json()
  const chilli = items.find((crop: { code: string }) => crop.code === 'chilli')
  const createdCultivation = await request.post(
    root + `/farms/${farm.id}/cultivations`,
    {
      headers: owner.headers,
      data: {
        crop_type_id: chilli.id,
        planting_date: '2099-01-15',
        area_value: '1',
        area_unit: 'ha',
      },
    },
  )
  expect(createdCultivation.ok()).toBe(true)
  const cultivation = await createdCultivation.json()
  return `/farms/${farm.id}/cultivations/${cultivation.id}`
}

test('farmer manages manual tasks and sees their cultivation history', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic task farmer')
  const cultivation = await taskCultivation(request, owner)
  await login(page, owner.email)
  await page.goto(cultivation)
  const tasks = page.getByRole('region', { name: 'Farm tasks' })

  async function addTask(title: string) {
    await tasks.getByRole('button', { name: 'Add task' }).click()
    await tasks.getByLabel('Task title').fill(title)
    await tasks.getByLabel('Due date').fill('2099-01-16')
    await fit(page)
    await tasks.getByRole('button', { name: 'Save task' }).click()
    await expect(tasks.getByRole('heading', { name: title })).toBeVisible()
  }

  await addTask('Check plot markers')
  await page.reload()
  const task = tasks
    .getByRole('article')
    .filter({ hasText: 'Check plot markers' })
  await expect(task.getByText('Due 2099-01-16')).toBeVisible()
  await task.getByRole('button', { name: 'Edit task' }).click()
  await tasks.getByLabel('Due date').fill('2099-01-17')
  await tasks.getByRole('button', { name: 'Save task' }).click()
  await expect(task.getByText('Due 2099-01-17')).toBeVisible()
  await task.getByRole('button', { name: 'Mark complete' }).click()
  await expect(tasks.getByText('No pending tasks.')).toBeVisible()

  await addTask('Copy plot labels')
  const another = tasks
    .getByRole('article')
    .filter({ hasText: 'Copy plot labels' })
  await another.getByRole('button', { name: 'Cancel task' }).click()
  await expect(tasks.getByText('No pending tasks.')).toBeVisible()
  await tasks.getByLabel('Task status').selectOption('all')
  await expect(task.getByText('Completed', { exact: true })).toBeVisible()
  await expect(another.getByText('Cancelled', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Cultivation history' }).click()
  const history = page.getByRole('region', { name: 'Task history' })
  await expect(history.getByText('Completed · Due 2099-01-17')).toBeVisible()
  await expect(history.getByText('Cancelled · Due 2099-01-16')).toBeVisible()
  await expect(history.getByRole('article')).toHaveCount(5)
  await fit(page)
})

test('farmer reviews a missed task and decides whether to move it', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic missed-task farmer')
  const cultivation = await taskCultivation(request, owner)
  const taskPath = root + cultivation + '/tasks'
  const listed = await request.get(taskPath, { headers: owner.headers })
  expect(listed.ok()).toBe(true)
  const today: string = (await listed.json()).farm_today
  const yesterday = new Date(`${today}T12:00:00Z`)
  yesterday.setUTCDate(yesterday.getUTCDate() - 1)
  const original = yesterday.toISOString().slice(0, 10)
  const created = await request.post(taskPath, {
    headers: owner.headers,
    data: { title: 'Synthetic missed field check', due_date: original },
  })
  expect(created.ok()).toBe(true)
  await login(page, owner.email)
  await page.goto(cultivation)
  const task = page.getByRole('article').filter({
    has: page.getByRole('heading', {
      name: 'Synthetic missed field check',
      exact: true,
    }),
  })
  const missed = task.getByRole('button', { name: 'I missed this task' })
  const review = task.getByRole('region', { name: 'Review missed task' })
  await missed.click()
  await review.getByLabel('Proposed date').fill(today)
  await review
    .getByLabel('Why was it missed? (optional)')
    .fill('Access was delayed.')
  await review.getByRole('button', { name: 'Review new date' }).click()
  await expect(review.getByText(original, { exact: true })).toBeVisible()
  await expect(review.getByText(today, { exact: true })).toBeVisible()
  await expect(review).toContainText('No current forecast is available')
  await review.getByRole('button', { name: 'Keep current date' }).click()
  await expect(task).toContainText(`Due ${original} · Overdue`)
  await missed.click()
  await review.getByLabel('Proposed date').fill(today)
  await review.getByRole('button', { name: 'Review new date' }).click()
  await review.getByRole('button', { name: 'Confirm new date' }).click()
  await expect(task).toContainText(`Due ${today}`)
  await expect(missed).toHaveCount(0)
  await page.getByRole('link', { name: 'Cultivation history' }).click()
  const history = page.getByRole('region', { name: 'Plan decisions' })
  await expect(history).toContainText(`Rejected · ${original} → ${today}`)
  await expect(history).toContainText(`Accepted · ${original} → ${today}`)
  await expect(history).toContainText('Access was delayed.')
  await fit(page)
})

test('farmer reviews suggested plans and accepts one addition', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic planner farmer')
  const cultivation = await taskCultivation(request, owner)
  const current = await request.post(root + cultivation + '/tasks', {
    headers: owner.headers,
    data: { title: 'Copy the field log', due_date: '2099-01-16' },
  })
  expect(current.ok()).toBe(true)
  await login(page, owner.email)
  await page.goto(cultivation)
  const tasks = page.getByRole('region', { name: 'Farm tasks' })
  const plans = tasks.getByRole('region', { name: 'Suggested plans' })
  const newTask = tasks
    .getByRole('article')
    .filter({ hasText: 'Check plot labels' })
  const review = plans.getByRole('button', { name: 'Review example plan' })

  await review.click()
  await expect(
    plans.getByRole('heading', { name: 'Check plot labels' }),
  ).toBeVisible()
  await expect(plans.getByText(/Sample recordkeeping checklist/)).toBeVisible()
  await expect(
    tasks.getByRole('heading', { name: 'Copy the field log' }),
  ).toBeVisible()
  await expect(newTask).toHaveCount(0)
  await fit(page)
  await plans.getByRole('button', { name: 'Reject suggestion' }).click()
  await expect(plans.getByText('Rejected', { exact: true })).toBeVisible()
  await expect(newTask).toHaveCount(0)

  await review.click()
  const accept = plans.getByRole('button', { name: 'Accept and add task' })
  await expect(accept).toBeVisible()
  const due = await plans.locator('time').innerText()
  await accept.click()
  await expect(
    plans.getByText('Accepted · Task added', { exact: true }),
  ).toBeVisible()
  await expect(newTask.getByText(`Due ${due}`)).toBeVisible()
  await page.reload()
  await expect(newTask).toHaveCount(1)
  await expect(
    plans.getByText('Accepted · Task added', { exact: true }),
  ).toBeVisible()
  await page.getByRole('link', { name: 'Cultivation history' }).click()
  const decisions = page.getByRole('region', { name: 'Plan decisions' })
  await expect(
    decisions.getByText(`Accepted · Task added · Due ${due}`),
  ).toBeVisible()
  await expect(decisions.getByText(/Rejected · Due/)).toBeVisible()
  await fit(page)
})

test('farmer reviews a matching task from the demo weather sample', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic weather farmer')
  const cultivation = await taskCultivation(request, owner)
  const unrelated = await request.post(root + cultivation + '/tasks', {
    headers: owner.headers,
    data: { title: 'File the field log', due_date: '2099-01-16' },
  })
  expect(unrelated.ok()).toBe(true)
  await login(page, owner.email)
  await page.goto(cultivation)
  const tasks = page.getByRole('region', { name: 'Farm tasks' })
  await tasks.getByRole('button', { name: 'Show demo weather' }).click()
  const weather = tasks.getByRole('region', { name: 'Demo weather' })
  await expect(
    weather.getByText(/Simulated forecast for Synthetic village/),
  ).toBeVisible()
  await expect(weather.getByText(/18 mm sample rainfall/)).toBeVisible()
  const due = await weather.locator('time').innerText()
  await expect(
    tasks
      .getByRole('article')
      .filter({ hasText: 'File the field log' })
      .getByRole('button', { name: 'Edit task' }),
  ).toBeVisible()

  const plans = tasks.getByRole('region', { name: 'Suggested plans' })
  await plans.getByRole('button', { name: 'Review example plan' }).click()
  await expect(plans.locator('time')).toHaveText(due)
  await plans.getByRole('button', { name: 'Accept and add task' }).click()
  const matching = tasks
    .getByRole('article')
    .filter({ hasText: 'Check plot labels' })
  const reviewTask = matching.getByRole('button', { name: 'Review this task' })
  await expect(
    tasks.getByRole('button', { name: 'Review this task' }),
  ).toHaveCount(1)
  const dueDate = tasks.getByLabel('Due date', { exact: true })
  await reviewTask.click()
  await expect(dueDate).toHaveValue(due)
  await expect(dueDate).toBeFocused()
  await tasks.getByRole('button', { name: 'Keep task date' }).click()
  await expect(matching.getByText(`Due ${due}`)).toBeVisible()
  const historyAfterKeep = await request.get(
    root + cultivation + '/tasks/history',
    {
      headers: owner.headers,
    },
  )
  expect(historyAfterKeep.ok()).toBe(true)
  expect((await historyAfterKeep.json()).total).toBe(2)

  await reviewTask.click()
  const next = new Date(`${due}T12:00:00Z`)
  next.setUTCDate(next.getUTCDate() + 1)
  const newDate = next.toISOString().slice(0, 10)
  await dueDate.fill(newDate)
  await tasks.getByRole('button', { name: 'Save task' }).click()
  await expect(matching.getByText(`Due ${newDate}`)).toBeVisible()
  await expect(reviewTask).toHaveCount(0)
  await page.reload()
  await expect(matching.getByText(`Due ${newDate}`)).toBeVisible()
  await expect(reviewTask).toHaveCount(0)
  await fit(page)
})

test('farmer fetches a farm forecast and sees it alongside a pending task', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic forecast farmer')
  const cultivation = await taskCultivation(request, owner)
  const farmPath = cultivation.split('/cultivations/')[0]
  await login(page, owner.email)
  await page.goto(cultivation)
  const weather = page.getByRole('region', { name: 'Weather forecast' })
  await expect(
    weather.getByRole('link', { name: 'Open farm to add coordinates' }),
  ).toHaveAttribute('href', farmPath)
  await expect(
    weather.getByRole('button', { name: 'Fetch forecast' }),
  ).toHaveCount(0)

  const updated = await request.patch(root + farmPath, {
    headers: owner.headers,
    data: { latitude: '8.3114', longitude: '80.4037', expected_version: 1 },
  })
  expect(updated.ok()).toBe(true)
  await page.reload()
  await weather.getByRole('button', { name: 'Fetch forecast' }).click()
  await expect(
    weather.getByRole('link', { name: 'Weather data by Open-Meteo' }),
  ).toBeVisible()
  await expect(
    weather.getByText('Low 24 °C · High 31 °C').first(),
  ).toBeVisible()
  await expect(weather.getByText('8.5 mm precipitation')).toBeVisible()
  const firstDay = weather
    .getByRole('list', { name: 'Daily forecast' })
    .locator('time')
    .first()
  const due = await firstDay.innerText()
  const tasks = page.getByRole('region', { name: 'Farm tasks' })
  await tasks.getByRole('button', { name: 'Add task' }).click()
  await tasks.getByLabel('Task title').fill('Check the field log')
  await tasks.getByLabel('Due date').fill(due)
  await tasks.getByRole('button', { name: 'Save task' }).click()
  const matching = tasks
    .getByRole('article')
    .filter({ hasText: 'Check the field log' })
  await expect(
    matching.getByText(/Forecast for the due date · 8.5 mm/),
  ).toBeVisible()
  await expect(
    matching.getByRole('button', { name: 'Edit task' }),
  ).toBeVisible()
  await page.reload()
  await expect(
    weather.getByRole('button', { name: 'Refresh forecast' }),
  ).toBeVisible()
  await expect(matching.getByText(`Due ${due}`)).toBeVisible()
  await fit(page)
})

test('farmer sets a weather alert and confirms a reviewed task date', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic weather review farmer')
  const cultivation = await taskCultivation(request, owner)
  const farmPath = cultivation.split('/cultivations/')[0]
  const updated = await request.patch(root + farmPath, {
    headers: owner.headers,
    data: { latitude: '8.3114', longitude: '80.4037', expected_version: 1 },
  })
  expect(updated.ok()).toBe(true)
  await login(page, owner.email)
  await page.goto(cultivation)
  const tasks = page.getByRole('region', { name: 'Farm tasks' })
  const weather = tasks.getByRole('region', { name: 'Weather forecast' })
  await weather.getByRole('button', { name: 'Fetch forecast' }).click()
  const due = await weather
    .getByRole('list', { name: 'Daily forecast' })
    .locator('time')
    .first()
    .innerText()
  const alerts = tasks.getByRole('region', { name: 'Weather alerts' })
  await alerts.getByLabel('Rain alert threshold (mm)').fill('5')
  await alerts.getByRole('button', { name: 'Save threshold' }).click()
  await expect(alerts.getByText('Weather alert threshold saved.')).toBeVisible()

  await tasks.getByRole('button', { name: 'Add task' }).click()
  await tasks.getByLabel('Task title').fill('Synthetic rain task')
  await tasks.getByLabel('Due date', { exact: true }).fill(due)
  await tasks.getByRole('button', { name: 'Save task' }).click()
  const alert = alerts
    .getByRole('article')
    .filter({ hasText: 'Synthetic rain task' })
  await expect(alert).toHaveCount(1)
  await expect(alert).toContainText('8.5 mm forecast')
  await weather.getByRole('button', { name: 'Refresh forecast' }).click()
  await expect(
    weather.getByRole('button', { name: 'Refresh forecast' }),
  ).toBeEnabled()
  await expect(alert).toHaveCount(1)

  await alert.getByRole('button', { name: 'Review task date' }).click()
  const review = alerts.getByRole('region', { name: 'Review task date change' })
  const next = new Date(`${due}T12:00:00Z`)
  next.setUTCDate(next.getUTCDate() + 1)
  const replacement = next.toISOString().slice(0, 10)
  await review.getByLabel('Proposed date').fill(replacement)
  await review.getByRole('button', { name: 'Review new date' }).click()
  await expect(review.getByText(due, { exact: true })).toBeVisible()
  await expect(review.getByText(replacement, { exact: true })).toBeVisible()
  const task = tasks.getByRole('article').filter({
    has: page.getByRole('heading', { name: 'Synthetic rain task', level: 3 }),
  })
  await expect(task.getByText(`Due ${due}`, { exact: true })).toBeVisible()
  await review.getByRole('button', { name: 'Confirm new date' }).click()
  await expect(
    task.getByText(`Due ${replacement}`, { exact: true }),
  ).toBeVisible()
  await expect(alert).toHaveCount(0)
  await page.reload()
  await expect(
    task.getByText(`Due ${replacement}`, { exact: true }),
  ).toBeVisible()
  await weather
    .getByRole('button', { name: 'Turn on automatic alerts' })
    .click()
  await expect(weather.getByText('On for this farm')).toBeVisible()
  await page.reload()
  await expect(weather.getByText('On for this farm')).toBeVisible()
  await weather
    .getByRole('button', { name: 'Turn off automatic alerts' })
    .click()
  await expect(weather.getByText('Off for this farm')).toBeVisible()
  await page.getByRole('link', { name: 'Cultivation history' }).click()
  await expect(
    page.getByRole('region', { name: 'Plan decisions' }),
  ).toContainText(`Accepted · ${due} → ${replacement}`)
  await fit(page)
})

async function rainyWeek(
  request: APIRequestContext,
  owner: Awaited<ReturnType<typeof actor>>,
  cultivation: string,
) {
  const farmPath = cultivation.split('/cultivations/')[0]
  const updated = await request.patch(root + farmPath, {
    headers: owner.headers,
    data: { latitude: '8.31', longitude: '80.40', expected_version: 1 },
  })
  expect(updated.ok()).toBe(true)
  const rule = await request.patch(
    root + cultivation + '/weather/alerts/rule',
    {
      headers: owner.headers,
      data: { expected_version: 0, threshold_mm: 5 },
    },
  )
  expect(rule.ok()).toBe(true)
  const forecast = await request.post(root + cultivation + '/weather/refresh', {
    headers: owner.headers,
    data: {},
  })
  expect(forecast.ok()).toBe(true)
  return (await forecast.json()).forecast.days as Array<{ date: string }>
}

async function openPlanNotice(page: Page, title: string) {
  await page.goto('/notifications', { waitUntil: 'domcontentloaded' })
  const item = page
    .getByRole('listitem')
    .filter({ has: page.getByRole('heading', { name: title, exact: true }) })
  await item.getByRole('link', { name: 'Open plan review' }).click()
  await expect(page).toHaveURL(/\/plan-reviews\/[a-f0-9-]+$/)
}

test('farmer revises an advisor suggestion from notices and confirms the cleared date', async ({
  page,
  request,
  browser,
}) => {
  const owner = await actor(request, 'Synthetic weekly planner farmer')
  const advisor = await actor(request, 'Synthetic assigned advisor')
  const admin = await request.post(root + '/auth/login', {
    headers,
    data: { email: adminEmail, password },
  })
  expect(admin.ok()).toBe(true)
  const promoted = await request.patch(
    root + `/admin/users/${advisor.user.id}/role`,
    {
      headers: {
        ...headers,
        Authorization: `Bearer ${(await admin.json()).access_token}`,
      },
      data: {
        role: 'advisor',
        expected_version: advisor.user.version,
        reason: 'Synthetic advisor case test',
      },
    },
  )
  expect(promoted.ok()).toBe(true)
  const cultivation = await taskCultivation(request, owner)
  const days = await rainyWeek(request, owner, cultivation)
  const name = 'Synthetic weekly field check'
  const task = await request.post(root + cultivation + '/tasks', {
    headers: owner.headers,
    data: { title: name, due_date: days[0].date },
  })
  expect(task.ok()).toBe(true)
  await login(page, owner.email)
  await page.goto(cultivation)
  const planner = page.getByRole('region', { name: 'Seven-day planner' })
  const day = planner.getByRole('region', { name: `Tasks for ${days[0].date}` })
  await expect(day).toContainText('Rain alert (8.5 mm)')
  await day.getByRole('button', { name: `Open task ${name}` }).click()
  await expect(
    page.getByRole('button', { name: 'Back to task list' }),
  ).toBeVisible()
  await day.getByRole('button', { name: 'Review suggestion' }).click()
  const suggestion = planner.getByRole('region', {
    name: 'Weekly date suggestion',
  })
  await suggestion.getByRole('button', { name: 'Suggest a date' }).click()
  await expect(
    suggestion.getByRole('button', { name: 'Confirm new date' }),
  ).toBeDisabled()
  await expect(
    suggestion.getByText(days[1].date, { exact: true }),
  ).toBeVisible()
  await suggestion.getByRole('button', { name: 'Ask an advisor' }).click()
  await suggestion.getByLabel('Advisor account email').fill(advisor.email)
  await suggestion.getByRole('button', { name: 'Send for review' }).click()
  await expect(suggestion).toContainText('Waiting for your assigned advisor')
  const advisorPage = await browser.newPage({
    baseURL: webOrigin,
    viewport: page.viewportSize() ?? undefined,
  })
  try {
    await advisorPage.goto('/login')
    await advisorPage.getByLabel('Email address').fill(advisor.email)
    await advisorPage.getByLabel('Password', { exact: true }).fill(password)
    await advisorPage.getByRole('button', { name: 'Sign in' }).click()
    await expect(advisorPage).toHaveURL('/account')
    await openPlanNotice(advisorPage, 'Plan review assigned')
    const assigned = advisorPage.getByRole('article', {
      name: `Advisor review for ${name}`,
    })
    await assigned
      .getByLabel('Review reason')
      .fill('Consider the following dry day.')
    await assigned.getByRole('button', { name: 'Request changes' }).click()
    await expect(assigned).toContainText('Changes requested')

    await openPlanNotice(page, 'Advisor requested changes')
    const returned = page.getByRole('region', {
      name: 'Weekly date suggestion',
    })
    await expect(returned).toContainText('Consider the following dry day.')
    await returned
      .getByRole('button', { name: 'Revise suggested date' })
      .click()
    await returned.getByLabel('Revised date').fill(days[2].date)
    await returned
      .getByRole('button', { name: 'Send revised suggestion' })
      .click()
    await expect(returned).toContainText(
      `Previous suggestion · ${days[1].date}`,
    )
    await expect(
      returned.getByRole('button', { name: 'Confirm new date' }),
    ).toBeDisabled()

    await openPlanNotice(advisorPage, 'Revised plan assigned')
    await expect(assigned).toContainText(
      `Previous suggestion · ${days[1].date}`,
    )
    await assigned
      .getByLabel('Review reason')
      .fill('The revised date works for this synthetic task.')
    await assigned.getByRole('button', { name: 'Clear suggestion' }).click()
    await expect(assigned.getByText('Cleared', { exact: true })).toBeVisible()
  } finally {
    await advisorPage.close()
  }
  await openPlanNotice(page, 'Plan cleared by advisor')
  const cleared = page.getByRole('region', { name: 'Weekly date suggestion' })
  await expect(
    cleared.getByRole('button', { name: 'Confirm new date' }),
  ).toBeEnabled()
  await cleared.getByRole('button', { name: 'Confirm new date' }).click()
  await expect(cleared).toContainText('Task date updated.')
  await page.getByRole('link', { name: 'Open cultivation' }).click()
  await expect(page).toHaveURL(cultivation)
  await expect(
    planner.getByRole('region', { name: `Tasks for ${days[2].date}` }),
  ).toContainText(name)
  await page.getByRole('link', { name: 'Cultivation history' }).click()
  const diary = page.getByRole('region', { name: 'Cultivation diary' })
  await expect(diary).toContainText('Task date changed from a plan')
  await expect(diary).toContainText(name)
  await expect(diary).toContainText(`${days[0].date} → ${days[2].date}`)
  await expect(
    page.getByRole('region', { name: 'Weekly suggestion history' }),
  ).toContainText('Consider the following dry day.')
  await expect(
    page.getByRole('region', { name: 'Plan decisions' }),
  ).toContainText('The revised date works for this synthetic task.')
  await fit(page)
})

test('farmer accepts selected tasks together in a weekly plan', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic weekly batch farmer')
  const cultivation = await taskCultivation(request, owner)
  const days = await rainyWeek(request, owner, cultivation)
  const stage = await request.post(root + cultivation + '/stage-confirmation', {
    headers: owner.headers,
    data: { expected_version: 1, stage: 'Seedling' },
  })
  expect(stage.ok()).toBe(true)
  for (const title of [
    'Synthetic task one',
    'Synthetic task two',
    'Synthetic task three',
  ]) {
    expect(
      (
        await request.post(root + cultivation + '/tasks', {
          headers: owner.headers,
          data: { title, due_date: days[0].date },
        })
      ).ok(),
    ).toBe(true)
  }
  await login(page, owner.email)
  await page.goto(cultivation)
  const planner = page.getByRole('region', { name: 'Seven-day planner' })
  await planner.getByRole('button', { name: 'Review weekly changes' }).click()
  const batch = planner.getByRole('region', { name: 'Review weekly changes' })
  await batch
    .getByRole('button', { name: 'Prepare weekly suggestions' })
    .click()
  await batch.getByLabel('Select change for Synthetic task one').check()
  await batch.getByLabel('Select change for Synthetic task two').check()
  await batch
    .getByRole('button', { name: 'Accept selected changes (2)' })
    .click()
  const saved = batch.getByRole('region', { name: 'Saved weekly changes' })
  await expect(saved).toContainText('Synthetic task one')
  await expect(saved).toContainText('Synthetic task two')
  await expect(saved).not.toContainText('Synthetic task three')
  await expect(
    planner.getByRole('region', { name: `Tasks for ${days[0].date}` }),
  ).toContainText('Synthetic task three')
  await fit(page)
})

test('farmer reads cited cultivation guidance with a saved soil moisture observation', async ({
  page,
  request,
}) => {
  const owner = await actor(request, 'Synthetic chilli guidance farmer')
  const cultivation = await taskCultivation(request, owner)
  const farmPath = cultivation.split('/cultivations/')[0]
  expect(
    (
      await request.patch(root + farmPath, {
        headers: owner.headers,
        data: {
          location: 'Synthetic village, Anuradhapura District, Sri Lanka',
          expected_version: 1,
        },
      })
    ).ok(),
  ).toBe(true)
  expect(
    (
      await request.post(root + cultivation + '/stage-confirmation', {
        headers: owner.headers,
        data: { stage: 'Seedling', expected_version: 1 },
      })
    ).ok(),
  ).toBe(true)
  await login(page, owner.email)
  await page.goto(cultivation)
  const guidance = page.getByRole('region', { name: 'Chilli growing help' })
  const check = guidance.getByRole('button', { name: 'Check guidance' })
  const answer = guidance.getByRole('article', {
    name: 'Cultivation guidance answer',
  })
  await check.click()
  await expect(answer).toContainText(
    'Record a recent soil moisture observation',
  )
  const observations = page.getByRole('region', { name: 'Observations' })
  await observations.getByRole('button', { name: 'Add observation' }).click()
  await observations.getByRole('button', { name: 'Use current time' }).click()
  await observations
    .getByLabel('Observation notes')
    .fill('Synthetic field reading')
  await observations.getByLabel('Soil moisture (optional)').selectOption('dry')
  await observations.getByRole('button', { name: 'Record observation' }).click()
  await expect(observations.getByText('Soil moisture: dry')).toBeVisible()
  await expect(answer).toHaveCount(0)
  await check.click()
  await expect(answer).toContainText('Recorded crop stage: Seedling')
  await expect(answer).toContainText('Recorded soil moisture: dry')
  await expect(
    answer.getByRole('link', {
      name: /Department of Agriculture · Irrigation/,
    }),
  ).toHaveAttribute('href', 'https://doa.gov.lk/field-crops-chilli-si/')
  await fit(page)
})

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
  await expect(
    page.getByRole('heading', { name: 'Make yourself at home.' }),
  ).toBeVisible()
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
