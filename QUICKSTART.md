# Quick Start

## Installation

First, clone the repository to your local machine:

**Linux and Windows:**
```bash
git clone https://github.com/BLACKUM/rtca-bot-hypixel.git
cd rtca-bot-hypixel
```

## Configuration

Before running, you need to set up your Discord bot token:

1. **Create the secrets file:**
   
   **Linux:**
   ```bash
   cp core/secrets.example.py core/secrets.py
   ```
   
   **Windows:**
   ```cmd
   copy core\secrets.example.py core\secrets.py
   ```

2. **Edit `core/secrets.py` and add your Discord Bot Token:**
   ```python
   TOKEN = "your_discord_bot_token_here"
   ```
   
   Get your token from: https://discord.com/developers/applications

**Note:** The `core/secrets.py` file is not tracked by git for security reasons.

## Running the Bot

### For Linux

1. **Make the script executable:**
   ```bash
   chmod +x run.sh
   ```

2. **Run the bot:**
   ```bash
   ./run.sh
   ```

   The script will automatically create a virtual environment and install all dependencies.

### For Windows

#### Option 1: CMD (run.bat)

1. **Double-click on `run.bat`** or run from command prompt:
   ```cmd
   run.bat
   ```

#### Option 2: PowerShell (run.ps1)

1. **Open PowerShell** in the project folder
2. **If you get a script execution error**, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. **Run the script:**
   ```powershell
   .\run.ps1
   ```

### Alternative Method (No Virtual Environment)

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
*(Or `python --version` on Windows)*

Install dependencies manually (if needed):
```bash
pip3 install -r requirements.txt
```

## Running in Background (Linux)

I recommend using `tmux` for managing the bot in the background.

1. **Check for existing sessions:**
   ```bash
   tmux ls
   ```

2. **Start the bot:**
   ```bash
   tmux new -s rtca "cd /path/to/bot && source venv/bin/activate && chmod +x run.sh && ./run.sh"
   ```

3. **Detach from session:** `Ctrl+B`, then `D`.

4. **Reattach to session:**
   ```bash
   tmux attach -t rtca
   ```
   
5. **Stop the bot:**
   ```bash
   tmux kill-session -t rtca
   ```

## Updating the Bot

To update the bot to the latest version:

1. **Stop the bot**
2. **Pull the latest changes:**
   ```bash
   git pull origin main
   ```
3. **Restart the bot**
