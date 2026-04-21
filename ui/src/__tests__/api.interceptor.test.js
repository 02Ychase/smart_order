import { describe, expect, test, vi } from 'vitest'

const { mockApi } = vi.hoisted(() => ({
  mockApi: {
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn(),
      },
    },
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockApi),
  },
}))

await import('../api/index')

const [, responseErrorHandler] = mockApi.interceptors.response.use.mock.calls[0]

describe('api interceptor', () => {
  test('throws an Error with detail message and response metadata', () => {
    const rejection = {
      response: {
        status: 422,
        data: {
          detail: '商家不存在',
          reason: 'missing_merchant',
        },
      },
    }

    let thrownError

    try {
      responseErrorHandler(rejection)
    } catch (error) {
      thrownError = error
    }

    expect(thrownError).toBeInstanceOf(Error)
    expect(thrownError.message).toBe('商家不存在')
    expect(thrownError.status).toBe(422)
    expect(thrownError.data).toEqual(rejection.response.data)
    expect(thrownError.payload).toEqual(rejection.response.data)
  })
})
