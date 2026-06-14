import { describe, it, expect } from 'vitest'
import { formatUptime } from '../components/vm/VMTable'

describe('formatUptime', () => {
  it('returns an em dash for null/undefined (stopped or unknown)', () => {
    expect(formatUptime(null)).toBe('—')
    expect(formatUptime(undefined)).toBe('—')
  })

  it('formats seconds, minutes, hours, and days', () => {
    expect(formatUptime(45)).toBe('45s')
    expect(formatUptime(90)).toBe('1m')
    expect(formatUptime(3 * 3600 + 25 * 60)).toBe('3h 25m')
    expect(formatUptime(2 * 86400 + 5 * 3600)).toBe('2d 5h')
  })
})
