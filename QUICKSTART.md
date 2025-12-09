# Quick Start

## For Linux

1. **Make the script executable:**
   ```bash
   chmod +x run.sh
   ```

2. **Run the bot:**
   ```bash
   ./run.sh
   ```

The script will automatically create a virtual environment and install all dependencies.

## For Windows

### Option 1: CMD (run.bat)

1. **Double-click on `run.bat`** or run from command prompt:
   ```cmd
   run.bat
   ```

### Option 2: PowerShell (run.ps1)

1. **Open PowerShell** in the project folder
2. **If you get a script execution error**, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. **Run the script:**
   ```powershell
   .\run.ps1
   ```

The scripts will automatically create a virtual environment and install all dependencies.

## Alternative Method (without virtual environment)

**Linux:**
```bash
python3 main.py
```

**Windows:**
```cmd
python main.py
```

## Installation Check

**Linux and Windows:**
Make sure you have Python 3.8+ installed:
```bash
python3 --version
```

Install dependencies manually (if needed):
```bash
pip3 install -r requirements.txt
```

## Configuration

Before running, you need to set up your Discord bot token:

1. **Create the secrets file:**
   
   **Linux:**
   ```bash
   cp secrets.example.py secrets.py
   ```
   
   **Windows:**
   ```cmd
   copy secrets.example.py secrets.py
   ```

2. **Edit `secrets.py` and add your Discord Bot Token:**
   ```python
   TOKEN = "your_discord_bot_token_here"
   ```
   
   Get your token from: https://discord.com/developers/applications

**Note:** The `secrets.py` file is not tracked by git for security reasons. You need to create it from `secrets.example.py`.

## Running in Background

### For Linux Servers

We recommend using `tmux` for managing the bot in the background.

1. **Check for existing sessions:**
   ```bash
   tmux ls
   ```

2. **Kill existing session (if needed):**
   ```bash
   tmux kill-session -t rtca
   ```

3. **Start the bot:**
   Replace `/path/to/bot` with your actual bot directory path.
   ```bash
   tmux new -s rtca "cd /path/to/bot && source venv/bin/activate && chmod +x run.sh && ./run.sh"
   ```
   *This command creates a new session named 'rtca', navigates to the directory, activates the virtual environment, makes run.sh executable, and runs it - all in one go.*

4. **Detach from session:**
   Press `Ctrl+B`, then `D`.

5. **Reattach to session:**
   ```bash
   tmux attach -t rtca
   ```

### For Windows

Use Windows Task Scheduler or run as a service. For simple background execution, you can use PowerShell:

```powershell
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden
```

Or create a shortcut for `run.bat` and configure it to run in the background.

Win+r > shell:startup and place it here 

## Updating the Bot

To update the bot to the latest version:

1. **Stop the bot** if it's currently running

2. **Pull the latest changes from git:**
   
   **Linux:**
   ```bash
   git pull origin main
   ```
   
   **Windows:**
   ```cmd
   git pull origin main
   ```

3. **Restart the bot** using your preferred method (run.sh, run.bat, run.ps1, etc.)

**Note:** Your `secrets.py` file will not be affected by updates as it's not tracked by git.

