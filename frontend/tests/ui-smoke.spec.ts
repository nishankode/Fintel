import { expect, test } from '@playwright/test'

test('registers, signs in, and adds a company', async ({ page }) => {
  const suffix = String(Date.now()).slice(-8)
  const username = `analyst${suffix}`
  const ticker = `T${suffix.slice(-5)}`

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Document Copilot' })).toBeVisible()

  await page.getByRole('button', { name: 'Register' }).click()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Email').fill(`${username}@example.com`)
  await page.getByLabel('Password').fill('ChangeMe123!')
  await page.getByRole('button', { name: 'Create user' }).click()
  await expect(page.getByLabel('Email')).toBeHidden()

  await page.getByRole('button', { name: 'Login' }).click()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill('ChangeMe123!')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.locator('.new-session-button')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Configure new session' })).toBeVisible()
  await expect(page.getByRole('button', { name: '10-K', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: String(new Date().getFullYear()) })).toBeVisible()

  await page.getByLabel('Ticker').fill(ticker)
  await page.getByLabel('CIK').fill(suffix.padStart(10, '0'))
  await page.getByLabel('Company name').fill(`Test Company ${suffix}`)
  await page.getByRole('button', { name: 'Add company' }).click()

  await expect(page.getByText(`${ticker} added to your filing corpus.`)).toBeVisible()
  await expect(page.getByRole('option', { name: `${ticker} - Test Company ${suffix}` })).toBeAttached()
  await expect(page.getByRole('button', { name: 'Chunk and embed filings' })).toBeVisible()
})

test('submits chat with enter and keeps composer anchored', async ({ page }) => {
  await page.route('**/health/ready', async (route) => {
    await route.fulfill({
      json: {
        status: 'ready',
        dependencies: [],
      },
    })
  })
  await page.route('**/companies', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 1,
          cik: '0000320193',
          ticker: 'AAPL',
          name: 'Apple Inc.',
        },
      ],
    })
  })
  await page.route('**/filings', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/query', async (route) => {
    await route.fulfill({
      json: {
        question: 'How did revenue change?',
        answer: 'Revenue shifted toward services.',
        evidence: [],
      },
    })
  })

  await page.addInitScript(() => {
    const session = {
      id: 'session-enter-test',
      title: 'Apple Inc. 2024, 2025',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
      config: {
        companyId: 1,
        companyTicker: 'AAPL',
        companyName: 'Apple Inc.',
        filingTypes: ['10-K'],
        filingYears: [2024, 2025],
        jobId: 1,
        status: 'completed',
      },
    }
    window.localStorage.setItem('fintel_access_token', 'test-token')
    window.localStorage.setItem('fintel_active_chat_session', session.id)
    window.localStorage.setItem('fintel_chat_sessions', JSON.stringify([session]))
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Apple Inc. 2024, 2025' })).toBeVisible()

  const composer = page.locator('.composer-wrap')
  const before = await composer.boundingBox()
  await page.getByPlaceholder('Ask about SEC filings...').fill('How did revenue change?')
  await page.getByPlaceholder('Ask about SEC filings...').press('Enter')

  await expect(page.getByText('How did revenue change?')).toBeVisible()
  await expect(page.getByText('Revenue shifted toward services.')).toBeVisible()
  const after = await composer.boundingBox()

  expect(before).not.toBeNull()
  expect(after).not.toBeNull()
  expect(Math.abs(after!.y - before!.y)).toBeLessThan(4)
})
