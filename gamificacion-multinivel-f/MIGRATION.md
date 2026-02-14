# CSS Migration Notes

Date: 2026-02-14

Scope: `src/styles.css` token unification and global utility normalization with backward-compatible aliases.

## Tokens

Canonical tokens introduced:

- `--color-text`
- `--color-text-muted`
- `--color-text-inverse`
- `--color-accent`
- `--color-gold`
- `--color-success`
- `--color-warning`
- `--color-danger`
- `--color-surface-1`
- `--color-surface-2`
- `--color-surface-3`
- `--color-bg-primary`
- `--color-bg-secondary`

Legacy aliases kept temporarily (`/* @deprecated */` in `src/styles.css`):

- `--text-main` -> `--color-text`
- `--text-light` -> `--color-text`
- `--text-muted` -> `--color-text-muted`
- `--muted-light` -> `--color-text-muted`
- `--text-accent` -> `--color-accent`
- `--text-gold` -> `--color-gold`
- `--text-success` -> `--color-success`
- `--text-warning` -> `--color-warning`
- `--text-danger` -> `--color-danger`
- `--bg-primary` -> `--color-bg-primary`
- `--bg-secondary` -> `--color-bg-secondary`
- `--text-primary` -> `--color-text`
- `--accent-olive` -> `--color-accent`

## Class Migrations

- `.modal-primary-btn` -> `.btn-primary` (alias kept)
- `.badge-delivered` -> `.badge-active` (alias kept)
- `ring` family:
  - `.ring-soft` -> `.ring` (alias kept)
  - `.ring-gold` -> `.ring--gold` (alias kept)
  - `.ring-silver` -> `.ring--silver` (alias kept)
  - `.ring-bronze` -> `.ring--bronze` (alias kept)
- `progress` family standardized:
  - Base: `.progress`, `.progress__rail`, `.progress__fill`
  - Modifiers: `.progress--soft`, `.progress__fill--olive`, `.progress__fill--gold`
  - Legacy aliases kept:
    - `.progress-rail`
    - `.progress-rail-soft`
    - `.progress-base`
    - `.progress-fill-olive`
    - `.progress-cart`

## Opacity Consolidation

Canonical surface alpha levels:

- soft: `--alpha-surface-soft` (`0.90`)
- strong: `--alpha-surface-strong` (`0.95`)

Legacy near-duplicate utilities mapped:

- `.bg-sand-200-92` -> same output as `.bg-sand-200-90` (deprecated)
- `.via-cream-92` retained as deprecated alias

## Planned Alias Removal

Suggested cleanup window: remove deprecated aliases after all templates/components stop referencing them and one stable release cycle has passed.
