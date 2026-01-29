# Vaihde – a Git worktree manager

(for instance, for wrangling your AI agents while retaining a sense of control)

## Installation

Easiest, probably, to go with `uv tool`:

```shell
uv tool install https://github.com/akx/vaihde.git
```

## Configuration

Configuration can live in your project in `vaihde.toml`,
or if you have friends who don't want to use Vaihde,
and you don't want to litter the repo,
you can also use a global per-repo config; see `vaihde config-path`.

Configuration can be initialized with `vaihde init`,
but here's an example nevertheless.

```toml
# Root for new worktrees (required)
worktree_root = "/tmp/vaihde-test-worktrees"

# Files to copy from canonical worktree (optional)
[copy]
files = [".env.example"]

# Commands to run in new worktree (optional)
# [[post_commands]]
# run = "uv sync"
```
