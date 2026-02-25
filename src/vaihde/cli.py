from __future__ import annotations

import argparse
import logging

from vaihde.config import find_config, get_global_config_path, get_local_config_path, load_config
from vaihde.excs import VaihdeError
from vaihde.ops import (
    copy_files,
    create_worktree,
    get_git_root,
    list_worktrees,
    run_commands,
)

log = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a new worktree")
    new_parser.add_argument("name", help="Name for the worktree and branch")
    new_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    subparsers.add_parser("list", help="List worktrees")
    subparsers.add_parser("config-path", help="Show the global config path for this directory")
    subparsers.add_parser("init", help="Create a new config file interactively")

    return parser.parse_args(argv)


def cmd_new(name: str) -> int:
    """Create a new worktree with automation."""
    git_root = get_git_root()
    log.debug("Git root: %s", git_root)

    config_path = find_config()
    if config_path is None:
        global_path = get_global_config_path(git_root)
        log.error("No vaihde.toml config found")
        log.error("Create vaihde.toml in your git repo, or: %s", global_path)
        return 1

    log.debug("Using config: %s", config_path)
    config = load_config(config_path)

    log.debug("Creating worktree '%s' in %s", name, config.worktree_root)
    worktree_path = create_worktree(git_root, config.worktree_root, name)
    log.info("Created worktree: %s", worktree_path)

    if config.copy_files:
        log.debug("Copying files...")
        copy_files(git_root, worktree_path, config.copy_files)

    if config.post_commands:
        log.debug("Running post-commands...")
        run_commands(worktree_path, config.post_commands)

    return 0


def cmd_list() -> int:
    """List worktrees."""
    git_root = get_git_root()
    list_worktrees(git_root)
    return 0


def cmd_config_path() -> int:
    """Show the global config path for this repository."""
    print(get_global_config_path(get_git_root()))
    return 0


CONFIG_TEMPLATE = """\
# Vaihde configuration

# Root directory for new worktrees (required)
worktree_root = "{worktree_root}"

# Files to copy from the main worktree (optional)
# [copy]
# files = [".env", ".env.local"]

# Commands to run after creating a worktree (optional)
# [[post_commands]]
# run = "uv sync"
#
# [[post_commands]]
# run = "npm install"
# shell = true
"""


def cmd_init() -> int:
    """Create a new config file interactively."""
    git_root = get_git_root()
    local_path = get_local_config_path(git_root)
    global_path = get_global_config_path(git_root)

    existing = find_config()
    if existing:
        log.error("Config already exists: %s", existing)
        return 1

    print("Where should the config be created?")
    print(f"  [1] Local:  {local_path}")
    print(f"  [2] Global: {global_path}")
    choice = input("Choice [1]: ").strip()
    config_path = global_path if choice == "2" else local_path

    default_root = f"~/worktrees/{git_root.name}"
    worktree_root = input(f"Worktree root [{default_root}]: ").strip() or default_root

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(CONFIG_TEMPLATE.format(worktree_root=worktree_root))
    print(f"Created: {config_path}")
    return 0


def run(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    try:
        args = parse_args(argv)
        setup_logging(verbose=getattr(args, "verbose", False))

        if args.command == "new":
            return cmd_new(args.name)
        if args.command == "list":
            return cmd_list()
        if args.command == "config-path":
            return cmd_config_path()
        if args.command == "init":
            return cmd_init()
        log.error("Unknown command: %s", args.command)
        return 1

    except VaihdeError as e:
        log.error("Error: %s", e)
        return 1
    except KeyboardInterrupt:
        log.info("\nInterrupted")
        return 130
