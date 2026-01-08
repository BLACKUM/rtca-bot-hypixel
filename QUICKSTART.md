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

## Running in Background (Linux / Tmux)

The `run.sh` script now automatically handles `tmux` sessions for you.

1.  **Make the script executable (first time only):**
    ```bash
    chmod +x run.sh
    ```

2.  **Simply run the script:**
    ```bash
    ./run.sh
    ```
    
    - If you are NOT in a tmux session, it will create one named `rtca` and attach you to it.
    - If the session already exists, it will attach you to it.
    - Inside the session, the bot runs in a loop. If it crashes or is restarted via the Admin Panel, it will auto-restart.

2.  **Detach from session:** Press `Ctrl+B`, then `D`.

3.  **Reattach later:**
    ```bash
    ./run.sh
    ```
    *(Or manually: `tmux attach -t rtca`)*

4.  **Stop the bot:**
    - Use `/admin` -> **System** -> **Shutdown** in Discord.
    - Or press `Ctrl+C` inside the tmux session window.


## Updating the Bot

To update the bot to the latest version:

1. **Stop the bot**
2. **Pull the latest changes:**
   ```bash
   git pull origin main
   ```
3. **Restart the bot**
