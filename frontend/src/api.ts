import { formatDetail } from './errors.ts'

export type QueryResponse = {
    sql: string
    columns: string[]
    rows: unknown[][]
    attempts: number
    explanation: string | null
}

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export async function askQuestion(question: string): Promise<QueryResponse> {
    const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({question}),
    })

    if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(formatDetail(body?.detail))
    }

    return response.json()
}
