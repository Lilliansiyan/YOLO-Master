# F1 Studio - YOLO-Master Task Management Interface

F1 Studio provides a Gradio-based web interface for managing YOLO-Master agent tasks including training, prediction, and export operations.

## Features

- **Task Submission**: Submit train/predict/export tasks through an intuitive web interface
- **Task History**: Track all submitted tasks with status and timestamps
- **Artifact Management**: View and access task outputs (weights, logs, results)
- **Environment Check**: Verify system configuration and dependencies
- **Path Security**: Whitelist-based path validation to prevent unauthorized file access

## Quick Start

```bash
# Start the F1 Studio interface
python3 app.py
```

The interface will open in your browser at `http://127.0.0.1:7860`

## Usage

### Task Management Tab

1. **Submit Tasks**:
   - **Train**: Specify model, dataset, epochs, and image size
   - **Predict**: Specify model and source images/videos
   - **Export**: Specify model and export format (ONNX, TorchScript, etc.)

2. **View Task History**:
   - All submitted tasks are tracked in an SQLite database
   - Click "🔄 Refresh History" to update the task list
   - View task status: `ok`, `failed`, or `timeout`

3. **View Artifacts**:
   - Enter a Job ID and click "👁️ View Artifacts" to see output files
   - Artifacts are categorized as: weights, results, exports, or logs
   - Full file paths are provided for easy access

4. **Environment Check**:
   - Click "🩺 Environment Check" to verify YOLO CLI availability
   - Shows device information, CLI version, and system configuration

## Architecture

### Components

- `app.py`: Main Gradio interface with inference and task management tabs
- `f1_studio_db.py`: SQLite database layer for task persistence
- `f1_studio_tasks.py`: Task submission and dispatcher interface
- `f1_studio.db`: SQLite database (created on first run)

### Task Flow

```
User Input → Gradio UI → f1_studio_tasks.py → Dispatcher → YOLO-Master Agent
                                ↓
                         f1_studio_db.py (persist)
                                ↓
                         Task History Display
```

### Security

- **Path Whitelist**: Only paths starting with `models/`, `datasets/`, `runs/`, `ckpts/`, `yolo`, or `coco` are allowed
- **Path Traversal Protection**: `..` and absolute paths are blocked
- **Timeout Protection**: Tasks timeout after 10 minutes

## Database Schema

```sql
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    skill TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    finished_at TEXT,
    response_json TEXT,
    artifacts_json TEXT,
    error_message TEXT
);
```

## Example: Submit a Training Task

```python
# Via UI (recommended):
# 1. Go to "Task Management" tab
# 2. Select "Train" sub-tab
# 3. Fill in:
#    - Model: yolo11n.pt
#    - Data: coco8.yaml
#    - Epochs: 1
#    - Image Size: 32
# 4. Click "▶️ Submit Train Task"

# Via Python API:
from f1_studio_tasks import submit_train

response = submit_train(
    model="yolo11n.pt",
    data="coco8.yaml",
    epochs=1,
    imgsz=32
)
print(f"Job ID: {response['job_id']}")
print(f"Status: {response['status']}")
```

## Troubleshooting

### Common Errors

**Path Violation**
```
Path violation: ../etc/passwd (contains '..' or absolute path)
```
Solution: Use relative paths within allowed directories

**Task Timeout**
```
Task execution exceeded 10 minute timeout
```
Solution: Reduce training epochs or dataset size for P0 testing

**Dispatcher Not Found**
```
No such file or directory: agent/scripts/run_yolo_master_skill.py
```
Solution: Ensure you're running from the YOLO-Master repository root

## Development Status

- ✅ P0 Day 1: Basic task submission and history (implemented)
- 🚧 P0 Day 2: Enhanced artifact management (in progress)
- ⏳ P0 Day 3: Error handling and polish (planned)

## Known Limitations (P0)

- Tasks run synchronously (no background queue)
- No real-time progress indicators
- No task cancellation support
- Limited to single-user operation

These are planned for P1/P2 iterations.
