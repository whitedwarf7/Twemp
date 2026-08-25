# RelayOps workspace instructions

- [x] Verify this instruction file exists.
- [x] Clarify project requirements: Next.js App Router, TypeScript, Tailwind CSS, ESLint, npm, and a provider-neutral hierarchical agent workflow.
- [x] Scaffold the project in the current workspace.
- [ ] Customize the multi-agent incident-response workflow.
- [x] Install required editor extensions: none required by the selected setup.
- [ ] Compile and validate the project.
- [ ] Create a reusable VS Code task if needed.
- [ ] Launch only when requested.
- [ ] Complete project documentation.

## Engineering rules

- Use strict TypeScript and the `@/*` import alias.
- Keep the workflow engine independent from UI and transport concerns.
- Require explicit human approval before any remediation phase.
- Default to deterministic demo mode; live model calls must be opt-in.
- Never place secrets in client-side code, logs, fixtures, or traces.
- Validate all API boundaries and model outputs.
- Prefer small, focused modules and preserve existing project style.
- Run lint, tests, and a production build after changes.
