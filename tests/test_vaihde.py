from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vaihde.cli import run
from vaihde.config import get_global_config_path, get_local_config_path
from vaihde.excs import VaihdeError
from vaihde.ops import create_worktree, get_git_root


@pytest.fixture(params=["local", "global"])
def config_path_getter(request, tmp_path: Path, monkeypatch):
    """Fixture that provides config path getter for both local and global configs."""
    if request.param == "local":
        return get_local_config_path

    if request.param == "global":
        # For global config, we need to mock the home directory
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        return get_global_config_path

    raise ValueError("Invalid fixture parameter")


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary git repository and cd into it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    # Create initial commit (required for worktrees)
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(repo)
    return repo


def test_get_git_root(git_repo: Path, monkeypatch) -> None:
    assert get_git_root() == git_repo
    subdir = git_repo / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    assert get_git_root() == git_repo


def test_get_git_root_not_a_repo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(VaihdeError, match="Not a git repository"):
        get_git_root()


def test_create_worktree(git_repo: Path, tmp_path: Path) -> None:
    worktree_root = tmp_path / "worktrees"
    worktree_path = create_worktree(git_repo, worktree_root, "feature-branch")

    assert worktree_path == worktree_root / "feature-branch"
    assert worktree_path.exists()
    assert (worktree_path / "README.md").exists()


def test_create_worktree_branch_exists(git_repo: Path, tmp_path: Path) -> None:
    worktree_root = tmp_path / "worktrees"
    create_worktree(git_repo, worktree_root, "my-branch")

    # Use different target dir so directory check passes, but branch check fails
    worktree_root2 = tmp_path / "worktrees2"
    with pytest.raises(VaihdeError, match="Branch already exists: my-branch"):
        create_worktree(git_repo, worktree_root2, "my-branch")


def test_create_worktree_dir_exists(git_repo: Path, tmp_path: Path) -> None:
    worktree_root = tmp_path / "worktrees"
    worktree_root.mkdir(parents=True)
    (worktree_root / "existing").mkdir()

    with pytest.raises(VaihdeError, match="Worktree directory already exists"):
        create_worktree(git_repo, worktree_root, "existing")


def test_cli_new_no_config(git_repo: Path) -> None:
    result = run(["new", "feature"])
    assert result == 1


def test_cli_new_with_config(git_repo: Path, tmp_path: Path, config_path_getter) -> None:
    worktree_root = tmp_path / "worktrees"
    config = config_path_getter(git_repo)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'worktree_root = "{worktree_root}"')

    result = run(["new", "feature"])
    assert result == 0
    assert (worktree_root / "feature").exists()


def test_cli_new_with_copy_files(git_repo: Path, tmp_path: Path, config_path_getter) -> None:
    worktree_root = tmp_path / "worktrees"
    (git_repo / ".env").write_text("SECRET=123")
    config = config_path_getter(git_repo)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f"""\
worktree_root = "{worktree_root}"

[copy]
files = [".env"]
""")

    result = run(["new", "feature"])
    assert result == 0
    assert (worktree_root / "feature" / ".env").read_text() == "SECRET=123"


def test_cli_list(git_repo: Path, tmp_path: Path, config_path_getter) -> None:
    worktree_root = tmp_path / "worktrees"
    config = config_path_getter(git_repo)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'worktree_root = "{worktree_root}"')
    run(["new", "feature"])

    result = run(["list"])
    assert result == 0
