// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

beforeEach(() => { localStorage.clear(); window.history.replaceState({}, '', '/portfolio') })
afterEach(() => cleanup())

describe('local portfolio journey', () => {
  it('searches holdings and navigates to exposure', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Your portfolio' })).toBeTruthy()
    await user.type(screen.getByRole('textbox', { name: 'Search holdings' }), 'semiconductor')
    expect(screen.getByText('1 of 7 positions · values are illustrative')).toBeTruthy()
    await user.click(screen.getByRole('link', { name: 'Exposure analysis' }))
    expect(await screen.findByRole('heading', { name: 'Exposure analysis' })).toBeTruthy()
  })
  it('validates and adds a local holding', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('heading', { name: 'Your portfolio' })
    await user.click(screen.getByRole('button', { name: 'Add holding' }))
    const dialog = screen.getByRole('dialog', { name: 'Add a holding' })
    await user.click(within(dialog).getByRole('button', { name: 'Add holding' }))
    expect(await within(dialog).findByText('Enter an asset name')).toBeTruthy()
    await user.type(within(dialog).getByRole('textbox', { name: /Asset name/ }), 'Example Test Asset')
    await user.type(within(dialog).getByRole('spinbutton', { name: /Market value/ }), '200')
    await user.click(within(dialog).getByRole('button', { name: 'Add holding' }))
    expect(await screen.findByText('8 of 8 positions · values are illustrative')).toBeTruthy()
    expect(screen.getAllByText('Example Test Asset').length).toBeGreaterThan(0)
  })
})
