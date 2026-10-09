import { useState } from 'react'
import type { FormEvent } from 'react'
import { askQuestion } from './api.ts'
import type { QueryResponse } from './api.ts'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: QueryResponse }

export default function App() {
  const [question, setQuestion] = useState('')
  const [state, setState] = useState<State>({ status: 'idle' })

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (question.trim() === '') return
    setState({ status: 'loading' })
    try {
      const data = await askQuestion(question)
      setState({ status: 'success', data })
    } catch (e) {
      const message =
        e instanceof TypeError
          ? 'Cannot reach the server.'
          : e instanceof Error
            ? e.message
            : 'Unexpected error'
      setState({ status: 'error', message })
    }
  }

  return (
    <main>
      <h1>nl2sql</h1>
      <form onSubmit={handleSubmit}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button type="submit" disabled={state.status === 'loading'}>
          Ask
        </button>
      </form>
      {state.status === 'loading' && <p>Thinking...</p>}
      {state.status === 'error' && <p role="alert">{state.message}</p>}
      {state.status === 'success' && (
        <section>
          <pre>{state.data.sql}</pre>
          <table>
            <thead>
              <tr>
                {state.data.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {state.data.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{cell === null ? '-' : String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p>Attempts: {state.data.attempts}</p>
        </section>
      )}
    </main>
  )
}
