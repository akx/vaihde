from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from vaihde.excs import VaihdeError
from vaihde.ops import get_git_root


@dataclass
class PostCommand:
    run: str
    shell: bool = False


@dataclass
class VaihdeConfig:
    worktree_root: Path
    copy_files: list[str] = field(default_factory=list)
    post_commands: list[PostCommand] = field(default_factory=list)


def mangle_path(path: Path) -> str:
    """Convert a path to a config filename.

    /Users/akx/build/foo -> Users__akx__build__foo.toml
    """
    path = path.resolve()
    path_str = str(path).lstrip("/").replace("/", "__")
    return f"{path_str}.toml"


def get_global_config_path(git_root: Path) -> Path:
    return Path.home() / ".config" / "vaihde" / mangle_path(git_root)


def get_local_config_path(git_root: Path) -> Path:
    return git_root / "vaihde.toml"


def find_config(start_dir: Path | None = None) -> Path | None:
    """Locate config file.

    Priority:
    1. vaihde.toml in git repository root
    2. ~/.config/vaihde/<mangled-git-root>.toml
    """

    if start_dir is None:
        start_dir = Path.cwd()
    start_dir = start_dir.resolve()

    try:
        git_root = get_git_root(start_dir)
    except VaihdeError:
        return None

    # Check for global config (keyed by git root path)
    global_config = get_global_config_path(git_root)
    if global_config.exists():
        return global_config

    # Check for local config in git root
    local_config = get_local_config_path(git_root)
    if local_config.exists():
        return local_config

    return None


def load_config(path: Path) -> VaihdeConfig:
    """Parse TOML config and return VaihdeConfig."""
    data = tomllib.loads(path.read_text())

    # Validate required fields
    if "worktree_root" not in data:
        raise VaihdeError(f"Missing required 'worktree_root' in {path}")

    worktree_root = Path(data["worktree_root"]).expanduser().resolve()

    # Parse optional copy files
    copy_files: list[str] = data.get("copy", {}).get("files", [])

    # Parse optional post commands
    post_commands: list[PostCommand] = []
    for cmd_data in data.get("post_commands", []):
        if "run" not in cmd_data:
            raise VaihdeError(f"Post command missing 'run' field in {path}")
        post_commands.append(
            PostCommand(
                run=cmd_data["run"],
                shell=cmd_data.get("shell", False),
            ),
        )

    return VaihdeConfig(
        worktree_root=worktree_root,
        copy_files=copy_files,
        post_commands=post_commands,
    )
