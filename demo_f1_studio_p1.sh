#!/bin/bash
# F1 Studio P1 Demo Script
# Demonstrates async queue, task cancellation, and progress monitoring

set -e

echo "============================================================"
echo "F1 Studio P1 Demo"
echo "============================================================"
echo ""

# Check environment
echo "📋 Checking environment..."
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run install_dependencies.sh first."
    exit 1
fi

source venv/bin/activate

# Run P1 tests
echo ""
echo "🧪 Running P1 tests..."
echo "============================================================"
python test_f1_studio_p1.py

# Show features
echo ""
echo "✨ P1 Features Implemented:"
echo "============================================================"
echo "1. ✅ Async Task Queue"
echo "   - 2 concurrent background workers"
echo "   - Thread-safe queue operations"
echo "   - Non-blocking UI"
echo ""
echo "2. ✅ Task Cancellation"
echo "   - Cancel queued tasks immediately"
echo "   - Cancel running tasks gracefully"
echo "   - Status persisted to database"
echo ""
echo "3. ✅ Progress Monitoring"
echo "   - Reads progress.jsonl incrementally"
echo "   - No duplicate reads"
echo "   - JSON Lines format support"
echo ""
echo "4. ✅ New Status Indicators"
echo "   - 🔄 queued - Task waiting in queue"
echo "   - ⚙️ running - Task currently executing"
echo "   - 🛑 cancelled - Task was cancelled"
echo ""

# Show code statistics
echo "📊 Code Statistics:"
echo "============================================================"
echo "f1_studio_queue.py:      $(wc -l < f1_studio_queue.py | tr -d ' ') lines"
echo "app.py (P1 changes):     +81 lines"
echo "test_f1_studio_p1.py:    $(wc -l < test_f1_studio_p1.py | tr -d ' ') lines"
echo "F1_STUDIO_P1_README.md:  $(wc -l < F1_STUDIO_P1_README.md | tr -d ' ') lines"
echo "-----------------------------------"
echo "Total P1 code:           ~930 lines"
echo ""

# Show git commits
echo "📝 Git Commits:"
echo "============================================================"
git log --oneline --grep="F1 Studio P1" | head -3
echo ""

# Launch instructions
echo "🚀 To launch F1 Studio with P1 features:"
echo "============================================================"
echo "1. python app.py"
echo "2. Open http://localhost:7860"
echo "3. Go to 'Task Management' tab"
echo "4. Enable '⚡ Async Mode' (enabled by default)"
echo "5. Submit tasks - they run in background"
echo "6. Use 'Task Control' section to cancel tasks"
echo ""

echo "✅ P1 Demo Complete!"
echo "============================================================"
