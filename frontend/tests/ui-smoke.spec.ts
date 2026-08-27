import { expect, test } from '@playwright/test'

test('registers, signs in, and adds a company', async ({ page }) => {
  const suffix = String(Date.now()).slice(-8)
  const username = `analyst${suffix}`
  const ticker = `T${suffix.slice(-5)}`

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Fintel' })).toBeVisible()
  await expect(page.getByText('Ready')).toBeVisible({
    timeout: 15000,
  })

  await page.getByRole('button', { name: 'Register' }).click()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Email').fill(`${username}@example.com`)
  await page.getByLabel('Password').fill('ChangeMe123!')
  await page.getByRole('button', { name: 'Create user' }).click()

  await page.getByRole('button', { name: 'Login' }).click()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill('ChangeMe123!')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByRole('heading', { name: 'Ask filings questions' })).toBeVisible()

  await page.getByLabel('Ticker').fill(ticker)
  await page.getByLabel('CIK').fill(suffix.padStart(10, '0'))
  await page.getByLabel('Company name').fill(`Test Company ${suffix}`)
  await page.getByRole('button', { name: 'Add company' }).click()

  await expect(page.getByText(`${ticker} added to your filing corpus.`)).toBeVisible()
  await expect(page.locator('.compact-row').filter({ hasText: `Test Company ${suffix}` })).toBeVisible()
})
