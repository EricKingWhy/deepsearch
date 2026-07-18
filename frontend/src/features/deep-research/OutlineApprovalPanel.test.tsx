import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OutlineApprovalPanel } from './OutlineApprovalPanel'
import { loadOutlineDraft, saveOutlineDraft } from './outline-draft'
import type { EditableResearchPlan } from './types'

function makePlan(): EditableResearchPlan {
  return {
    sections: [1, 2, 3].map((index) => ({
      id: `section-${index}`,
      title: `Chapter ${index}`,
      description: `Description ${index}`,
      section_type: 'mixed',
      requires_data: false,
      requires_chart: false,
    })),
    researchQuestions: [1, 2, 3].map((index) => ({
      id: `question-${index}`,
      text: `Question ${index}`,
    })),
  }
}

function renderPanel(overrides: Partial<React.ComponentProps<typeof OutlineApprovalPanel>> = {}) {
  const plan = makePlan()
  const props = {
    sessionId: 'session-1',
    outlineRevision: 'revision-1',
    initialSections: plan.sections,
    initialResearchQuestions: plan.researchQuestions,
    approving: false,
    onApprove: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
  return { ...render(<OutlineApprovalPanel {...props} />), props }
}

describe('OutlineApprovalPanel', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useRealTimers()
  })

  it('restores the matching revision draft and ignores another revision', () => {
    const draft = makePlan()
    draft.sections[0].title = 'Restored chapter'
    saveOutlineDraft('session-1', 'revision-1', draft)

    const { unmount } = renderPanel()
    expect(screen.getByDisplayValue('Restored chapter')).toBeInTheDocument()
    unmount()

    renderPanel({ outlineRevision: 'revision-2' })
    expect(screen.getByDisplayValue('Chapter 1')).toBeInTheDocument()
  })

  it('edits, adds, deletes, and reorders chapters and questions', async () => {
    const user = userEvent.setup()
    renderPanel()

    const firstTitle = screen.getByLabelText('Chapter 1 title')
    await user.clear(firstTitle)
    await user.type(firstTitle, 'Market overview')
    await user.click(screen.getByRole('button', { name: 'Move chapter 1 down' }))
    expect(screen.getAllByLabelText(/Chapter \d+ title/)[1]).toHaveValue(
      'Market overview',
    )

    await user.click(screen.getByRole('button', { name: 'Add chapter' }))
    expect(screen.getAllByLabelText(/Chapter \d+ title/)).toHaveLength(4)
    await user.click(screen.getByRole('button', { name: 'Delete chapter 4' }))
    expect(screen.getAllByLabelText(/Chapter \d+ title/)).toHaveLength(3)

    await user.click(screen.getByRole('button', { name: 'Add question' }))
    expect(screen.getAllByLabelText(/Research question \d+/)).toHaveLength(4)
    await user.click(screen.getByRole('button', { name: 'Delete question 4' }))
    expect(screen.getAllByLabelText(/Research question \d+/)).toHaveLength(3)
  })

  it('debounces draft writes by 800ms', () => {
    vi.useFakeTimers()
    renderPanel()

    fireEvent.change(screen.getByLabelText('Chapter 1 title'), {
      target: { value: 'Updated title' },
    })
    expect(loadOutlineDraft('session-1', 'revision-1')).toBeNull()

    act(() => vi.advanceTimersByTime(799))
    expect(loadOutlineDraft('session-1', 'revision-1')).toBeNull()
    act(() => vi.advanceTimersByTime(1))
    expect(loadOutlineDraft('session-1', 'revision-1')?.sections[0].title).toBe(
      'Updated title',
    )
  })

  it('blocks invalid plans and clears the draft after approval', async () => {
    const user = userEvent.setup()
    const { props } = renderPanel()
    saveOutlineDraft('session-1', 'revision-1', makePlan())

    const firstTitle = screen.getByLabelText('Chapter 1 title')
    await user.clear(firstTitle)
    expect(screen.getByRole('button', { name: 'Approve and start research' })).toBeDisabled()
    expect(screen.getByText('Chapter titles and descriptions cannot be blank')).toBeInTheDocument()

    await user.type(firstTitle, 'Valid title')
    await user.click(screen.getByRole('button', { name: 'Approve and start research' }))
    await waitFor(() => expect(props.onApprove).toHaveBeenCalledOnce())
    expect(loadOutlineDraft('session-1', 'revision-1')).toBeNull()
  })

  it('shows API errors and disables controls while approving', () => {
    renderPanel({ approving: true, error: 'Outline revision is stale' })

    expect(screen.getByText('Outline revision is stale')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approving outline' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add chapter' })).toBeDisabled()
  })

  it('enforces the maximum of twelve chapters and questions', () => {
    const plan = makePlan()
    plan.sections = Array.from({ length: 12 }, (_, index) => ({
      ...plan.sections[0],
      id: `section-${index + 1}`,
      title: `Chapter ${index + 1}`,
    }))
    plan.researchQuestions = Array.from({ length: 12 }, (_, index) => ({
      id: `question-${index + 1}`,
      text: `Question ${index + 1}`,
    }))

    renderPanel({
      initialSections: plan.sections,
      initialResearchQuestions: plan.researchQuestions,
    })

    expect(screen.getByRole('button', { name: 'Add chapter' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add question' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Delete chapter 1' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Delete question 1' })).toBeEnabled()
  })
})
