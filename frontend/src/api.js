const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  let data = null
  try {
    data = await res.json()
  } catch {
    // no/invalid JSON body — leave data as null
  }

  if (!res.ok) {
    const message = (data && data.detail) || `Request failed (${res.status})`
    const err = new Error(message)
    err.status = res.status
    throw err
  }

  return data
}

export const api = {
  health: () => request('/health'),

  listTasks: (limit = 50, offset = 0) =>
    request(`/tasks?limit=${limit}&offset=${offset}`),

  getTask: (jobId) => request(`/tasks/${encodeURIComponent(jobId)}`),

  submitTrain: (body) =>
    request('/tasks/train', { method: 'POST', body: JSON.stringify(body) }),

  submitPredict: (body) =>
    request('/tasks/predict', { method: 'POST', body: JSON.stringify(body) }),

  submitExport: (body) =>
    request('/tasks/export', { method: 'POST', body: JSON.stringify(body) }),

  // Note: the DELETE endpoint returns 409 (job already finished) or 404
  // (job not found) — callers should catch and surface err.status.
  cancelTask: (jobId) =>
    request(`/tasks/${encodeURIComponent(jobId)}`, { method: 'DELETE' }),
}
