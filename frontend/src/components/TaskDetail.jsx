import { useEffect, useState } from 'react'
import { api } from '../api.js'

const POLL_MS = 5000

function formatBytes(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function TaskDetail({ jobId }) {
  const [job, setJob] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!jobId) return

    let cancelled = false
    setMetrics(null)

    async function load() {
      try {
        const data = await api.getTask(jobId)
        if (cancelled) return
        setJob(data)
        setError(null)

        // Metrics only exist for finished yolo.train jobs; a 404 here just
        // means "not applicable yet", not a real error.
        if (data.skill === 'yolo.train' && data.status === 'ok') {
          try {
            const m = await api.getMetrics(jobId)
            if (!cancelled) setMetrics(m)
          } catch (err) {
            if (!cancelled && err.status !== 404) throw err
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    }

    load()
    const id = setInterval(load, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [jobId])

  if (!jobId) {
    return (
      <section className="panel">
        <h2>Task Detail</h2>
        <p>Select a task from the list to see details.</p>
      </section>
    )
  }

  return (
    <section className="panel">
      <h2>Task Detail — <code>{jobId}</code></h2>

      {error && <p className="msg msg-error">Failed to load task: {error}</p>}
      {!job && !error && <p>Loading…</p>}

      {job && (
        <div className="detail">
          <dl>
            <dt>Skill</dt><dd>{job.skill}</dd>
            <dt>Status</dt><dd><span className={`status status-${job.status}`}>{job.status}</span></dd>
            <dt>Submitted</dt><dd>{job.submitted_at}</dd>
            <dt>Finished</dt><dd>{job.finished_at || '—'}</dd>
            {job.error_message && (
              <>
                <dt>Error</dt><dd className="msg-error">{job.error_message}</dd>
              </>
            )}
          </dl>

          <h3>Artifacts</h3>
          {(!job.artifacts || job.artifacts.length === 0) && <p>No artifacts.</p>}
          {job.artifacts && job.artifacts.length > 0 && (
            <table className="task-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {job.artifacts.map((a) => (
                  <tr key={a.rel_path}>
                    <td>{a.rel_path}</td>
                    <td>{a.category}</td>
                    <td>{formatBytes(a.size)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {metrics && (
            <>
              <h3>Metrics</h3>
              <dl>
                <dt>Epochs</dt><dd>{metrics.epochs}</dd>
                <dt>Image size</dt><dd>{metrics.imgsz}</dd>
                <dt>mAP50</dt><dd>{metrics['mAP50'].toFixed(3)}</dd>
                <dt>mAP50-95</dt><dd>{metrics['mAP50-95'].toFixed(3)}</dd>
                <dt>Precision</dt><dd>{metrics.precision.toFixed(3)}</dd>
                <dt>Recall</dt><dd>{metrics.recall.toFixed(3)}</dd>
                <dt>Box loss</dt><dd>{metrics.box_loss.toFixed(3)}</dd>
              </dl>
            </>
          )}

          <details>
            <summary>Raw response</summary>
            <pre>{JSON.stringify(job.response, null, 2)}</pre>
          </details>
        </div>
      )}
    </section>
  )
}
