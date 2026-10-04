# Task 001 — Environment Preflight

## Goal
Verify the Codex Cloud or CI environment before any platform implementation.

## Required output
Create reports/environment-preflight.md containing OS/architecture, CPU/memory/disk, Git/Python/Node/Java/package-manager versions, network restrictions, build command availability, Git status, version pins, and commands passed/failed.

## Acceptance
- ./scripts/preflight.sh executed
- no version pin changed
- no secret printed
- environment limitations explicitly recorded
