import os
import gc
import json
import warnings
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

import gradio as gr
import numpy as np
import pandas as pd
import cv2
import torch
from ultralytics import YOLO

# F1 Studio imports
from f1_studio_db import F1StudioDB
from f1_studio_tasks import (
    submit_train,
    submit_predict,
    submit_export,
    submit_system_check,
    validate_path
)
from f1_studio_queue import TaskQueue, ProgressMonitor

# Ignore unnecessary warnings
warnings.filterwarnings("ignore")


class GlobalConfig:
    """Global configuration parameters for easy modification."""
    # Default model files mapping
    DEFAULT_MODELS = {
        "detect": "yolov8n.pt",
        "seg": "yolov8n-seg.pt",
        "cls": "yolov8n-cls.pt",
        "pose": "yolov8n-pose.pt",
        "obb": "yolov8n-obb.pt"
    }
    # Allowed image formats
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    # UI Theme
    THEME = gr.themes.Soft(primary_hue="blue", neutral_hue="slate")


class ModelManager:
    """Handles model scanning, loading, and memory management."""
    def __init__(self, ckpts_root: Path):
        self.ckpts_root = ckpts_root
        self.current_model: Optional[YOLO] = None
        self.current_model_path: str = ""
        self.current_task: str = "detect"

    def scan_checkpoints(self) -> Dict[str, List[str]]:
        """
        Scans the checkpoint directory and categorizes models by task.
        """
        model_map = {k: [] for k in GlobalConfig.DEFAULT_MODELS.keys()}
        
        if not self.ckpts_root.exists():
            return model_map

        # Recursively find all .pt files
        for p in self.ckpts_root.rglob("*.pt"):
            if p.is_dir(): continue 
            
            path_str = str(p.absolute())
            filename = p.name.lower()
            parent = p.parent.name.lower()
            
            # Intelligent classification logic
            if "seg" in filename or "seg" in parent:
                model_map["seg"].append(path_str)
            elif "cls" in filename or "class" in filename or "cls" in parent:
                model_map["cls"].append(path_str)
            elif "pose" in filename or "pose" in parent:
                model_map["pose"].append(path_str)
            elif "obb" in filename or "obb" in parent:
                model_map["obb"].append(path_str)
            else:
                model_map["detect"].append(path_str) # Default to detect

        # Deduplicate and sort
        for k in model_map:
            model_map[k] = sorted(list(set(model_map[k])))
            
        return model_map

    def unload_model(self):
        """Force clear GPU memory."""
        if self.current_model is not None:
            del self.current_model
            self.current_model = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("INFO: Memory cleared.")

    def load_model(self, model_path: str, task: str) -> YOLO:
        """Load model with caching and memory management."""
        target_path = model_path
        if not target_path or not os.path.exists(target_path):
            target_path = GlobalConfig.DEFAULT_MODELS.get(task, "yolov8n.pt")
        else:
            # Support directory path, auto-resolve to weights file
            if os.path.isdir(target_path):
                candidates = [
                    os.path.join(target_path, "weights", "best.pt"),
                    os.path.join(target_path, "weights", "last.pt"),
                    os.path.join(target_path, "best.pt"),
                    os.path.join(target_path, "last.pt"),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        target_path = c
                        break

        if self.current_model is not None and self.current_model_path == target_path:
            return self.current_model

        self.unload_model()

        print(f"INFO: Loading model from {target_path}...")
        try:
            model = YOLO(target_path)
            self.current_model = model
            self.current_model_path = target_path
            self.current_task = task
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")

    def get_current_model_info(self):
        """Returns device info of the current loaded model."""
        try:
            if self.current_model:
                return str(next(self.current_model.model.parameters()).device)
        except Exception:
            pass
        return "unknown"


class YOLO_Master_WebUI:
    def __init__(self, ckpts_root: str):
        self.ckpts_root = Path(ckpts_root)
        self.model_manager = ModelManager(self.ckpts_root)
        self.model_map = self.model_manager.scan_checkpoints()
        self.db = F1StudioDB()  # Initialize F1 Studio database
        self.task_queue = TaskQueue(self.db, max_workers=2)  # P1: Async queue
        self.task_queue.start()

    def inference(self, 
                  task: str, 
                  image: np.ndarray, 
                  model_dropdown: str,
                  custom_model_path: str,
                  conf: float, 
                  iou: float, 
                  device: str, 
                  max_det: float, 
                  line_width: float, 
                  cpu: bool,
                  checkboxes: List[str]):
        """
        Core inference function.
        Returns: (Annotated Image, Results DataFrame, Summary Text)
        """
        if image is None:
            return None, None, "⚠️ Please upload an image first."

        # 1. Parameter Sanitization
        device_opt = "cpu" if cpu else (device if device else "")
        line_width_opt = int(line_width) if line_width > 0 else None
        max_det_opt = int(max_det)
        options = {k: True for k in checkboxes}
        
        # Optimization for segmentation task
        if task == "seg" and "retina_masks" not in options:
            options["retina_masks"] = True

        # 2. Model Loading
        # Prioritize custom path, then dropdown
        model_path = (custom_model_path or "").strip() or (model_dropdown or "").strip()
        try:
            model = self.model_manager.load_model(model_path, task)
        except Exception as e:
            return image, None, f"❌ Error loading model: {str(e)}"

        # 3. Execution
        try:
            # Gradio input is RGB, but Ultralytics expects BGR for numpy arrays
            # We convert to BGR to ensure correct inference and plotting colors
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            results = model(image_bgr, 
                            conf=conf, 
                            iou=iou, 
                            device=device_opt, 
                            max_det=max_det_opt, 
                            line_width=line_width_opt, 
                            **options)
        except Exception as e:
            return image, None, f"❌ Inference Error: {str(e)}"

        # 4. Result Parsing
        res = results[0]
        
        # 4.1 Image Processing
        res_img = res.plot() 
        res_img = cv2.cvtColor(res_img, cv2.COLOR_BGR2RGB) # Convert back to RGB
        
        # 4.2 Data Extraction (Build DataFrame)
        data_list = []
        if res.boxes:
            for box in res.boxes:
                try:
                    # Compatibility handling: box.cls might be tensor or float
                    cls_id = int(box.cls[0]) if box.cls.numel() > 0 else 0
                    cls_name = model.names[cls_id]
                    conf_val = float(box.conf[0]) if box.conf.numel() > 0 else 0.0
                    coords = box.xyxy[0].tolist()
                    
                    row = {
                        "Class ID": cls_id,
                        "Class Name": cls_name,
                        "Confidence": round(conf_val, 3),
                        "x1": round(coords[0], 1),
                        "y1": round(coords[1], 1),
                        "x2": round(coords[2], 1),
                        "y2": round(coords[3], 1)
                    }
                    data_list.append(row)
                except Exception:
                    pass
        
        df = pd.DataFrame(data_list)
        
        # 4.3 Summary Info
        speed = res.speed
        infer_time = speed.get('inference', 0.0)
        model_device = self.model_manager.get_current_model_info()
        
        summary = (
            f"### ✅ Inference Done\n"
            f"- **Model:** `{Path(self.model_manager.current_model_path).name}`\n"
            f"- **Time:** `{infer_time:.1f}ms`\n"
            f"- **Objects:** {len(data_list)}\n"
            f"- **Device:** `{model_device}`"
        )
        
        return res_img, df, summary

    def describe_model(self, task: str, model_path: str) -> str:
        """Validate and describe the model."""
        if not model_path or not model_path.strip():
            return "⚠️ Please enter a model path."
        
        path = Path(model_path.strip())
        if not path.exists():
            return f"❌ Path does not exist: `{model_path}`"
            
        try:
            # Check if it's a directory, try to find pt file
            if path.is_dir():
                candidates = [
                    path / "weights" / "best.pt",
                    path / "weights" / "last.pt",
                    path / "best.pt",
                    path / "last.pt",
                ]
                found = False
                for c in candidates:
                    if c.exists():
                        path = c
                        found = True
                        break
                if not found:
                    return f"❌ No model file (.pt) found in directory: `{model_path}`"
            
            # Load model to get info (temporary load, no caching here to avoid polluting main state)
            model = YOLO(str(path))
            names = model.names
            nc = len(names)
            model_task = model.task
            
            return (
                f"### ✅ Model Validated\n"
                f"- **Path:** `{path}`\n"
                f"- **Task:** `{model_task}` (Expected: `{task}`)\n"
                f"- **Classes:** {nc}\n"
                f"- **Names:** {list(names.values())[:5]}..."
            )
        except Exception as e:
            return f"❌ Invalid Model: {str(e)}"

    def update_model_dropdown(self, task: str):
        """UI Event: Update model list when task changes."""
        choices = self.model_map.get(task, [])
        if not choices:
            choices = [GlobalConfig.DEFAULT_MODELS.get(task, "yolov8n.pt")]
        return gr.update(choices=choices, value=choices[0])

    def refresh_models(self, task: str):
        """UI Event: Manually refresh model list."""
        self.model_map = self.model_manager.scan_checkpoints()
        return self.update_model_dropdown(task)

    # ==================== F1 Studio Task Management Methods ====================

    def handle_train_submit(self, model: str, data: str, epochs: int, imgsz: int, timeout: int, async_mode: bool = True) -> Tuple[str, pd.DataFrame]:
        """Handle train task submission."""
        try:
            # P1.3: Validate timeout
            if timeout < 60:
                return "⚠️ **Timeout must be at least 60 seconds**", pd.DataFrame()
            if timeout > 7200:
                return "⚠️ **Timeout too large (max 2 hours / 7200 seconds)**", pd.DataFrame()

            if async_mode:
                # P1: Submit to async queue
                job_id = self.task_queue.submit(
                    skill="yolo.train",
                    inputs={"model": model, "data": data},
                    params={"epochs": int(epochs), "imgsz": int(imgsz)},
                    timeout=int(timeout)
                )
                message = f"🔄 **Task {job_id} queued**\n\nThe task is executing in the background. Refresh the history to see updates."
            else:
                # P0: Synchronous submission
                response = submit_train(model, data, int(epochs), int(imgsz), timeout=int(timeout))
                job_id = response.get("job_id", "unknown")
                status = response.get("status", "unknown")

                if status == "ok":
                    summary = response.get("summary", "")
                    save_dir = response.get("job", {}).get("save_dir", "")
                    message = f"✅ **Task {job_id} completed successfully**\n\n{summary}\n\n📁 **Output**: `{save_dir}`"
                elif status == "timeout":
                    error_msg = response.get("error", {}).get("message", "Unknown timeout")
                    message = f"⏱️ **Task {job_id} timed out**\n\n{error_msg}"
                else:
                    error = response.get("error", {})
                    error_type = error.get("type", "Unknown")
                    error_msg = error.get("message", "Unknown error")
                    message = f"❌ **Task {job_id} failed**\n\n**Error Type**: {error_type}\n\n**Message**: {error_msg}"

            # Refresh history
            history_df = self.load_task_history()
            return message, history_df
        except Exception as e:
            return f"❌ **Error submitting task**: {str(e)}", pd.DataFrame()

    def handle_predict_submit(self, batch_mode: str, model: str, source: str, timeout: int, async_mode: bool = True) -> Tuple[str, pd.DataFrame]:
        """Handle predict task submission."""
        try:
            # P1.3: Validate timeout
            if timeout < 60:
                return "⚠️ **Timeout must be at least 60 seconds**", pd.DataFrame()
            if timeout > 7200:
                return "⚠️ **Timeout too large (max 2 hours / 7200 seconds)**", pd.DataFrame()

            # P1.2: Validate source based on batch mode
            from pathlib import Path

            # Skip validation for URLs
            if not (source.startswith("http://") or source.startswith("https://")):
                source_path = Path(source)

                if batch_mode == "Directory (Batch)":
                    # Must be a directory
                    if not source_path.exists():
                        return f"❌ **Directory not found**: {source}", pd.DataFrame()
                    if not source_path.is_dir():
                        return f"❌ **Path is not a directory**: {source}\n\nPlease select 'Single File/URL' mode for files.", pd.DataFrame()

                    # Check if directory is empty
                    files = list(source_path.glob("*"))
                    if len(files) == 0:
                        return f"⚠️ **Directory is empty**: {source}", pd.DataFrame()

                    # Info message about batch mode
                    message_prefix = f"📁 **Batch mode**: Processing directory with {len(files)} files\n\n"
                else:
                    # Single mode: prefer file or URL
                    if source_path.exists() and source_path.is_dir():
                        return f"⚠️ **Path is a directory**: {source}\n\nPlease select 'Directory (Batch)' mode for batch processing.", pd.DataFrame()
                    message_prefix = ""

            else:
                message_prefix = ""

            if async_mode:
                # P1: Submit to async queue
                job_id = self.task_queue.submit(
                    skill="yolo.predict",
                    inputs={"model": model, "source": source},
                    params={},
                    timeout=int(timeout)
                )
                message = f"{message_prefix}🔄 **Task {job_id} queued**\n\nThe task is executing in the background. Refresh the history to see updates."
            else:
                # P0: Synchronous submission
                response = submit_predict(model, source, timeout=int(timeout))
                job_id = response.get("job_id", "unknown")
                status = response.get("status", "unknown")

                if status == "ok":
                    summary = response.get("summary", "")
                    save_dir = response.get("job", {}).get("save_dir", "")
                    message = f"{message_prefix}✅ **Task {job_id} completed successfully**\n\n{summary}\n\n📁 **Output**: `{save_dir}`"
                elif status == "timeout":
                    error_msg = response.get("error", {}).get("message", "Unknown timeout")
                    message = f"⏱️ **Task {job_id} timed out**\n\n{error_msg}"
                else:
                    error = response.get("error", {})
                    error_type = error.get("type", "Unknown")
                    error_msg = error.get("message", "Unknown error")
                    message = f"❌ **Task {job_id} failed**\n\n**Error Type**: {error_type}\n\n**Message**: {error_msg}"

            # Refresh history
            history_df = self.load_task_history()
            return message, history_df
        except Exception as e:
            return f"❌ **Error submitting task**: {str(e)}", pd.DataFrame()

    def handle_export_submit(self, model: str, format: str, timeout: int) -> Tuple[str, pd.DataFrame]:
        """Handle export task submission."""
        try:
            # P1.3: Validate timeout
            if timeout < 60:
                return "⚠️ **Timeout must be at least 60 seconds**", pd.DataFrame()
            if timeout > 7200:
                return "⚠️ **Timeout too large (max 2 hours / 7200 seconds)**", pd.DataFrame()

            response = submit_export(model, format, timeout=int(timeout))
            job_id = response.get("job_id", "unknown")
            status = response.get("status", "unknown")

            if status == "ok":
                summary = response.get("summary", "")
                save_dir = response.get("job", {}).get("save_dir", "")

                # For export, also show the exported file info if available
                export_info = ""
                if "export" in response:
                    export_data = response["export"]
                    if "path" in export_data:
                        export_info = f"\n\n📦 **Exported File**: `{export_data['path']}`"
                    if "size" in export_data:
                        size_mb = export_data["size"] / (1024 * 1024)
                        export_info += f"\n📏 **Size**: {size_mb:.2f} MB"

                message = f"✅ **Task {job_id} completed successfully**\n\n{summary}\n\n📁 **Output**: `{save_dir}`{export_info}"
            elif status == "timeout":
                error_msg = response.get("error", {}).get("message", "Unknown timeout")
                message = f"⏱️ **Task {job_id} timed out**\n\n{error_msg}"
            else:
                error = response.get("error", {})
                error_type = error.get("type", "Unknown")
                error_msg = error.get("message", "Unknown error")
                message = f"❌ **Task {job_id} failed**\n\n**Error Type**: {error_type}\n\n**Message**: {error_msg}"

            # Refresh history
            history_df = self.load_task_history()
            return message, history_df
        except Exception as e:
            return f"❌ **Error submitting task**: {str(e)}", pd.DataFrame()

    def handle_system_check(self) -> str:
        """Handle system check."""
        try:
            response = submit_system_check()
            status = response.get("status", "unknown")

            if status == "ok":
                return f"✅ **Environment Check Passed**\n\n```json\n{json.dumps(response, indent=2)}\n```"
            else:
                error_msg = response.get("error", {}).get("message", "Unknown error")
                return f"❌ **Environment Check Failed**\n\n{error_msg}"
        except Exception as e:
            return f"❌ **Error running system check**: {str(e)}"

    def handle_cancel_task(self, job_id: str) -> Tuple[str, pd.DataFrame]:
        """Cancel a running task."""
        if not job_id or job_id.strip() == "":
            return "⚠️ Please enter a Job ID", self.load_task_history()

        job_id = job_id.strip()
        success = self.task_queue.cancel(job_id)

        if success:
            message = f"🛑 **Task {job_id} cancellation requested**\n\nThe task will be cancelled if it hasn't completed yet."
        else:
            message = f"⚠️ **Task {job_id} not found or already completed**\n\nOnly running tasks can be cancelled."

        return message, self.load_task_history()

    def handle_experiment_comparison(self, selected_job_ids: List[str]) -> Tuple[pd.DataFrame, str]:
        """
        Compare multiple training experiments and generate comparison report.

        Args:
            selected_job_ids: List of job IDs to compare

        Returns:
            Tuple of (comparison_dataframe, markdown_summary)
        """
        # Edge case 1: Check if at least 2 jobs selected
        if len(selected_job_ids) < 2:
            empty_df = pd.DataFrame(columns=["Job ID", "Epochs", "ImgSz", "mAP50", "mAP50-95", "Precision", "Recall", "Loss"])
            warning = "⚠️ **Please select at least 2 jobs to compare**\n\nSelect multiple rows in Task History and click 'Compare Selected Jobs'."
            return empty_df, warning

        # Get metrics for all selected jobs
        results = self.db.get_jobs_for_comparison(selected_job_ids)

        # Edge case 2: No valid training results found
        if len(results) == 0:
            empty_df = pd.DataFrame(columns=["Job ID", "Epochs", "ImgSz", "mAP50", "mAP50-95", "Precision", "Recall", "Loss"])
            error = "❌ **No valid training results found**\n\nThe selected jobs either:\n- Are not training tasks (predict/export jobs don't have metrics)\n- Don't have results.csv files\n- Have been deleted from disk"
            return empty_df, error

        # Edge case 3: Some jobs filtered out (non-training or missing metrics)
        filtered_count = len(selected_job_ids) - len(results)
        filter_warning = ""
        if filtered_count > 0:
            filter_warning = f"\n⚠️ Note: {filtered_count} job(s) were filtered out (non-training or missing results.csv)\n"

        # Build DataFrame
        rows = []
        for r in results:
            rows.append({
                "Job ID": r["job_id"],
                "Epochs": r["epochs"],
                "ImgSz": r["imgsz"],
                "mAP50": r["mAP50"],
                "mAP50-95": r["mAP50-95"],
                "Precision": r["precision"],
                "Recall": r["recall"],
                "Loss": r["box_loss"]
            })

        df = pd.DataFrame(rows)

        # Sort by mAP50 descending (best first)
        df = df.sort_values("mAP50", ascending=False).reset_index(drop=True)

        # Generate markdown summary
        best_job = df.iloc[0]
        best_job_id = best_job["Job ID"]
        best_mAP50 = best_job["mAP50"]

        summary = f"""## 📊 Experiment Comparison Results

**Best performing model**: {best_job_id} (mAP50: {best_mAP50:.3f})
**Compared jobs**: {len(results)} training tasks{filter_warning}

### Key Findings:
"""

        # Generate insights based on data
        insights = []

        # Insight 1: Epochs impact
        if len(df) >= 2:
            epochs_sorted = df.sort_values("Epochs")
            if len(epochs_sorted) >= 2:
                min_epoch_row = epochs_sorted.iloc[0]
                max_epoch_row = epochs_sorted.iloc[-1]
                if max_epoch_row["Epochs"] > min_epoch_row["Epochs"]:
                    epoch_diff = max_epoch_row["Epochs"] - min_epoch_row["Epochs"]
                    mAP_diff = max_epoch_row["mAP50"] - min_epoch_row["mAP50"]
                    if mAP_diff > 0:
                        pct_improvement = (mAP_diff / (min_epoch_row["mAP50"] + 0.001)) * 100  # Avoid div by 0
                        insights.append(f"- Higher epochs ({int(max_epoch_row['Epochs'])}) → +{pct_improvement:.1f}% mAP50 improvement")
                    elif mAP_diff < 0:
                        insights.append(f"- More epochs didn't improve performance (possible overfitting)")

        # Insight 2: Image size impact
        unique_imgsz = df["ImgSz"].unique()
        if len(unique_imgsz) > 1 and -1 not in unique_imgsz:
            imgsz_sorted = df.sort_values("ImgSz")
            if len(imgsz_sorted) >= 2:
                small_img = imgsz_sorted.iloc[0]
                large_img = imgsz_sorted.iloc[-1]
                if large_img["mAP50"] > small_img["mAP50"]:
                    insights.append(f"- Larger image size ({int(large_img['ImgSz'])}) → better accuracy than {int(small_img['ImgSz'])}")

        # Insight 3: Loss correlation
        if df["mAP50"].max() > 0:
            correlation = df[["mAP50", "Loss"]].corr().iloc[0, 1]
            if correlation < -0.5:
                insights.append(f"- Lower loss correlates with better mAP50 (correlation: {correlation:.2f})")

        # Add insights to summary
        if insights:
            summary += "\n".join(insights)
        else:
            summary += "- Results are similar across experiments\n- Consider trying different hyperparameters for more variation"

        return df, summary

    def handle_experiment_comparison_from_selection(self, selected_rows: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
        """
        Wrapper method to handle experiment comparison from Gradio selected rows.

        Args:
            selected_rows: DataFrame of selected rows from Task History

        Returns:
            Tuple of (comparison_dataframe, markdown_summary)
        """
        # Check if any rows selected
        if selected_rows is None or len(selected_rows) == 0:
            empty_df = pd.DataFrame(columns=["Job ID", "Epochs", "ImgSz", "mAP50", "mAP50-95", "Precision", "Recall", "Loss"])
            warning = "⚠️ **No jobs selected**\n\nPlease select rows in Task History by clicking on them, then click 'Compare Selected Jobs'."
            return empty_df, warning

        # Extract job IDs from selected rows
        # Gradio returns selected rows as DataFrame with same columns as original
        job_ids = selected_rows["Job ID"].tolist()

        # Call the main comparison handler
        return self.handle_experiment_comparison(job_ids)

    def load_task_history(self) -> pd.DataFrame:
        """Load task history from database as DataFrame with status indicators."""
        jobs = self.db.load_job_history(limit=50)

        if not jobs:
            return pd.DataFrame(columns=["Job ID", "Skill", "Status", "Submitted At", "Artifacts"])

        rows = []
        for job in jobs:
            artifact_count = len(job.get("artifacts", []))
            artifact_str = f"{artifact_count} files" if artifact_count > 0 else "-"

            # Add status emoji for visual indication
            status = job["status"]
            status_display = {
                "ok": "✅ ok",
                "failed": "❌ failed",
                "timeout": "⏱️ timeout",
                "queued": "🔄 queued",
                "running": "⚙️ running",
                "cancelled": "🛑 cancelled"
            }.get(status, f"⚪ {status}")

            rows.append({
                "Job ID": job["job_id"],
                "Skill": job["skill"],
                "Status": status_display,
                "Submitted At": job["submitted_at"][:19],  # Trim microseconds
                "Artifacts": artifact_str
            })

        return pd.DataFrame(rows)

    def view_artifacts(self, job_id: str) -> Tuple[str, List[str]]:
        """View artifacts for a specific job and return downloadable files."""
        if not job_id or job_id.strip() == "":
            return "⚠️ Please enter a Job ID", []

        job = self.db.get_job(job_id.strip())
        if not job:
            return f"❌ Job not found: {job_id}", []

        artifacts = job.get("artifacts", [])
        if not artifacts:
            return f"ℹ️ No artifacts found for job {job_id}", []

        # Group by category
        by_category = {}
        for artifact in artifacts:
            cat = artifact["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(artifact)

        # Format output with download paths
        lines = [f"## 📦 Artifacts for Job: `{job_id}`\n"]
        lines.append(f"**Status**: {job.get('status', 'unknown')}")
        lines.append(f"**Skill**: {job.get('skill', 'unknown')}")

        # Extract save_dir for display
        response = job.get("response", {})
        if "job" in response and "save_dir" in response["job"]:
            lines.append(f"**Save Directory**: `{response['job']['save_dir']}`")

        lines.append("\n---\n")

        # Collect files for download component
        downloadable_files = []

        for category in ["weight", "result", "export", "config", "log", "other"]:
            if category not in by_category:
                continue

            # Use emoji for each category
            category_emoji = {
                "weight": "⚖️",
                "result": "📊",
                "export": "📦",
                "config": "⚙️",
                "log": "📝",
                "other": "📄"
            }
            emoji = category_emoji.get(category, "📄")

            lines.append(f"### {emoji} {category.title()}s ({len(by_category[category])} files)\n")

            for artifact in by_category[category]:
                size_mb = artifact["size"] / (1024 * 1024)
                name = artifact.get("name", artifact["rel_path"])

                # Format size appropriately
                if size_mb >= 1:
                    size_str = f"{size_mb:.2f} MB"
                elif artifact["size"] >= 1024:
                    size_str = f"{artifact['size'] / 1024:.2f} KB"
                else:
                    size_str = f"{artifact['size']} bytes"

                lines.append(f"- **{name}** ({size_str})")
                lines.append(f"  - Path: `{artifact['rel_path']}`")

                # Add to downloadable list (we'll show the first few key files)
                if category in ["weight", "result", "export"] and len(downloadable_files) < 5:
                    downloadable_files.append(artifact["path"])

            lines.append("")  # Blank line between categories

        return "\n".join(lines), downloadable_files

    def clear_history(self) -> Tuple[str, pd.DataFrame]:
        """Clear all task history."""
        count = self.db.clear_history()
        return f"✅ Cleared {count} records", pd.DataFrame(columns=["Job ID", "Skill", "Status", "Submitted At", "Artifacts"])

    def launch(self):
        import json  # Import for system check JSON display

        with gr.Blocks(title="YOLO-Master WebUI", theme=GlobalConfig.THEME) as app:
            gr.Markdown("# 🚀 YOLO-Master Dashboard")

            with gr.Tabs():
                # ================= Original Inference Tab =================
                with gr.TabItem("🖼️ Inference"):
                    with gr.Row(equal_height=False):
                        # Sidebar: Control Panel
                        with gr.Column(scale=1, variant="panel"):
                            gr.Markdown("### 🛠 Settings")

                            # Task and Model Selection
                            with gr.Group():
                                task_radio = gr.Radio(
                                    choices=["detect", "seg", "cls", "pose", "obb"],
                                    value="detect",
                                    label="Task"
                                )
                                with gr.Row():
                                    model_dd = gr.Dropdown(
                                        choices=self.model_map["detect"],
                                        value=self.model_map["detect"][0] if self.model_map["detect"] else None,
                                        label="Model Weights",
                                        scale=5,
                                        interactive=True
                                    )
                                    refresh_btn = gr.Button("🔄", scale=1, min_width=10, size="sm")
                                custom_model_txt = gr.Textbox(
                                    value="",
                                    label="Custom Model Path (file or directory)",
                                    placeholder="./ckpts/yolo_master_n.pt",
                                    interactive=True
                                )
                                validate_btn = gr.Button("✅ Validate Path", size="sm")

                            # Advanced Parameters
                            with gr.Accordion("⚙️ Advanced Parameters", open=True):
                                conf_slider = gr.Slider(0, 1, 0.25, step=0.01, label="Confidence (Conf)")
                                iou_slider = gr.Slider(0, 1, 0.7, step=0.01, label="IoU Threshold")

                                with gr.Row():
                                    max_det_num = gr.Number(300, label="Max Objects", precision=0)
                                    line_width_num = gr.Number(0, label="Line Width", precision=0)

                                with gr.Row():
                                    device_txt = gr.Textbox("0", label="Device ID (e.g. 0, cpu)", placeholder="0 or cpu")
                                    cpu_chk = gr.Checkbox(False, label="Force CPU")

                            # Output Options
                            options_chk = gr.CheckboxGroup(
                                ["half", "show", "save", "save_txt", "save_crop", "hide_labels", "hide_conf", "agnostic_nms", "retina_masks"],
                                label="Output Options",
                                value=[]
                            )

                            # Run Button
                            run_btn = gr.Button("🔥 Start Inference", variant="primary", size="lg")

                        # Main Area: Display Panel
                        with gr.Column(scale=3):
                            with gr.Tabs():
                                with gr.TabItem("🖼️ Visualization"):
                                    with gr.Row():
                                        inp_img = gr.Image(type="numpy", label="Input Image", height=500)
                                        out_img = gr.Image(type="numpy", label="Inference Result", height=500, interactive=False)
                                    info_md = gr.Markdown(value="Waiting for input...")

                                with gr.TabItem("📊 Data Analysis"):
                                    gr.Markdown("### Detections Data")
                                    out_df = gr.Dataframe(
                                        headers=["Class ID", "Class Name", "Confidence", "x1", "y1", "x2", "y2"],
                                        label="Raw Detections"
                                    )

                    # Event Binding for Inference Tab
                    task_radio.change(fn=self.update_model_dropdown, inputs=task_radio, outputs=model_dd)
                    refresh_btn.click(fn=self.refresh_models, inputs=task_radio, outputs=model_dd)
                    validate_btn.click(fn=self.describe_model, inputs=[task_radio, custom_model_txt], outputs=info_md)

                    run_btn.click(
                        fn=self.inference,
                        inputs=[
                            task_radio, inp_img, model_dd, custom_model_txt,
                            conf_slider, iou_slider, device_txt,
                            max_det_num, line_width_num, cpu_chk, options_chk
                        ],
                        outputs=[out_img, out_df, info_md]
                    )

                # ================= NEW: Task Management Tab =================
                with gr.TabItem("📋 Task Management"):
                    gr.Markdown("## F1 Studio - Agent Task Management")

                    # System Check Button at the top
                    with gr.Row():
                        system_check_btn = gr.Button("🩺 Environment Check", variant="secondary")
                    system_check_output = gr.Markdown(value="")

                    gr.Markdown("---")

                    # Task Submission Area
                    gr.Markdown("### 🚀 Task Submission")

                    # P1: Async mode toggle
                    with gr.Row():
                        async_mode_checkbox = gr.Checkbox(label="⚡ Async Mode (run tasks in background)", value=True)
                        gr.Markdown("*Enable to submit tasks without blocking. Disable for immediate feedback.*")

                    with gr.Tabs():
                        # Train Task
                        with gr.TabItem("🏋️ Train"):
                            with gr.Row():
                                with gr.Column():
                                    train_model = gr.Textbox(label="Model", value="yolo11n.pt", placeholder="yolo11n.pt")
                                    train_data = gr.Textbox(label="Data", value="coco8.yaml", placeholder="coco8.yaml")
                                with gr.Column():
                                    train_epochs = gr.Number(label="Epochs", value=1, precision=0)
                                    train_imgsz = gr.Number(label="Image Size", value=32, precision=0)

                            # P1.3: Timeout configuration
                            with gr.Accordion("⚙️ Advanced Options", open=False):
                                train_timeout = gr.Number(
                                    label="Timeout (seconds)",
                                    value=1800,  # 30 minutes for training
                                    precision=0,
                                    info="Maximum execution time. Training jobs typically need more time."
                                )

                            train_submit_btn = gr.Button("▶️ Submit Train Task", variant="primary")
                            train_output = gr.Markdown(value="")

                        # Predict Task
                        with gr.TabItem("🔍 Predict"):
                            # P1.2: Batch mode selection
                            batch_mode = gr.Radio(
                                choices=["Single File/URL", "Directory (Batch)"],
                                value="Single File/URL",
                                label="Mode",
                                info="Single: one image/video/URL. Batch: process all files in a directory"
                            )

                            with gr.Row():
                                predict_model = gr.Textbox(label="Model", value="yolo11n.pt", placeholder="yolo11n.pt")
                                predict_source = gr.Textbox(
                                    label="Source",
                                    value="coco8/images/",
                                    placeholder="Path to image, video, URL, or directory"
                                )

                            # P1.3: Timeout configuration
                            with gr.Accordion("⚙️ Advanced Options", open=False):
                                predict_timeout = gr.Number(
                                    label="Timeout (seconds)",
                                    value=600,  # 10 minutes
                                    precision=0,
                                    info="Maximum execution time. Task will be cancelled if exceeded."
                                )

                            predict_submit_btn = gr.Button("▶️ Submit Predict Task", variant="primary")
                            predict_output = gr.Markdown(value="")

                        # Export Task
                        with gr.TabItem("📦 Export"):
                            with gr.Row():
                                export_model = gr.Textbox(label="Model", value="yolo11n.pt", placeholder="yolo11n.pt")
                                export_format = gr.Dropdown(
                                    choices=["onnx", "torchscript", "coreml", "saved_model", "tflite"],
                                    value="onnx",
                                    label="Format"
                                )

                            # P1.3: Timeout configuration
                            with gr.Accordion("⚙️ Advanced Options", open=False):
                                export_timeout = gr.Number(
                                    label="Timeout (seconds)",
                                    value=600,  # 10 minutes
                                    precision=0,
                                    info="Maximum execution time for model export."
                                )

                            export_submit_btn = gr.Button("▶️ Submit Export Task", variant="primary")
                            export_output = gr.Markdown(value="")

                    gr.Markdown("---")

                    # Task History Area
                    gr.Markdown("### 📜 Task History")
                    with gr.Row():
                        refresh_history_btn = gr.Button("🔄 Refresh History")
                        clear_history_btn = gr.Button("🗑️ Clear History", variant="stop")

                    history_df = gr.Dataframe(
                        value=self.load_task_history(),
                        headers=["Job ID", "Skill", "Status", "Submitted At", "Artifacts"],
                        label="Task History",
                        interactive=True  # P1 Task 1.3: Enable row selection
                    )

                    # P1 Task 1.3: Experiment Comparison
                    gr.Markdown("---")
                    gr.Markdown("### 📊 Experiment Comparison")
                    gr.Markdown("💡 **Tip**: Select 2 or more training tasks above to compare their performance metrics")
                    with gr.Row():
                        compare_btn = gr.Button("🔬 Compare Selected Jobs", variant="primary")
                    comparison_output = gr.Markdown(value="")
                    comparison_table = gr.Dataframe(
                        value=pd.DataFrame(),
                        label="Comparison Results"
                    )

                    gr.Markdown("---")

                    # P1: Task Control
                    gr.Markdown("### ⚙️ Task Control")
                    with gr.Row():
                        cancel_job_id = gr.Textbox(label="Job ID", placeholder="Enter Job ID to cancel")
                        cancel_task_btn = gr.Button("🛑 Cancel Task", variant="stop")
                    cancel_output = gr.Markdown(value="")

                    # Artifact Viewer
                    gr.Markdown("### 🔍 Artifact Inspector")
                    with gr.Row():
                        artifact_job_id = gr.Textbox(label="Job ID", placeholder="Enter Job ID to view artifacts")
                        view_artifacts_btn = gr.Button("👁️ View Artifacts")
                    artifact_output = gr.Markdown(value="")

                    # Download section
                    gr.Markdown("**Quick Downloads** (key files from selected job)")
                    artifact_files = gr.File(
                        label="Downloadable Files",
                        file_count="multiple",
                        interactive=False,
                        visible=True
                    )

                    # Event Binding for Task Management Tab
                    system_check_btn.click(
                        fn=self.handle_system_check,
                        outputs=system_check_output
                    )

                    train_submit_btn.click(
                        fn=self.handle_train_submit,
                        inputs=[train_model, train_data, train_epochs, train_imgsz, train_timeout, async_mode_checkbox],
                        outputs=[train_output, history_df]
                    )

                    predict_submit_btn.click(
                        fn=self.handle_predict_submit,
                        inputs=[batch_mode, predict_model, predict_source, predict_timeout, async_mode_checkbox],
                        outputs=[predict_output, history_df]
                    )

                    export_submit_btn.click(
                        fn=self.handle_export_submit,
                        inputs=[export_model, export_format, export_timeout],
                        outputs=[export_output, history_df]
                    )

                    cancel_task_btn.click(
                        fn=self.handle_cancel_task,
                        inputs=[cancel_job_id],
                        outputs=[cancel_output, history_df]
                    )

                    refresh_history_btn.click(
                        fn=self.load_task_history,
                        outputs=history_df
                    )

                    clear_history_btn.click(
                        fn=self.clear_history,
                        outputs=[artifact_output, history_df]
                    )

                    # P1 Task 1.3: Experiment comparison event binding
                    compare_btn.click(
                        fn=self.handle_experiment_comparison_from_selection,
                        inputs=history_df,
                        outputs=[comparison_table, comparison_output]
                    )

                    view_artifacts_btn.click(
                        fn=self.view_artifacts,
                        inputs=artifact_job_id,
                        outputs=[artifact_output, artifact_files]
                    )

        app.launch(share=False, inbrowser=True)


if __name__ == "__main__":
    # Configure your checkpoints path
    CKPTS_DIR = Path(__file__).parent / "ckpts"
    
    # Create default dir if not exists
    if not CKPTS_DIR.exists():
        CKPTS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created default checkpoints dir: {CKPTS_DIR}")
    
    print(f"Starting YOLO-Master WebUI...")
    print(f"Scanning models in: {CKPTS_DIR}")
    
    ui = YOLO_Master_WebUI(str(CKPTS_DIR))
    ui.launch()
