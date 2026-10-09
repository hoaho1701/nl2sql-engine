import { describe, expect, it } from 'vitest'
import { formatDetail } from './errors.ts'

describe('formatDetail', () => {
    it('returns a string detail unchanged', () => {
        expect(formatDetail('boom')).toBe('boom')
    })

    it('joins the messages of a validation error list', () => {
        expect(formatDetail([{ msg: 'a'}, { msg: 'b'}])).toBe('a; b')
    })

    it('falls back for anything else', () => {
        expect(formatDetail(undefined)).toBe('Unexpected error')
        expect(formatDetail([])).toBe('Unexpected error')
        expect(formatDetail(42)).toBe('Unexpected error')
    })
})