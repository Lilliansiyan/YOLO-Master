"""
F1 Studio Lite - 纯任务管理界面（不含推理功能）
用于在没有完整 YOLO 环境时测试任务管理功能
"""
import gradio as gr
import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Tuple

from f1_studio_db import F1StudioDB
from f1_studio_tasks import (
    submit_train,
    submit_predict,
    submit_export,
    submit_system_check,
)


class F1StudioLite:
    def __init__(self):
        self.db = F1StudioDB()

    def handle_train_submit(self, model: str, data: str, epochs: int, imgsz: int) -> Tuple[str, pd.DataFrame]:
        """Handle train task submission."""
        try:
            response = submit_train(model, data, int(epochs), int(imgsz))
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

            history_df = self.load_task_history()
            return message, history_df
        except Exception as e:
            return f"❌ **Error submitting task**: {str(e)}", pd.DataFrame()

    def handle_predict_submit(self, model: str, source: str) -> Tuple[str, pd.DataFrame]:
        """Handle predict task submission."""
        try:
            response = submit_predict(model, source)
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

            history_df = self.load_task_history()
            return message, history_df
        except Exception as e:
            return f"❌ **Error submitting task**: {str(e)}", pd.DataFrame()

    def handle_export_submit(self, model: str, format: str) -> Tuple[str, pd.DataFrame]:
        """Handle export task submission."""
        try:
            response = submit_export(model, format)
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

    def load_task_history(self) -> pd.DataFrame:
        """Load task history from database as DataFrame."""
        jobs = self.db.load_job_history(limit=50)

        if not jobs:
            return pd.DataFrame(columns=["Job ID", "Skill", "Status", "Submitted At", "Artifacts"])

        rows = []
        for job in jobs:
            artifact_count = len(job.get("artifacts", []))
            artifact_str = f"{artifact_count} files" if artifact_count > 0 else "-"

            status = job["status"]
            status_display = {
                "ok": "✅ ok",
                "failed": "❌ failed",
                "timeout": "⏱️ timeout"
            }.get(status, f"⚪ {status}")

            rows.append({
                "Job ID": job["job_id"],
                "Skill": job["skill"],
                "Status": status_display,
                "Submitted At": job["submitted_at"][:19],
                "Artifacts": artifact_str
            })

        return pd.DataFrame(rows)

    def view_artifacts(self, job_id: str) -> Tuple[str, List[str]]:
        """View artifacts for a specific job."""
        if not job_id or job_id.strip() == "":
            return "⚠️ Please enter a Job ID", []

        job = self.db.get_job(job_id.strip())
        if not job:
            return f"❌ Job not found: {job_id}", []

        artifacts = job.get("artifacts", [])
        if not artifacts:
            return f"ℹ️ No artifacts found for job {job_id}", []

        by_category = {}
        for artifact in artifacts:
            cat = artifact["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(artifact)

        lines = [f"## 📦 Artifacts for Job: `{job_id}`\n"]
        lines.append(f"**Status**: {job.get('status', 'unknown')}")
        lines.append(f"**Skill**: {job.get('skill', 'unknown')}")

        response = job.get("response", {})
        if "job" in response and "save_dir" in response["job"]:
            lines.append(f"**Save Directory**: `{response['job']['save_dir']}`")

        lines.append("\n---\n")

        downloadable_files = []
        category_emoji = {
            "weight": "⚖️",
            "result": "📊",
            "export": "📦",
            "config": "⚙️",
            "log": "📝",
            "other": "📄"
        }

        for category in ["weight", "result", "export", "config", "log", "other"]:
            if category not in by_category:
                continue

            emoji = category_emoji.get(category, "📄")
            lines.append(f"### {emoji} {category.title()}s ({len(by_category[category])} files)\n")

            for artifact in by_category[category]:
                size_mb = artifact["size"] / (1024 * 1024)
                name = artifact.get("name", artifact["rel_path"])

                if size_mb >= 1:
                    size_str = f"{size_mb:.2f} MB"
                elif artifact["size"] >= 1024:
                    size_str = f"{artifact['size'] / 1024:.2f} KB"
                else:
                    size_str = f"{artifact['size']} bytes"

                lines.append(f"- **{name}** ({size_str})")
                lines.append(f"  - Path: `{artifact['rel_path']}`")

                if category in ["weight", "result", "export"] and len(downloadable_files) < 5:
                    downloadable_files.append(artifact["path"])

            lines.append("")

        return "\n".join(lines), downloadable_files

    def clear_history(self) -> Tuple[str, pd.DataFrame]:
        """Clear all task history."""
        count = self.db.clear_history()
        return f"✅ Cleared {count} records", pd.DataFrame(columns=["Job ID", "Skill", "Status", "Submitted At", "Artifacts"])

    def launch(self):
        with gr.Blocks(title="F1 Studio - Task Management", theme=gr.themes.Soft(primary_hue="blue")) as app:
            gr.Markdown("# 📋 F1 Studio - YOLO-Master Task Management")
            gr.Markdown("*Lite version - Task management interface without inference features*")

            # System Check
            with gr.Row():
                system_check_btn = gr.Button("🩺 Environment Check", variant="secondary")
            system_check_output = gr.Markdown(value="")

            gr.Markdown("---")

            # Task Submission
            with gr.Tabs():
                with gr.TabItem("🏋️ Train"):
                    with gr.Row():
                        with gr.Column():
                            train_model = gr.Textbox(label="Model", value="yolo11n.pt")
                            train_data = gr.Textbox(label="Data", value="coco8.yaml")
                        with gr.Column():
                            train_epochs = gr.Number(label="Epochs", value=1, precision=0)
                            train_imgsz = gr.Number(label="Image Size", value=32, precision=0)
                    train_submit_btn = gr.Button("▶️ Submit Train Task", variant="primary")
                    train_output = gr.Markdown(value="")

                with gr.TabItem("🔍 Predict"):
                    with gr.Row():
                        predict_model = gr.Textbox(label="Model", value="yolo11n.pt")
                        predict_source = gr.Textbox(label="Source", value="coco8/images/")
                    predict_submit_btn = gr.Button("▶️ Submit Predict Task", variant="primary")
                    predict_output = gr.Markdown(value="")

                with gr.TabItem("📦 Export"):
                    with gr.Row():
                        export_model = gr.Textbox(label="Model", value="yolo11n.pt")
                        export_format = gr.Dropdown(
                            choices=["onnx", "torchscript", "coreml", "saved_model", "tflite"],
                            value="onnx",
                            label="Format"
                        )
                    export_submit_btn = gr.Button("▶️ Submit Export Task", variant="primary")
                    export_output = gr.Markdown(value="")

            gr.Markdown("---")
            gr.Markdown("### 📜 Task History")

            with gr.Row():
                refresh_history_btn = gr.Button("🔄 Refresh History")
                clear_history_btn = gr.Button("🗑️ Clear History", variant="stop")

            history_df = gr.Dataframe(
                value=self.load_task_history(),
                headers=["Job ID", "Skill", "Status", "Submitted At", "Artifacts"],
                label="Task History"
            )

            gr.Markdown("### 🔍 Artifact Inspector")
            with gr.Row():
                artifact_job_id = gr.Textbox(label="Job ID", placeholder="Enter Job ID")
                view_artifacts_btn = gr.Button("👁️ View Artifacts")
            artifact_output = gr.Markdown(value="")

            gr.Markdown("**Quick Downloads**")
            artifact_files = gr.File(label="Downloadable Files", file_count="multiple", interactive=False)

            # Event bindings
            system_check_btn.click(fn=self.handle_system_check, outputs=system_check_output)
            train_submit_btn.click(fn=self.handle_train_submit, inputs=[train_model, train_data, train_epochs, train_imgsz], outputs=[train_output, history_df])
            predict_submit_btn.click(fn=self.handle_predict_submit, inputs=[predict_model, predict_source], outputs=[predict_output, history_df])
            export_submit_btn.click(fn=self.handle_export_submit, inputs=[export_model, export_format], outputs=[export_output, history_df])
            refresh_history_btn.click(fn=self.load_task_history, outputs=history_df)
            clear_history_btn.click(fn=self.clear_history, outputs=[artifact_output, history_df])
            view_artifacts_btn.click(fn=self.view_artifacts, inputs=artifact_job_id, outputs=[artifact_output, artifact_files])

        app.launch(share=False, inbrowser=True)


if __name__ == "__main__":
    print("Starting F1 Studio Lite - Task Management Interface")
    print("=" * 60)
    ui = F1StudioLite()
    ui.launch()
