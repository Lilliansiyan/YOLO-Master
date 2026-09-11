import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

const POLL_MS = 5000
const PAGE_SIZE = 20

// Jobs stay "queued" in the DB for their entire in-flight lifetime — the
// background task only overwrites the row once it finishes (see api.py).
const IN_FLIGHT_STATUS = 'queued'

export default function TaskList({ refreshSignal, selectedJobId, onSelectJob }) {
  const [jobs, setJobs] = useState([])
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [cancelling, setCancelling] = useState(null)
  const [cancelError, setCancelError] = useState(null)

  const load = useCallback(async () => {
    try {
      const data = await api.listTasks(PAGE_SIZE, offset)
      setJobs(data.jobs)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [offset])

  useEffect(() => {
    setLoading(true)
    load()
    const id = setInterval(load, POLL_MS)
    return () => clearInterval(id)
  }, [load])

  // Refresh immediately after a new task is submitted, without waiting for
  // the next poll tick.
  useEffect(() => {
    if (refreshSignal) load()
  }, [refreshSignal, load])

  async function handleCancel(jobId) {
    setCancelling(jobId)
    setCancelError(null)
    try {
      await api.cancelTask(jobId)
      await load()
    } catch (err) {
      setCancelError(`${jobId}: ${err.message}`)
    } finally {
      setCancelling(null)
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Tasks</h2>
        <div className="pager">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            ← Prev
          </button>
          <span>offset {offset}</span>
          <button disabled={jobs.length < PAGE_SIZE} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Next →
          </button>
        </div>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p className="msg msg-error">Failed to load tasks: {error}</p>}
      {cancelError && <p className="msg msg-error">Cancel failed — {cancelError}</p>}

      {!loading && !error && (
        <table className="task-table">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Skill</th>
              <th>Status</th>
              <th>Submitted</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={5}>No tasks yet.</td>
              </tr>
            )}
            {jobs.map((job) => (
              <tr
                key={job.job_id}
                className={job.job_id === selectedJobId ? 'row-selected' : ''}
                onClick={() => onSelectJob(job.job_id)}
              >
                <td><code>{job.job_id}</code></td>
                <td>{job.skill}</td>
                <td>
                  <span className={`status status-${job.status}`}>{job.status}</span>
                </td>
                <td>{job.submitted_at}</td>
                <td onClick={(e) => e.stopPropagation()}>
                  {job.status === IN_FLIGHT_STATUS && (
                    <button
                      disabled={cancelling === job.job_id}
                      onClick={() => handleCancel(job.job_id)}
                    >
                      {cancelling === job.job_id ? 'Cancelling…' : 'Cancel'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
