# -*- coding: utf-8 -*-
"""
LUMIXA PRO // C270 CINEMA STUDIO — Built-In GitHub Auto-Sync Engine (`core/github_sync.py`).

LAW 5 COMPLIANCE:
- Checks if `.git` exists in the project directory.
- Runs `git fetch --all` / `git fetch origin` and checks `git status -uno` to see if new commits exist on GitHub.
- Provides `pull_and_restart()` which executes `git pull --rebase --autostash` (and fallback `git reset --hard HEAD && git pull origin main`),
  installs any new packages via `pip install -r requirements.txt --quiet`, and hot-restarts the running desktop app
  via `os.execl(sys.executable, sys.executable, *sys.argv)`.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal


class GitHubSyncManager(QThread):
    """Background GitHub Auto-Sync worker for checking and pulling cloud updates."""

    sync_status = pyqtSignal(str, bool)  # (status_message, update_available)
    sync_completed = pyqtSignal(bool, str)  # (success, detail_message)

    def __init__(self, repo_root: Optional[Path] = None, parent=None) -> None:
        super().__init__(parent)
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent
        self._mode: str = "check"  # "check" or "pull"

    def check_for_updates_async(self) -> None:
        if self.isRunning():
            return
        self._mode = "check"
        self.start()

    def trigger_pull_and_sync_async(self) -> None:
        if self.isRunning():
            return
        self._mode = "pull"
        self.start()

    def _run_git(self, args: list) -> subprocess.CompletedProcess:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        return subprocess.run(
            ["git"] + args,
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=25,
            creationflags=creationflags,
        )

    def run(self) -> None:
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            self.sync_status.emit("GitHub Sync: Local Standalone Mode (No .git repo)", False)
            if self._mode == "pull":
                self.sync_completed.emit(False, "No .git folder found in application root.")
            return

        if self._mode == "check":
            try:
                self._run_git(["fetch", "--all", "--quiet"])
                self._run_git(["fetch", "origin", "--quiet"])
                st = self._run_git(["status", "-uno"])
                output = (st.stdout or "") + (st.stderr or "")
                if "behind" in output.lower():
                    self.sync_status.emit("UPDATE AVAILABLE ON GITHUB", True)
                else:
                    self.sync_status.emit("GITHUB SYNC: UP TO DATE", False)
            except Exception as exc:
                self.sync_status.emit(f"GitHub Sync Offline ({exc})", False)
            return

        if self._mode == "pull":
            try:
                self.sync_status.emit("SYNCING FROM GITHUB...", False)
                self._run_git(["fetch", "--all"])
                res = self._run_git(["pull", "--rebase", "--autostash"])
                if res.returncode != 0:
                    # Fallback to clean reset + pull origin main/master
                    self._run_git(["reset", "--hard", "HEAD"])
                    res = self._run_git(["pull", "origin", "main"])
                    if res.returncode != 0:
                        res = self._run_git(["pull", "origin", "master"])

                req_file = self.repo_root / "requirements.txt"
                if req_file.exists():
                    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
                        cwd=str(self.repo_root),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=60,
                        creationflags=creationflags,
                    )

                self.sync_status.emit("GITHUB SYNC COMPLETE", False)
                self.sync_completed.emit(True, (res.stdout or "Updated to latest commit.").strip())
            except Exception as exc:
                self.sync_status.emit("GITHUB SYNC FAILED", False)
                self.sync_completed.emit(False, str(exc))

    def pull_and_restart(self) -> None:
        """
        Synchronously pulls latest commits from GitHub, updates dependencies in requirements.txt,
        and hot-restarts the running desktop process via os.execl.
        """
        git_dir = self.repo_root / ".git"
        if git_dir.exists():
            try:
                self._run_git(["fetch", "--all"])
                res = self._run_git(["pull", "--rebase", "--autostash"])
                if res.returncode != 0:
                    self._run_git(["reset", "--hard", "HEAD"])
                    res = self._run_git(["pull", "origin", "main"])
                    if res.returncode != 0:
                        self._run_git(["pull", "origin", "master"])

                req_file = self.repo_root / "requirements.txt"
                if req_file.exists():
                    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
                        cwd=str(self.repo_root),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=60,
                        creationflags=creationflags,
                    )
            except Exception:
                pass

        os.execl(sys.executable, sys.executable, *sys.argv)
