// @vitest-environment node
import { describe, expect, test, vi } from 'vitest'

const loadConfig = async () => {
  vi.resetModules()
  return import('../../vite.config.js')
}

describe('vite proxy config', () => {
  test('uses VITE_API_TARGET override for the api proxy target', async () => {
    vi.stubEnv('VITE_API_TARGET', 'http://127.0.0.1:8001')

    const { default: config } = await loadConfig()

    expect(config.server.proxy['/api'].target).toBe('http://127.0.0.1:8001')

    vi.unstubAllEnvs()
  })
})

