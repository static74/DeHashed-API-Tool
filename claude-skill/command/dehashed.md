---
name: dehashed
description: Run a DeHashed v2 recon investigation — exposure sweep, credential lookup, or identity correlation. Outputs a flat xlsx.
argument-hint: "[target details — name, emails, phones, domains, addresses, etc.]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Skill
  - Task
---

<objective>
Kick off an investigation via the `dehashed-recon` skill. The skill handles:
credit-conscious query crafting, direct `/v2/search` API calls with pagination
and rate-limit safety, broad-then-prune post-processing (subagent optional),
and a flat xlsx deliverable on `~/Desktop/`.

The command does not re-implement the skill. It invokes it and passes the
target context through.
</objective>

<context>
Target: $ARGUMENTS
</context>

<process>

1. **Invoke the skill** via the Skill tool: `dehashed-recon`. Its `SKILL.md` contains the full workflow, grammar reference, and anti-patterns. Follow it exactly.

2. **If `$ARGUMENTS` is non-empty**, treat it as the user's target specification and begin the skill's step 2 (query craft) directly. Do not re-ask questions whose answers are already in `$ARGUMENTS`.

3. **If `$ARGUMENTS` is empty**, begin at the skill's step 1 (light intake). Ask at most three PI-style clarifying questions before firing any API call.

4. **Default query shape for "pull everything on a person"**: one single-field call per identifier, merged locally by entry `id`. Do not combine identifiers with `&` for exposure sweeps (that's AND — narrows to intersection, misses records that only carry one identifier). See the exposure-vs-correlation table in the skill.

5. **Always surface the remaining credit balance** after each API call and in the final report.

6. **Final deliverable** is a flat xlsx on the Desktop, named `linda-kost-recon-YYYYMMDD.xlsx`-style (swap the subject to match the investigation). Include the `_query` provenance column.

</process>

<notes>
- Grammar is verified: `&` is AND, space is HTTP 400. No more grammar guessing.
- Wildcards need ≥3 chars before the wildcard character and cannot lead.
- Regex on emails must split: `email:pattern&domain:example.com`.
- `database_name=source` is an origin filter and must be combined with another field.
- Password presence checks use the free `/v2/search-password` endpoint (no credits).
</notes>
