---
name: dehashed-recon
description: Investigative skill for querying the DeHashed v2 Search API efficiently, built for security researchers and PI-style OSINT work. Use this skill whenever the user asks about DeHashed, breach data lookups, credential exposure, compromised accounts, dark web exposure, email/username/domain/phone/IP reconnaissance, OSINT enrichment, or any investigative task where the goal is "who or what is associated with this identifier" from breach databases. Also trigger when the user mentions their `dat` or `dehashapitool` CLI, or references `~/git/DeHashed-API-Tool`. The skill builds broad single-call queries to conserve API credits, then prunes and normalizes results locally, and exports a flat xlsx report.
---

# DeHashed Recon

A credit-conscious, investigation-first workflow for the DeHashed v2 Search API. You craft one wide query per investigation, pull results in a single paginated call, prune/normalize locally, and produce a flat xlsx report.

## Why this skill exists

DeHashed charges API credits per call to `/v2/search`. Naive investigations (one call per field, one call per target) burn credits fast. An experienced investigator crafts **one broad query** that captures the full population of interest, pages through it once, and does narrowing work **locally** against the returned rows.

This is the "broad then prune" pattern. It trades a slightly larger payload for dramatic credit savings. The skill defaults to this pattern and only reaches for multiple API calls when the investigation genuinely needs them (e.g., two truly unrelated targets).

## When to activate

Trigger on any of these cues, even if DeHashed is not mentioned by name:
- Breach / credential / password exposure checks on a person, email, domain, username, phone, or IP
- "What do we know about [target]" investigative framing
- Domain-wide credential inventory ("all exposed creds for acme.com")
- Correlation tasks ("is this phone number tied to this email?")
- Explicit mentions: `dat`, `dehashapitool`, DeHashed, `/v2/search`, `api.dehashed.com`, the repo at `~/git/DeHashed-API-Tool`

If the request is about the **CLI behavior itself** (bugs, flags, install), that's a code task — don't use this skill; read `run.py` directly.

## Workflow

### 1. Light intake (ask only when ambiguous)

The user is probably a security researcher or investigator. Don't interrogate them. Ask only what you need to write a good query. Skip any question whose answer is obvious from the request.

Typical questions worth asking, in rough priority:

1. **Target scope.** Is this one identifier (email/domain/phone), a small set, or a broad sweep (e.g., everything at a domain)? This determines query shape.
2. **Intent.** Credential exposure report? Identity correlation? Monitoring setup? This shapes what to prune and keep in the xlsx.
3. **Known aliases or adjacent identifiers** if correlation is the goal (e.g., "also check these two variants"). Often the user already has these in their head and mentioning them up front saves a second call.

Three questions is the ceiling. One is often enough. If the request is clear ("pull all creds for acme.com"), just go.

Tone: professional, terse, PI-style. You are not a chatbot asking "would you like fries with that"; you are a colleague triaging a case.

### 2. Craft the query

Consult `references/query-syntax.md` for the authoritative grammar. The critical grammar facts:
- `&` joins fields as logical **AND** (narrows). Space-separation returns HTTP 400.
- Single field: `field:"value"` (quotes for values with spaces; domains unquoted).
- Field names: `email`, `username`, `password`, `hashed_password`, `ip_address`, `name`, `phone`, `address`, `domain`, `dob`, `vin`, `license_plate`, `company`, `url`, `social`, `cryptocurrency_address`.

Defaults to use unless the user specifies otherwise:
- `size=10000` (the API maximum per page — fewer pages = fewer calls = fewer credits)
- `de_dupe=true` when the user wants unique entries; `false` when they want raw source records (better for auditing where data came from)
- `wildcard=false` and `regex=false` unless needed; the two are mutually exclusive

#### Query shape: exposure vs. correlation

This is the single most important decision in the skill. Pick the right shape first, every time.

| Intent | Query shape | Example |
|---|---|---|
| **Exposure sweep** on a person ("pull everything tied to Linda Kost") | One **single-field** query per identifier, merged locally by entry `id`. | 3 calls: `email:"x"`, `email:"y"`, `phone:"z"`. |
| **Exposure sweep** on a population with a shared surface ("all exposed creds for acme.com") | One **broad-field** query. | 1 call: `domain:acme.com`. |
| **Correlation / intersection** ("records where this email AND this phone both appear") | One **`&`-AND** query. | 1 call: `email:"x"&phone:"y"`. |

The trap: combining a person's identifiers with `&` looks credit-efficient but produces the correlation set, not the exposure set. You lose every record that only carries one of the identifiers. For a 3-identifier person, running 3 single-field calls is the correct exposure path.

**Credit-saving patterns that still apply:**
- If the user supplies 20 emails at the same domain, query the domain once and filter locally. The domain is the broad surface.
- Don't re-query the same field separately when one call covers it (e.g., `domain:acme.com&password:*` and `domain:acme.com&phone:*` — just call `domain:acme.com` once and split locally).
- Use `database_name=<source>` as a filter when investigating a specific known breach. It must be combined with another field (cannot be the only parameter).

### 3. Execute

Use the bundled script:

```bash
python3 <skill-dir>/scripts/dehashed_query.py \
  --query 'domain:acme.com' \
  --size 10000 \
  --output /tmp/dehashed-<case>.json
```

Key discovery order (automatic, no flag needed):
1. `DEHASHED_API_KEY` environment variable
2. `config.txt` inside the installed `dehashapitool` package (resolves via `import dehashapitool`)
3. Interactive prompt as last resort

The script paginates automatically, respects the 0.1s rate-limit courtesy sleep, and prompts before exceeding 25 calls (use `--yes` to pre-approve). It prints the remaining credit balance at the end. Always surface that number back to the user.

If the query uses boolean operators or advanced syntax, run a probe first:

```bash
python3 <skill-dir>/scripts/dehashed_query.py \
  --query '(domain:acme.com OR domain:acme.io) AND NOT username:noreply*' \
  --probe
```

A probe returns a single result (or confirms syntactic validity) at minimal cost. If the probe returns a 400, rework the query before paginating.

### 4. Prune and normalize

Two paths depending on result size:

**Small result set (<100 rows)**: filter directly in the final xlsx step or inspect inline. No subagent needed.

**Large result set (>100 rows, or investigation has non-obvious filtering criteria)**: spawn a subagent to read the JSON, apply investigation-specific pruning, and write a trimmed JSON the xlsx step consumes.

Dispatch the subagent with clear instructions anchored to the investigation intent captured during intake. Example:

> Read `/tmp/dehashed-acme.json`. The investigation goal is identifying exposed credentials for current Acme employees (not third-party partners, not expired test accounts). Prune entries where: (a) the email domain is not acme.com or a known Acme subsidiary (acme.io, acme-labs.com), (b) the username matches test/noreply/automated patterns, (c) the raw_record flags the source as `le_only`. Write the kept entries to `/tmp/dehashed-acme-pruned.json`. Report counts: kept, dropped, and the reason categories for drops.

The judgment on when to use a subagent is yours. Threshold of 100 is a guideline, not a rule — a 50-row set with tricky inclusion criteria is also a subagent case; a 500-row set with a trivial filter (domain equals X) is not.

### 5. Export to xlsx

```bash
python3 <skill-dir>/scripts/to_xlsx.py \
  --input /tmp/dehashed-acme-pruned.json \
  --output ~/Desktop/acme-exposure-$(date +%Y%m%d).xlsx
```

Output is flat: one sheet, one row per entry, columns limited to those actually populated. List-valued fields (email, username, etc. come back as arrays from the API) are joined with commas so a human can read the sheet without unpacking nested data.

### 6. Report back

Report to the user with:
- Credit balance remaining (from the API response)
- Row count (raw / kept / dropped if pruning ran)
- Path to the xlsx
- Any notable findings you observed in passing (a specific breach source repeated, a pattern of reused passwords, unexpected domains in the results) — investigators want the signal, not just the file

Keep the summary terse. Two or three sentences. The xlsx is the deliverable.

## Anti-patterns (things not to do)

- **Don't combine identifiers with `&` for exposure sweeps on a person.** That's AND and narrows to the intersection. For "pull everything on Linda," fan out one call per identifier and merge by `id`. See the exposure-vs-correlation table above.
- **Don't fan out when a broad field covers the set.** If the user has 20 emails at the same domain, query the domain once. The fan-out rule applies across dimensions (email + phone + username), not within one (20 emails at one domain).
- **Don't paginate the full 50k without a reason.** If the user wants a summary, `size=10000 page=1` is usually enough. Only go deep when `total` indicates it.
- **Don't skip the credit balance.** Every run, surface the balance. Credit visibility is a safety net.
- **Don't probe grammar that's already documented.** `&` is AND, space is invalid. These are verified. Only probe when exploring something genuinely undocumented.
- **Don't over-ask.** The user already knows who they're chasing. One or two clarifying questions is the ceiling when the ask is ambiguous. Otherwise just run.

## Files in this skill

- `SKILL.md` — this file; workflow and intake guidance
- `scripts/dehashed_query.py` — direct API caller with pagination, safety prompts, key discovery
- `scripts/to_xlsx.py` — JSON-to-xlsx flattener
- `references/query-syntax.md` — query grammar reference, verified vs. unverified features, credit-saving patterns
