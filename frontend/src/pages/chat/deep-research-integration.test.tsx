import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  deepsearch: vi.fn(),
  approveResearchOutline: vi.fn(),
  resumeResearch: vi.fn(),
  cancelResearch: vi.fn(),
  addMessage: vi.fn(),
  getSession: vi.fn(),
  getFullResearchCheckpoint: vi.fn(),
  getAttachment: vi.fn(),
  deleteAttachment: vi.fn(),
  uploadAttachment: vi.fn(),
  chat: vi.fn(),
  chatWithAttachments: vi.fn(),
}))

vi.mock('@/api', () => ({ session: apiMocks }))
vi.mock('@/utils', () => ({
  usePageTransport: () => ({ data: { ctx: undefined }, dataReady: true }),
}))
vi.mock('@/store/device', () => ({
  deviceState: { searchModes: ['web'] },
  deviceActions: { setChatting: vi.fn() },
}))
vi.mock('@/store/session', () => ({
  sessionState: { currentSession: null },
}))
vi.mock('ahooks', () => ({ useUnmount: vi.fn() }))
vi.mock('@/components/page-layout', () => ({
  default: ({ children, sender, right }: {
    children: React.ReactNode
    sender: React.ReactNode
    right?: React.ReactNode
  }) => (
    <main>
      <section data-testid="chat-main">
        {children}
        {sender}
      </section>
      <aside data-testid="right-workspace">{right}</aside>
    </main>
  ),
}))
vi.mock('@/components/sender', () => ({
  default: ({ onSend }: { onSend: (value: string) => void }) => (
    <button onClick={() => onSend('Battery industry outlook')}>Start research</button>
  ),
}))
vi.mock('./component/chat-message', () => ({
  default: ({ list }: { list: Array<{ content?: string }> }) => (
    <div data-testid="chat-messages">
      {list.map((item, index) => (
        <div key={index}>{item.content}</div>
      ))}
    </div>
  ),
}))
vi.mock('./component/drawer', () => ({ default: () => null }))
vi.mock('./component/source', () => ({ default: () => null }))
vi.mock('./component/step-detail-panel', () => ({ default: () => null }))
vi.mock('./component/research-detail', () => ({ default: () => null }))

import ChatPage from './index'

function eventStream(events: unknown[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
      }
      controller.close()
    },
  })
}

function jsonStream(value: unknown): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(JSON.stringify(value)))
      controller.close()
    },
  })
}

function outlineEvent() {
  return {
    type: 'outline_pending_approval',
    session_id: 'session-1',
    outline_revision: 'revision-1',
    sections: [1, 2, 3].map((index) => ({
      id: `section-${index}`,
      title: `Chapter ${index}`,
      description: `Description ${index}`,
      section_type: 'mixed',
      requires_data: false,
      requires_chart: false,
    })),
    research_questions: [1, 2, 3].map((index) => ({
      id: `question-${index}`,
      text: `Question ${index}`,
    })),
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/chat/session-1']}>
      <Routes>
        <Route path="/chat/:id" element={<ChatPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('deep research outline approval integration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    apiMocks.getSession.mockResolvedValue({ data: { messages: [] } })
    apiMocks.getFullResearchCheckpoint.mockResolvedValue({
      data: { success: false },
    })
    apiMocks.addMessage.mockResolvedValue({ data: {} })
    apiMocks.deepsearch.mockResolvedValue({
      data: eventStream([outlineEvent()]),
    })
  })

  it('submits edited content once and consumes the approval stream', async () => {
    const user = userEvent.setup()
    apiMocks.approveResearchOutline.mockResolvedValue({
      data: eventStream([
        { type: 'phase', phase: 'planning', content: 'Generating queries' },
        { type: 'research_complete', final_report: 'Approved research report' },
      ]),
    })
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Start research' }))
    const firstTitle = await screen.findByLabelText('Chapter 1 title')
    expect(
      within(screen.getByTestId('right-workspace')).getByText(
        'Review the research outline',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByTestId('chat-main')).queryByText(
        'Review the research outline',
      ),
    ).not.toBeInTheDocument()
    await user.clear(firstTitle)
    await user.type(firstTitle, 'Edited market overview')
    const approveButton = screen.getByRole('button', {
      name: 'Approve and start research',
    })
    await user.dblClick(approveButton)

    await waitFor(() =>
      expect(apiMocks.approveResearchOutline).toHaveBeenCalledTimes(1),
    )
    expect(apiMocks.approveResearchOutline).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({
        outline_revision: 'revision-1',
        sections: expect.arrayContaining([
          expect.objectContaining({ title: 'Edited market overview' }),
        ]),
      }),
      expect.objectContaining({ errorToast: false }),
    )
    expect(await screen.findByText('Approved research report')).toBeInTheDocument()
    expect(screen.queryByText('Review the research outline')).not.toBeInTheDocument()
    expect(
      localStorage.getItem(
        'deep-research-outline-draft:session-1:revision-1',
      ),
    ).toBeNull()
  })

  it('keeps the edited panel and draft when approval returns 409', async () => {
    const user = userEvent.setup()
    apiMocks.approveResearchOutline.mockRejectedValue({
      response: { data: jsonStream({ detail: 'Outline revision is stale' }) },
    })
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Start research' }))
    const firstTitle = await screen.findByLabelText('Chapter 1 title')
    await user.clear(firstTitle)
    await user.type(firstTitle, 'Preserved edit')
    await user.click(
      screen.getByRole('button', { name: 'Approve and start research' }),
    )

    expect(await screen.findByText('Outline revision is stale')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Preserved edit')).toBeInTheDocument()
    await waitFor(
      () => {
        const raw = localStorage.getItem(
          'deep-research-outline-draft:session-1:revision-1',
        )
        expect(raw).toContain('Preserved edit')
      },
      { timeout: 1500 },
    )
  })

  it('uses the shared stream path when resuming a checkpoint', async () => {
    apiMocks.getFullResearchCheckpoint.mockResolvedValue({
      data: {
        success: true,
        checkpoint: {
          id: 'checkpoint-1',
          session_id: 'session-1',
          query: 'Battery industry outlook',
          phase: 'researching',
          status: 'running',
          final_report: null,
          state_json: { references: [], charts: [] },
          ui_state_json: {
            research_steps: [],
            search_results: [],
            charts: [],
            knowledge_graph: null,
            streaming_report: '',
          },
        },
      },
    })
    apiMocks.resumeResearch.mockResolvedValue({
      data: eventStream([
        { type: 'phase', phase: 'researching', content: 'Resumed' },
        { type: 'research_complete', final_report: 'Resumed research report' },
      ]),
    })

    renderPage()

    expect(await screen.findByText('Resumed research report')).toBeInTheDocument()
    expect(apiMocks.resumeResearch).toHaveBeenCalledWith('session-1')
    expect(apiMocks.deepsearch).not.toHaveBeenCalled()
  })
})
