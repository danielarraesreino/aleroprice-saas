---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel (vendored locally, rules pinned)
  version: "1.0.0-local"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines (cópia local fixada)

Review files for compliance with the Web Interface Guidelines in `guidelines.md` (same folder).

**Local install note.** The upstream skill fetches its rules from a URL at every use. This copy does NOT:
the rules are pinned in `guidelines.md` (source: vercel-labs/web-interface-guidelines `command.md`,
see SOURCE.txt for the hash). Never fetch rules from the network during a review. To update the rules,
a human re-vendors the file.

## How It Works

1. Read `guidelines.md` in this folder.
2. Read the specified files (or ask the user which files/pattern).
3. Check against every rule; output findings in the terse `file:line` format described in the file.

## Adaptations for this project (Flask + Jinja, pt-BR)

- Rules written for React (`onChange`, hydration, `useState`) do not apply to Jinja templates; skip them.
- Copy rules are for English: in pt-BR use **sentence case** in headings and buttons (not Title Case) and
  keep `…` instead of `...`.
- Everything else (accessibility, focus, images with width/height, reduced motion, touch, safe areas,
  dark mode, performance) applies as written.
