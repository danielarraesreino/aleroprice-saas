---
name: ui-quality-baseline
description: Enforces stack-agnostic UI quality defaults, checklist and audit for any project. Use when starting a project, building or reviewing screens, auditing an existing interface, or when the user wants to avoid rework on responsive, typography, states, accessibility or feedback. Triggers on quality baseline, UI checklist, audit interface, defaults de interface, validar qualidade, o que esta inadequado, checklist de UI.
---

# UI Quality Baseline

## Purpose

This skill defines the non-negotiable baseline for interface quality that must be applied to **any** project (known or unknown). It prevents the common rework cycle of vibe coding by making defaults explicit and checkable.

Principles are stack-agnostic. Only the implementation changes.

## When to activate

- Starting any new project or feature
- Building or modifying screens/components
- User asks to audit, validate or review UI quality
- User asks "what is inadequate" or "what is missing"
- Before considering any interface "done"

## Core Defaults (non-negotiable)

Every new screen or interactive component must be born with these:

### 1. Layout & Responsive
- Mobile-first
- Tested on mobile (≤480px), tablet and desktop
- No critical information only available on hover or desktop-only
- No unwanted horizontal scroll

### 2. Typography & Text Hierarchy
- Clear visual hierarchy (page title → section → body → secondary)
- Sufficient contrast (WCAG AA minimum)
- Body text readable on mobile (≥16px equivalent)
- Consistent spacing scale
- No orphan or "floating" text without hierarchy

### 3. Interface States (mandatory for interactive components)
- Loading
- Empty
- Error
- Success (when applicable)
- Disabled (when applicable)

### 4. Accessibility (minimum)
- Keyboard navigable
- Visible focus indicator
- Meaningful alt text on significant images
- Labels on form controls
- Information not conveyed by color alone

### 5. User Feedback
- Important actions have clear visual or textual response
- Error messages are understandable and actionable
- User is never left without knowing what happened

## Verifiable Checklist

Use this before marking any screen, component or feature as ready. Only mark complete when all applicable items pass:

**Layout**
- [ ] Works correctly on mobile (≤480px)
- [ ] Works correctly on tablet
- [ ] Works correctly on desktop
- [ ] No unwanted horizontal scroll
- [ ] Critical elements do not depend on hover

**Typography & Content**
- [ ] Clear visual hierarchy
- [ ] Adequate text contrast
- [ ] Readable on mobile
- [ ] Consistent spacing

**States**
- [ ] Loading state present
- [ ] Empty state present
- [ ] Error state present
- [ ] Disabled state (when applicable)

**Accessibility**
- [ ] Keyboard navigable
- [ ] Visible focus
- [ ] Images have alt when needed
- [ ] Forms have labels

**Feedback**
- [ ] Important actions give clear response
- [ ] Errors are understandable
- [ ] User is never left in the dark

**General**
- [ ] No obvious visual regression
- [ ] Behavior consistent with the rest of the project

## Audit Protocol (when user asks to validate or find inadequacies)

When asked to audit, review or report what is inadequate:

1. **Do not assume context.** If the project is unknown, work only with what is visible or provided. Never invent screens or features.
2. **Be specific and evidence-based.** Point to concrete problems, not vague opinions.
3. **Structure the report clearly:**
   - **Executive Summary:** Pass/fail breakdown across the 5 core dimensions and overall readiness.
   - **Critical Inadequacies (Blockers):** Direct violations causing broken layout (horizontal scroll, touch targets <44px), accessibility failures, missing form labels, or broken states.
   - **Usability & Ergonomic Debt:** Secondary contrast warnings, typography inconsistency, hover-only interactions, missing empty/loading states.
   - **Actionable Remediation Plan:** Exact files, components, and code changes needed to bring the interface up to baseline.
4. **Map every finding to the checklist categories** (Layout, Typography, States, Accessibility, Feedback).
5. **For known projects** (e.g. Corte 800 / Saraiva): respect existing architecture and design tokens. Report only real gaps against this baseline.
6. **For unknown projects**: apply pure baseline. Do not invent brand, stack or business rules.
7. End with a short prioritized recommendation list.

## Rules for vibe coding / generation

When generating or modifying UI under this skill:

1. Apply the Core Defaults automatically. Do not wait to be asked.
2. Never consider an interface ready without running the checklist mentally (or explicitly).
3. Prefer consistency over clever one-off solutions.
4. When speed conflicts with baseline quality, choose the baseline. Rework costs more.
5. These rules are independent of language or framework. Adapt only the implementation.

## Reference standards (gold baseline)

- Accessibility → WCAG 2.2 AA
- Usability research → Nielsen Norman Group + Steve Krug
- Practical UI craft → Refactoring UI (Wathan & Schoger)
- Mature public design systems → Material 3, Apple HIG, Shopify Polaris, Atlassian DS

## Integration notes

- Can be loaded together with project-specific skills (corte800-*, nilceia-*, etc.).
- This skill owns the **baseline quality gate**. Project skills own domain rules.
- When both are active, baseline quality is never waived.
