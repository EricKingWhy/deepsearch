import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('./request', () => ({ request: requestMocks }))

import { deepsearch, getFullResearchCheckpoint } from './session'

describe('deep research request configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('treats a missing optional checkpoint as a silent probe', () => {
    getFullResearchCheckpoint('session-1')

    expect(requestMocks.get).toHaveBeenCalledWith(
      '/research/checkpoint/session-1/full',
      { loading: false, errorToast: false },
    )
  })

  it('lets the chat page handle research startup failures', () => {
    deepsearch({ query: 'Huawei outlook', session_id: 'session-1' })

    expect(requestMocks.post).toHaveBeenCalledWith(
      '/research/stream',
      expect.any(Object),
      expect.objectContaining({ errorToast: false }),
    )
  })
})
