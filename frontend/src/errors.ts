export function formatDetail(detail: unknown): string {
    if (typeof detail === 'string') return detail

    if (Array.isArray(detail)) {
        const msgs: string[] = []
        for (const item of detail) {
            if (typeof item?.msg === 'string') {
                msgs.push(item.msg)
            }
        }
        if (msgs.length > 0) return msgs.join('; ')
    }

    return 'Unexpected error'
}