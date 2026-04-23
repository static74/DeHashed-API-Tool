# DeHashed v2 Query Syntax Reference

Sourced from the DeHashed official search guide. Verified against live API behavior
during skill development. When in doubt, consult the authoritative guide at
`https://app.dehashed.com/documentation/search-guide` (auth-walled).

## Field matching

Syntax: `{fieldname}:{value}`

Examples:
- `username:example123`
- `email:example@example.com`
- `name:"john smith"` — **quotes required** for values with spaces
- `ip_address:127.0.0.1`
- `domain:example.com` — do not quote domain values
- `phone:"+18005551234"` or `phone:"8005551234"`

Field names confirmed in the API response schema and the search guide:
`email`, `username`, `password`, `hashed_password`, `ip_address`, `name`, `phone`,
`address`, `domain`, `dob`, `vin`, `license_plate`, `company`, `url`, `social`,
`cryptocurrency_address`, `raw_record`.

## Combining fields — `&` is AND

Multiple `field:value` pairs joined with `&` combine as a logical **AND** — each
additional filter narrows the result set. Verified empirically during Linda Kost
recon: `email:"lkost@realtymetrix.com"&phone:"8479108820"` returned 2 records,
whereas `phone:"8479108820"` alone returned 8. The `&` narrowed, not widened.

Examples from the official guide:
- `email:example@example.com&username:test` — records matching **both** email and username
- `email:example@example.com&username:test&database_name=collections` — narrowed further by source
- `username:example&email:example@example.com&name:"john smith"&ip_address:127.0.0.1&database_name=collections` — complex multi-field AND

**Space-separated fields are rejected with HTTP 400 "Issue with query format".**
Use `&`.

### Implication for investigations

This is the single most important distinction in the skill:

| Goal | Query shape | Why |
|---|---|---|
| **Exposure sweep** ("everything tied to this person") | Single-field queries, one per identifier, merged locally | Each identifier widens the net. Combining with `&` would intersect and miss records that only carry one identifier. |
| **Correlation** ("which records have both X and Y together?") | `field_a:X&field_b:Y` in one call | `&`-AND narrows to the intersection, which is what you want. |

When the user says "pull everything for this person," default to single-field per identifier and merge. A 3-identifier person is 3 calls — credit-cheap and exhaustive. Combining with `&` to save calls on exposure sweeps causes blind spots.

## Origin matching

`&database_name=<origin>` filters to a specific data source. Cannot be the only
parameter in a query.

Example: `example&database_name=collections`

Useful when chasing exposure from a specific known breach.

## Wildcards

Enable by setting `wildcard: true` in the POST body (`--wildcard` flag on the
query script). Characters: `?` (single char), `*` (multi-char).

Rules:
- Cannot appear at the **start** of a query (e.g., `name:*ohn` is invalid)
- Minimum **3 characters before** the wildcard (`name:joh*` is valid, `name:jo*` is not)
- Must be paired with a defined field
- Wildcards and regex **cannot mix** in the same query

Email wildcards must split into email + domain:
- `email:examp*&domain:example.com`
- `email:/joh?n(ath[oa]n)/&domain:hotmail.com`

Not: `email:examp*@example.com`

## Regex

Enable by setting `regex: true` in the POST body (`--regex` flag). Field prefix
required. No slashes needed around the pattern — the API wraps it.

Examples:
- `name:joh?n(ath[oa]n)`
- `username:example&email:example@example.com&name:[A-Za-z]&ip_address:127.0.0.1&database_name=collections` — regex on name combined with AND filters

Email regex must split: `email:joh?n(ath[oa]n)&domain:hotmail.com`.

## Password search

Prefer the hashed form over the plaintext form when looking up a password:
- `hashed_password:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8`
  (SHA256 of `"password"`)

DeHashed auto-hashes into MD5, SHA256, SHA512, and Base64 internally, so hashed
lookups find both hashed and plaintext storage matches. Computing the hash
client-side before calling is the recommended investigator pattern.

The separate `POST /v2/search-password` endpoint (not `/v2/search`) is **free**
for SHA256 presence checks — no credits consumed. Use it when the only question
is "has this password been seen at all?"

## Credit-saving patterns

### 1. Domain sweep beats email-by-email (for exposure on a company)

Bad (N calls):
```
for email in known_emails: query(f'email:"{email}"')
```

Good (1 call):
```
query('domain:acme.com')
# filter locally to the emails of interest
```

### 2. Single broad call + local prune beats narrow calls

Bad (3 calls, same records returned 3 times):
```
query('domain:acme.com&password:*')
query('domain:acme.com&phone:*')
query('domain:acme.com&hashed_password:*')
```

Good (1 call):
```
query('domain:acme.com')
# split result locally into cred / phone / hash sub-reports
```

### 3. Use `size=10000` by default

One page of 10,000 = one API call. Ten pages of 1,000 = ten calls. Credit cost
doesn't depend on size. Max the size, minimize the calls.

### 4. Pagination depth vs. credits

`page × size ≤ 50,000` is the hard cap. Within the first 10,000 results, pages
can be requested in any order. Past that, pagination is sequential with a
10-minute session TTL. For summary-style asks, page 1 at size=10000 is almost
always enough.

### 5. For exposure asks on a single person: one call per identifier

Don't combine identifiers with `&` (that's AND, narrows). One call per:
- Each known email
- Each known phone
- Each known username

Dedupe locally by entry `id`. See "Implication for investigations" above.

## Known gotchas

- **Response omits empty fields.** An entry without a phone won't have a `phone`
  key at all. The `to_xlsx.py` flattener handles this.
- **`le_only` flag** inside `raw_record` marks law-enforcement-only records.
  Surface this to the user; they may have access restrictions.
- **Deep pagination is session-bound.** Past 10,000 results, pages must be
  fetched sequentially within 10 minutes. The bundled script does not implement
  deep pagination; add a `--deep` mode if genuinely needed.
- **Header casing.** API docs use `Dehashed-Api-Key`; old CLI uses
  `DeHashed-Api-Key`. Both work. Bundled script uses the documented casing.
- **Grammar errors return HTTP 400** with `{"error": "Issue with query format"}`.
  No credit consumed on malformed queries, but the round trip still spends time.
