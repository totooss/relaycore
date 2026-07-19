# Decision: Surface Uncommitted Session State In Mission Control

Date: 2026-07-19
Phase: 11 Tests And Validation

## Decision

Mission Control should show an explicit warning when a session has not been committed with `memory_commit_task`.

The UI uses `session.metadata.last_commit_at` as the commit signal:

- If `last_commit_at` is missing, render `Uncommitted Session`.
- If `last_commit_at` exists, render the latest commit timestamp instead of the warning.

## Why

The MVP acceptance checklist requires operators to see when a session still has uncommitted state. Exposing this directly in the session detail view keeps the warning visible without expanding the API surface or adding new storage fields.

## Rejected Option

Infer commit state only from the presence of digests.

Rejected because digests can be created automatically from event volume, while `memory_commit_task` is the explicit operator/runtime action the MVP wants to surface.
