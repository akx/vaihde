from __future__ import annotations

import logging
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from vaihde.excs import VaihdeError

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from vaihde.config import PostCommand


def get_git_root(path: Path | None = None) -> Path:
    """Find the git repository root."""
    if path is None:
        path = Path.cwd()

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise VaihdeError(f"Not a git repository: {path}") from e
    return Path(result.stdout.strip())


def _branch_exists(repo_root: Path, branch: str) -> bool:
    """Check if a branch exists."""
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
    )
    return result.returncode == 0


def create_worktree(repo_root: Path, target: Path, name: str) -> Path:
    """Create a new worktree with a new branch.

    Args:
        repo_root: The git repository root
        target: Directory where the worktree will be created
        name: Name for both the worktree directory and the new branch

    Returns:
        Path to the created worktree
    """
    worktree_path = target / name

    if worktree_path.exists():
        raise VaihdeError(f"Worktree directory already exists: {worktree_path}")
    if _branch_exists(repo_root, name):
        raise VaihdeError(f"Branch already exists: {name}")

    target.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            ["git", "worktree", "add", "-b", name, str(worktree_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise VaihdeError(f"Failed to create worktree: {e.stderr.strip()}") from e

    return worktree_path


def copy_files(src_dir: Path, dst_dir: Path, files: list[str]) -> None:
    """Copy files from src_dir to dst_dir. Warns but continues on failure."""
    for filename in files:
        src = src_dir / filename
        dst = dst_dir / filename
        try:
            if not src.exists():
                log.info("Skipping %s (not found in source)", filename)
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            log.debug("Copied %s", filename)
        except OSError as e:
            log.warning("Failed to copy %s: %s", filename, e)


def run_commands(cwd: Path, commands: list[PostCommand]) -> None:
    """Execute post-commands in the given directory.

    Reports failures but continues execution.
    """
    for cmd in commands:
        log.debug("Running: %s", cmd.run)
        args = cmd.run if cmd.shell else shlex.split(cmd.run)
        result = subprocess.run(
            args,
            cwd=cwd,
            shell=cmd.shell,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.warning("Command failed with exit code %d", result.returncode)
            if result.stderr:
                log.warning("  %s", result.stderr.strip())


def list_worktrees(repo_root: Path) -> None:
    """List all worktrees for the repository."""
    try:
        subprocess.run(["git", "worktree", "list"], cwd=repo_root, check=True)
    except subprocess.CalledProcessError as e:
        raise VaihdeError("Failed to list worktrees") from e
