#!/bin/bash

echo "🚀 Starting TimberGem PDF-to-HTML Demo"
echo "======================================"

# Check if we're in the correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null; then
        return 0
    else
        return 1
    fi
}

# Start backend server
echo "📦 Starting backend server on port 5001..."
cd backend

# Check if backend is already running
if check_port 5001; then
    echo "⚠️  Backend already running on port 5001"
else
    # Install backend dependencies if needed
    if [ ! -d "venv" ]; then
        echo "📥 Setting up Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Start backend in background
    echo "🐍 Starting Flask backend..."
    python app.py &
    BACKEND_PID=$!
    sleep 3
fi

cd ..

# Start frontend server
echo "⚛️  Starting frontend server on port 5173..."
cd frontend

# Check if frontend is already running
if check_port 5173; then
    echo "⚠️  Frontend already running on port 5173"
else
    # Install frontend dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📥 Installing Node.js dependencies..."
        npm install
    fi
    
    # Start frontend in background
    echo "🌐 Starting Vite frontend..."
    npm run dev &
    FRONTEND_PID=$!
    sleep 5
fi

cd ..

echo ""
echo "✅ Demo is now running!"
echo "======================================"
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend:  http://localhost:5001"
echo ""
echo "📖 How to use the demo:"
echo "1. The app will auto-load in 'Testing Mode' with the TEST document"
echo "2. Navigate to the 'PDF-to-HTML Pipeline' tab (should be active by default)"
echo "3. Toggle 'Auto Mode ON' to automatically start the simulation"
echo "4. Watch as pages are processed in real-time (3-8 seconds each)"
echo "5. Click on completed pages to view their HTML output"
echo ""
echo "🛑 To stop the demo, press Ctrl+C"

# Keep script running and handle cleanup
cleanup() {
    echo ""
    echo "🛑 Stopping demo servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    # Kill any remaining processes on the ports
    pkill -f "python app.py" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    echo "✅ Demo stopped"
    exit 0
}

trap cleanup INT TERM

# Wait for user to stop
echo "Press Ctrl+C to stop the demo..."
while true; do
    sleep 1
done 