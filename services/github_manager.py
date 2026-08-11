import subprocess
import os
import asyncio
import shutil
from datetime import datetime
from core.logger import log_info, log_error
from core.config import GITHUB_BACKUP_REPO, GITHUB_BACKUP_TOKEN

class GithubManager:
    def __init__(self):
        self.project_root = os.path.abspath(".")
        self.backup_dir = os.path.join(self.project_root, ".github_backup")
        self.repo_url = GITHUB_BACKUP_REPO
        self.token = GITHUB_BACKUP_TOKEN
    
    def is_enabled(self) -> bool:
        return bool(self.repo_url and self.token)

    def _get_authed_url(self) -> str:
        if not self.repo_url or not self.token:
            return ""
        
        clean_url = self.repo_url.replace("https://", "")
        return f"https://{self.token}@{clean_url}"

    def _redact(self, text: str) -> str:
        if not self.token or not text:
            return text
        return text.replace(self.token, "********")

    async def run_git_command(self, args: list[str], cwd: str = None) -> tuple[bool, str]:
        try:
            work_dir = cwd or self.backup_dir
            process = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            # args carry the authenticated remote URL on clone/remote commands
            command = self._redact(f"git {' '.join(args)}")

            if process.returncode == 0:
                output = stdout.decode().strip()
                log_info(f"Git command success: {command}")
                return True, output
            else:
                error = self._redact(stderr.decode().strip())
                log_error(f"Git command failed: {command}\nError: {error}")
                return False, error
        except Exception as e:
            log_error(f"Exception running git command: {e}")
            return False, str(e)

    async def _prepare_repo(self) -> bool:
        if not self.repo_url or not self.token:
            log_error("GitHub Backup settings are missing in secrets.py!")
            return False

        authed_url = self._get_authed_url()

        # Gate on the working copy, not the directory: a bind mount or docker
        # volume makes the directory exist before anything was cloned into it.
        if not os.path.isdir(os.path.join(self.backup_dir, ".git")):
            log_info(f"Initializing backup repository: {self.backup_dir}")
            os.makedirs(self.backup_dir, exist_ok=True)

            success, err = await self.run_git_command(["clone", authed_url, "."], cwd=self.backup_dir)
            if not success:
                success, err = await self.run_git_command(["init"], cwd=self.backup_dir)
                if success:
                    await self.run_git_command(["remote", "add", "origin", authed_url], cwd=self.backup_dir)
                    await self.run_git_command(["branch", "-M", "main"], cwd=self.backup_dir)
                else:
                    return False
        else:
            await self.run_git_command(["remote", "set-url", "origin", authed_url])
            await self.run_git_command(["config", "pull.rebase", "false"])
            await self.run_git_command(["pull", "origin", "main", "--allow-unrelated-histories"])
            
        return True

    async def backup_data(self) -> tuple[bool, str]:
        if not await self._prepare_repo():
            return False, "Failed to prepare backup repository. Check your GITHUB_BACKUP_REPO and GITHUB_BACKUP_TOKEN."

        important_files = [
            "data/daily_data.json",
            "data/rng_data.json",
            "data/user_links.json",
            "data/custom_names.json",
            "data/config.json",
            "data/solo_clears.json",
            "data/recent_teammates.json",
            "data/ip_bans.json",
            "data/irc_history.json",
        ]
        
        files_copied = 0
        for rel_path in important_files:
            src = os.path.join(self.project_root, rel_path)
            dst = os.path.join(self.backup_dir, rel_path)
            
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                files_copied += 1
        
        if files_copied == 0:
            return False, "No important data files found to back up."
        
        await self.run_git_command(["add", "."])
        
        success, output = await self.run_git_command(["status", "--porcelain"])
        if not output:
            return True, "No changes detected in data files."
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_msg = f"chore: automated data backup {timestamp}"
        success, err = await self.run_git_command(["commit", "-m", commit_msg])
        if not success:
            return False, f"Failed to commit: {err}"
            
        success, err = await self.run_git_command(["push", "-u", "origin", "main"])
        if not success:
            return False, f"Failed to push: {err}"
            
        return True, f"Backup successful at {timestamp}!"
