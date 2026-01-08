#!/bin/bash

# RTCA Discord Bot Launcher for Linux
SESSION="rtca"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed. Please install tmux first."
    exit 1
fi

# Check if we are inside tmux
if [ -z "$TMUX" ]; then
    # Get absolute path to this script
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    SCRIPT_NAME=$(basename "$0")
    SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"

    # Check if session exists
    tmux has-session -t $SESSION 2>/dev/null

    if [ $? != 0 ]; then
        echo "Creating new tmux session: $SESSION"
        # Create session and run this script inside it
        # We append '; read' to keep the window open if the script crashes
        tmux new-session -s $SESSION -d "bash '$SCRIPT_PATH'; read -p 'Session ended. Press Enter to close...'"
    fi

    echo "Attaching to session: $SESSION"
    tmux attach -t $SESSION
    exit 0
fi

# --- Main Bot Logic (Inside Tmux) ---

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run the bot in a loop for auto-restart
echo "Starting RTCA Discord Bot inside Tmux... (Press Ctrl+C to stop)"
while true; do
    python3 main.py
    echo "Bot stopped. Restarting in 5 seconds..."
    sleep 5
done
