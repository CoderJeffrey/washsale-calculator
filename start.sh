#!/bin/bash
# Run both FastAPI (backend) and Next.js (frontend) servers

# Exit on first error
set -e

# Define ports (you can change these)
BACKEND_PORT=8000
FRONTEND_PORT=3000

echo "🔧 Starting Wash Sale Dashboard..."
echo "📦 Checking dependencies..."

# ---- Backend ----
if [ ! -d "backend/venv" ]; then
  echo "🐍 Creating Python virtual environment..."
  python3 -m venv backend/venv
  source backend/venv/bin/activate
  pip install -r backend/requirements.txt
  deactivate
fi

# ---- Frontend ----
if [ ! -d "frontend/node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  cd frontend
  npm install
  cd ..
fi

echo "🚀 Launching servers..."
# Start backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port $BACKEND_PORT &
BACK_PID=$!
cd ..

# Start frontend
cd frontend
npm run dev -- --port $FRONTEND_PORT &
FRONT_PID=$!
cd ..

echo "✅ Servers started:"
echo "   - FastAPI backend → http://127.0.0.1:$BACKEND_PORT"
echo "   - Next.js frontend → http://127.0.0.1:$FRONTEND_PORT"
echo
echo "Press Ctrl+C to stop both."

# Wait for either process to exit
wait $BACK_PID $FRONT_PID
