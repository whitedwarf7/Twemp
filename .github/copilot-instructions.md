# Twemp workspace instructions

- [x] Verify this instruction file exists.
- [x] Clarify project requirements: Next.js App Router, TypeScript, Tailwind CSS, ESLint, npm, and a provider-neutral hierarchical agent workflow.
- [x] Scaffold the project in the current workspace.
- [x] Customize the multi-agent incident-response workflow.
- [x] Install required editor extensions: none required by the selected setup.
- [x] Compile and validate the project with lint, typecheck, tests, production build, and browser checks.
- [x] Create a reusable VS Code task if needed: skipped because the npm scripts provide the complete workflow.
- [x] Launch only when requested: the temporary browser-validation server was stopped after testing.
- [x] Complete project documentation.

## Engineering rules

- The backend is FastAPI (Python) in `backend/`; the frontend is Next.js in `src/`.
- `backend/app/workflow/schemas.py` is the contract source of truth; keep `src/lib/workflow/schemas.ts` in sync.
- Use strict TypeScript with the `@/*` alias, and fully typed Python that passes strict mypy.
- Keep the workflow engine independent from UI and transport concerns.
- Require explicit human approval before any remediation phase.
- Default to deterministic demo mode; live model calls must be opt-in.
- Never place secrets in client-side code, logs, fixtures, or traces.
- Validate all API boundaries and model outputs.
- Prefer small, focused modules and preserve existing project style.
- After backend changes run ruff, mypy, and pytest; after frontend changes run `npm run validate`.
