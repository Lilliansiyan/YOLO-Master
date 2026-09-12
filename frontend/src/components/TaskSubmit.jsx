import { useState } from 'react'
import { api } from '../api.js'

const DEFAULTS = {
  train: { model: 'yolo11n.pt', data: 'coco8.yaml', epochs: 3, imgsz: 640, timeout: 600 },
  predict: { model: 'yolo11n.pt', source: 'bus.jpg', conf: 0.25, timeout: 300 },
  export: { model: 'runs/detect/train/weights/best.pt', format: 'onnx', timeout: 300 },
}

const FIELDS = {
  train: [
    { name: 'model', label: 'Model', type: 'text' },
    { name: 'data', label: 'Data (yaml)', type: 'text' },
    { name: 'epochs', label: 'Epochs', type: 'number' },
    { name: 'imgsz', label: 'Image size', type: 'number' },
    { name: 'timeout', label: 'Timeout (s)', type: 'number' },
  ],
  predict: [
    { name: 'model', label: 'Model', type: 'text' },
    { name: 'source', label: 'Source (image/video/dir)', type: 'text' },
    { name: 'conf', label: 'Confidence', type: 'number', step: '0.01' },
    { name: 'timeout', label: 'Timeout (s)', type: 'number' },
  ],
  export: [
    { name: 'model', label: 'Model (.pt weights)', type: 'text' },
    { name: 'format', label: 'Format (onnx/torchscript/...)', type: 'text' },
    { name: 'timeout', label: 'Timeout (s)', type: 'number' },
  ],
}

const SUBMIT_FN = {
  train: api.submitTrain,
  predict: api.submitPredict,
  export: api.submitExport,
}

const NUMERIC_FIELDS = new Set(['epochs', 'imgsz', 'timeout', 'conf'])

export default function TaskSubmit({ onSubmitted }) {
  const [taskType, setTaskType] = useState('train')
  const [values, setValues] = useState(DEFAULTS.train)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  function handleTypeChange(nextType) {
    setTaskType(nextType)
    setValues(DEFAULTS[nextType])
    setResult(null)
    setError(null)
  }

  function handleFieldChange(name, raw) {
    const value = NUMERIC_FIELDS.has(name) ? Number(raw) : raw
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setResult(null)
    try {
      const response = await SUBMIT_FN[taskType](values)
      setResult(response)
      onSubmitted?.(response)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="panel">
      <h2>Submit Task</h2>
      <form onSubmit={handleSubmit}>
        <label className="field">
          <span>Task type</span>
          <select value={taskType} onChange={(e) => handleTypeChange(e.target.value)}>
            <option value="train">Train</option>
            <option value="predict">Predict</option>
            <option value="export">Export</option>
          </select>
        </label>

        {FIELDS[taskType].map((f) => (
          <label className="field" key={f.name}>
            <span>{f.label}</span>
            <input
              type={f.type}
              step={f.step}
              value={values[f.name] ?? ''}
              onChange={(e) => handleFieldChange(f.name, e.target.value)}
              required
            />
          </label>
        ))}

        <button type="submit" disabled={submitting}>
          {submitting ? 'Submitting…' : `Submit ${taskType}`}
        </button>
      </form>

      {result && (
        <p className="msg msg-ok">
          Submitted — job_id: <code>{result.job_id}</code> (status: {result.status})
        </p>
      )}
      {error && <p className="msg msg-error">Error: {error}</p>}
    </section>
  )
}
