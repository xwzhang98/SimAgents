#!/bin/bash
# Start SimAgents GUI — backend + frontend in one command
set -e

echo "Starting SimAgents GUI..."

# Check conda env
if [[ "$CONDA_DEFAULT_ENV" != "langgraph" ]]; then
    echo "Activating langgraph conda environment..."
    eval "$(conda shell.bash hook 2>/dev/null)"
    conda activate langgraph
fi

# Install Python deps if needed
if python -c "import simagents" 2>/dev/null; then
    pip install -e ".[gui]" -q 2>/dev/null
else
    echo "Installing Python dependencies..."
    pip install -r requirements.txt -q
    pip install -e . -q
fi

# Install frontend deps if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Start backend
echo "Starting backend on http://localhost:8000..."
uvicorn simagents.api.server:app --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

# Open browser after a short delay
sleep 3
if command -v open &>/dev/null; then
    open http://localhost:3000
elif command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:3000
fi

echo ""
echo "SimAgents GUI is running!"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
