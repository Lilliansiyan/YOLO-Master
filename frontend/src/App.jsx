import { useState } from 'react'
import TaskSubmit from './components/TaskSubmit.jsx'
import TaskList from './components/TaskList.jsx'
import TaskDetail from './components/TaskDetail.jsx'
import './index.css'

export default function App() {
  const [selectedJobId, setSelectedJobId] = useState(null)
  const [refreshSignal, setRefreshSignal] = useState(0)

  function handleSubmitted(response) {
    setSelectedJobId(response.job_id)
    setRefreshSignal((n) => n + 1)
  }

  return (
    <div className="app">
      <header>
        <h1>F1 Studio</h1>
        <p className="subtitle">YOLO training / inference / export — FastAPI backend</p>
      </header>

      <main>
        <TaskSubmit onSubmitted={handleSubmitted} />
        <TaskList
          refreshSignal={refreshSignal}
          selectedJobId={selectedJobId}
          onSelectJob={setSelectedJobId}
        />
        <TaskDetail jobId={selectedJobId} />
      </main>
    </div>
  )
}
