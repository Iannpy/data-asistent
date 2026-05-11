# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| implementation, commit splitting, chained PRs, or keeping tests and docs with code | work-unit-commits | C:\Users\DELL\.config\opencode\skills\work-unit-commits\SKILL.md |
| PR feedback, issue replies, reviews, Slack messages, or GitHub comments | comment-writer | C:\Users\DELL\.config\opencode\skills\comment-writer\SKILL.md |
| writing guides, READMEs, RFCs, onboarding, architecture, or review-facing docs | cognitive-doc-design | C:\Users\DELL\.config\opencode\skills\cognitive-doc-design\SKILL.md |
| PRs over 400 lines, stacked PRs, or review slices | chained-pr | C:\Users\DELL\.config\opencode\skills\chained-pr\SKILL.md |
| creating GitHub issues, bug reports, or feature requests | issue-creation | C:\Users\DELL\.config\opencode\skills\issue-creation\SKILL.md |
| creating, opening, or preparing PRs for review | branch-pr | C:\Users\DELL\.config\opencode\skills\branch-pr\SKILL.md |
| new skills, agent instructions, or documenting AI usage patterns | skill-creator | C:\Users\DELL\.config\opencode\skills\skill-creator\SKILL.md |
| Go test coverage, teatest, or test patterns | go-testing | C:\Users\DELL\.config\opencode\skills\go-testing\SKILL.md |
| judgment day, dual review, adversarial review, or juzgar requests | judgment-day | C:\Users\DELL\.config\opencode\skills\judgment-day\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### work-unit-commits
- Commit by work unit — each commit represents a deliverable behavior, fix, migration, or docs unit
- Do NOT commit by file type — avoid "add models", then "add services" if none works alone
- Keep tests with code — tests belong in the same commit as the behavior they verify
- Keep docs with user-visible change — docs belong with the feature they explain
- Tell a story — a reviewer should understand why each commit exists from its diff and message
- Future PR-ready — each commit should be a candidate chained PR when the change grows

### comment-writer
- Be useful fast — start with the actionable point, do not recap the whole PR first
- Be warm and direct — sound like a thoughtful teammate, not a corporate bot
- Keep it short — prefer 1 to 3 short paragraphs or a tight bullet list
- Explain why — give the technical reason when asking for a change
- Avoid pile-ons — comment on the highest-value issue, not every tiny preference
- Match thread language — write in the thread/user language (use Rioplatense Spanish/voseo if Spanish)

### cognitive-doc-design
- Lead with the answer — put the decision, action, or outcome first; context comes after
- Progressive disclosure — start with happy path, then add details, edge cases, references
- Chunking — group related information into small sections; keep flat lists short
- Signposting — use headings, labels, callouts, and summaries so readers know where they are
- Recognition over recall — prefer tables, checklists, examples, and templates over prose
- Review empathy — design docs so reviewers can verify intent without reconstructing the story

### chained-pr
- Split PRs that exceed 400 changed lines (additions + deletions)
- Target ~60 minutes or less per PR for healthy review cognitive load
- Each PR in the chain must be independently testable and mergeable
- Use stacked PRs when dependencies exist between review slices
- Always link the issue being resolved to each PR

### issue-creation
- Blank issues are disabled — MUST use a template (bug report or feature request)
- Every issue gets `status:needs-review` automatically on creation
- A maintainer MUST add `status:approved` before any PR can be opened
- Questions go to Discussions, not issues

### branch-pr
- Every PR MUST link an approved issue — no exceptions
- Every PR MUST have exactly one `type:*` label
- Automated checks must pass before merge is possible
- Blank PRs without issue linkage will be blocked by GitHub Actions

### skill-creator
- Include valid frontmatter (name, description, license, metadata)
- Document trigger conditions clearly in description
- Keep skill focused on one domain/topic
- Include Critical Rules section with actionable patterns

### go-testing
- Write tests first (TDD) when implementing new functionality
- Use table-driven tests for multiple input scenarios
- Test behavior, not implementation — mock only external dependencies
- Include benchmark tests for performance-critical code
- Run `go test -cover` to verify coverage; aim for >70% on new code

### judgment-day
- Run dual adversarial review — one agent argues for, another against
- Verify fixes against the original bug report scenario
- Check for edge cases and regression risks
- Require confidence > 0.8 before marking as resolved
- Document the verdict and reasoning for future reference

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| (no conventions detected) | — | Project is empty — no AGENTS.md, CLAUDE.md, .cursorrules, or GEMINI.md found |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.