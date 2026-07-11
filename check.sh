#!/usr/bin/env bash
set -e

run_check() {
    local name=$1
    shift

    printf '\n==> Running %s...\n' "$name"
    if "$@"; then
        printf '✓ %s passed\n' "$name"
    else
        local status=$?
        printf '✗ %s failed (exit %d)\n' "$name" "$status" >&2
        exit "$status"
    fi
}

run_check "Ruff" uv run ruff check .
run_check "Black" uv run black --check .
run_check "Pylint (source)" uv run pylint fsort/
run_check "Pylint (tests)" uv run pylint tests/
run_check "Mypy (source)" uv run mypy fsort/
run_check "Mypy (tests)" uv run mypy tests/
run_check "Pytest" uv run pytest

printf '\n✓ All checks passed.\n'
