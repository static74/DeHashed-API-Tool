Here's the complete API reference document:

---

```markdown
# DeHashed API Reference

> **Base URL:** `https://api.dehashed.com`  
> **API Version:** v2  
> **Documentation Source:** https://app.dehashed.com/documentation/api

---

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Common Error Responses](#common-error-responses)
4. [Search API](#search-api)
   - [General Search](#general-search)
   - [Password Search](#password-search)
   - [Pagination](#pagination)
5. [Data Wells API](#data-wells-api)
6. [Monitoring API](#monitoring-api)
   - [Tasks](#tasks)
   - [Reports](#reports)
   - [Notification Channels](#notification-channels)
   - [Domains](#domains)
   - [Webhooks](#webhooks)
7. [WHOIS API](#whois-api)
   - [WHOIS Search](#whois-search)
   - [WHOIS History](#whois-history)
   - [Reverse WHOIS](#reverse-whois)
   - [WHOIS IP Search](#whois-ip-search)
   - [WHOIS MX Search](#whois-mx-search)
   - [WHOIS NS Search](#whois-ns-search)
   - [WHOIS Subdomain Scan](#whois-subdomain-scan)
   - [WHOIS Credits](#whois-credits)

---

## Authentication

All API requests (except Data Wells) require an API key passed via request header:

```
Dehashed-Api-Key: <your-api-key>
```

**Important notes:**
- You must refresh your API key at least once after a recent platform update if you haven't already.
- The old API has been fully deprecated and replaced with v2.
- API security is enforced via Cloudflare and additional technologies. Stick to supported endpoints and request patterns.

---

## Rate Limiting

- **Limit:** 10 requests per second per IP and API credential
- **Exceeded limit response:** HTTP `429`
- Consistent violations or proxy-based bypass attempts may result in account suspension.

```json
{ "error": "too many requests" }
```

---

## Common Error Responses

| Status Code | Description                            | Example Response                                             |
| ----------- | -------------------------------------- | ------------------------------------------------------------ |
| `400`       | Bad Request                            | `{"error": "issue with authentication"}`                     |
| `401`       | Unauthorized (no subscription/credits) | `{"error": "You need a search subscription and API credits to use the API, please purchase a search subscription."}` |
| `403`       | Forbidden (insufficient credits)       | `{"error": "Insufficient Credits"}`                          |
| `429`       | Too Many Requests                      | `{"error": "too many requests"}`                             |

---

## Search API

> Requires a search subscription and API credits.

### General Search

Search across DeHashed's databases with various filtering options.

**Endpoint:** `POST https://api.dehashed.com/v2/search`

**Headers:**
```
Dehashed-Api-Key: <your-api-key>
Content-Type: application/json
```

**Request Parameters:**

| Parameter  | Type    | Required | Default | Description                                    |
| ---------- | ------- | -------- | ------- | ---------------------------------------------- |
| `query`    | string  | Yes      | —       | Search query. See the Search Guide for syntax. |
| `page`     | integer | No       | `1`     | Page number for pagination.                    |
| `size`     | integer | No       | `100`   | Results per page (max: 10,000).                |
| `regex`    | boolean | No       | `false` | Enable regex matching.                         |
| `wildcard` | boolean | No       | `false` | Enable wildcard matching.                      |
| `de_dupe`  | boolean | No       | `false` | Remove duplicate results across sources.       |

**Notes:**
- Maximum pagination depth is 50,000 total results (`page × size ≤ 50,000`).
- `regex` and `wildcard` cannot both be `true` simultaneously.
- Result fields are omitted from the response if they are empty.

**Response:**

```json
{
  "balance": 100,
  "entries": [
    {
      "id": "5603802198",
      "email": ["test@example.com"],
      "ip_address": ["127.0.0.1"],
      "username": ["username@example.com"],
      "password": ["examplepassword"],
      "hashed_password": ["password:salt||passwordhash"],
      "name": ["name"],
      "dob": ["01/02/60"],
      "license_plate": ["123456"],
      "address": ["example address"],
      "phone": ["+18005551234"],
      "company": ["example company"],
      "url": ["url.com"],
      "social": ["social username"],
      "cryptocurrency_address": ["0xcryptocurrencyaddress"],
      "database_name": "Example Database Name",
      "raw_record": {
        "le_only": true,
        "unstructured": true
      }
    }
  ],
  "took": "179µs",
  "total": 5
}
```

**Python Example:**

```python
import requests

api_key = "<your-api-key>"

def v2_search(query: str, page: int, size: int, wildcard: bool, regex: bool, de_dupe: bool) -> dict:
    res = requests.post(
        "https://api.dehashed.com/v2/search",
        json={
            "query": query,
            "page": page,
            "size": size,
            "wildcard": wildcard,
            "regex": regex,
            "de_dupe": de_dupe,
        },
        headers={
            "Content-Type": "application/json",
            "Dehashed-Api-Key": api_key,
        }
    )
    return res.json()
```

---

### Password Search

Search for records associated with a specific password hash. **Free — does not require credits or a subscription.**

**Endpoint:** `POST https://api.dehashed.com/v2/search-password`

**Headers:**
```
Dehashed-Api-Key: <your-api-key>
Content-Type: application/json
```

**Request Parameters:**

| Parameter                | Type   | Required | Description                                 |
| ------------------------ | ------ | -------- | ------------------------------------------- |
| `sha256_hashed_password` | string | Yes      | SHA-256 hash of the password to search for. |

**Response:**

```json
{ "results_found": 1 }
```

**Python Example:**

```python
import requests
import hashlib

api_key = "<your-api-key>"

def get_sha256(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def v2_search_password(password: str) -> dict:
    sha256_hash = get_sha256(password)
    res = requests.post(
        "https://api.dehashed.com/v2/search-password",
        json={"sha256_hashed_password": sha256_hash},
        headers={
            "Content-Type": "application/json",
            "Dehashed-Api-Key": api_key,
        }
    )
    return res.json()
```

---

### Pagination

The search endpoint supports up to **50,000 total results per query**.

#### Quick Reference

| Parameter | Min  | Max             | Default |
| --------- | ---- | --------------- | ------- |
| `size`    | 1    | 10,000          | 100     |
| `page`    | 1    | `50,000 / size` | 1       |

#### Hard Limits

- `size` must be between 1 and 10,000. Requests outside this range are rejected immediately.
- Total results per query: `page × size ≤ 50,000`

| Size   | Maximum Page |
| ------ | ------------ |
| 10,000 | 5            |
| 5,000  | 10           |
| 1,000  | 50           |
| 500    | 100          |
| 100    | 500          |

#### Page Ordering Rules

**Within the first 10,000 results** (`page × size ≤ 10,000`): pages may be requested in any order — jump, repeat, or skip freely.

**Beyond the first 10,000 results** (deep pagination): pages must be fetched sequentially. To fetch page N, you must have already fetched page N−1 in the same session. You can navigate backward at any time as long as the session is still active.

#### Deep Pagination Sessions

- Deep pagination sessions expire after **10 minutes** of inactivity.
- If a session expires, restart pagination from page 1.
- Session state is encrypted in transit and at rest, and is automatically deleted on TTL expiry.

#### Pagination Error Reference

| HTTP Status | Error Message                                                | Cause                                                |
| ----------- | ------------------------------------------------------------ | ---------------------------------------------------- |
| `400`       | `size must be between 1 and 10000`                           | `size` is 0, negative, or > 10,000                   |
| `400`       | `page must be 1 or greater`                                  | `page` is 0 or negative                              |
| `400`       | `pagination limit exceeded`                                  | `page` exceeds max for the chosen `size`             |
| `400`       | `deep pagination error: pages must be fetched sequentially - please restart from page 1` | Deep page requested out of order, or session expired |
| `500`       | `issue with pagination state`                                | Transient error — retry the request                  |

---

## Data Wells API

Retrieve information about all data sources currently in DeHashed's system.

> **Free — no API key or subscription required.**

**Endpoint:** `GET https://api.dehashed.com/data-wells`

**Query Parameters:**

| Parameter | Type    | Required | Description                                                  |
| --------- | ------- | -------- | ------------------------------------------------------------ |
| `count`   | integer | No       | Number of results to return (`20` or `50`).                  |
| `page`    | integer | No       | Page of results to return.                                   |
| `sort`    | string  | No       | Sort field: `added`, `name`, `date`, `records`. Append `-ASC` for ascending order (default is descending). |

**Response:**

```json
{
  "next_page": true,
  "total": 20000,
  "data_wells": [
    {
      "data": "name,email,address,username",
      "date": "2025-03-01",
      "description": "Description of breach.",
      "name": "Breach Name",
      "records": 500000,
      "is_sensitive": false
    }
  ]
}
```

**Example Requests:**

```
GET https://api.dehashed.com/data-wells?sort=name-ASC&page=1&count=20
GET https://api.dehashed.com/data-wells?sort=records-DESC&page=2&count=50
GET https://api.dehashed.com/data-wells?sort=added-ASC&page=1&count=20
GET https://api.dehashed.com/data-wells?sort=date-DESC&page=1&count=20
```

---

## Monitoring API

Set up and manage monitoring tasks to receive notifications when new data matching your criteria is found.

**Common Headers (all Monitoring endpoints):**
```
Dehashed-Api-Key: <your-api-key>
Content-Type: application/json
```

---

### Tasks

#### Create Task

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/create-task`

| Parameter | Type   | Required | Description                                   |
| --------- | ------ | -------- | --------------------------------------------- |
| `type`    | string | Yes      | `email`, `username`, `phone`, or `name`       |
| `value`   | string | Yes      | The value to monitor (e.g., an email address) |

**Response:** `{ "success": true }`

---

#### Update Task

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/update-task`

| Parameter | Type    | Required | Description                             |
| --------- | ------- | -------- | --------------------------------------- |
| `id`      | string  | Yes      | ID of the task to update                |
| `type`    | string  | Yes      | `email`, `username`, `phone`, or `name` |
| `value`   | string  | Yes      | The new value to monitor                |
| `active`  | boolean | No       | Task active status                      |

**Response:** `{ "success": true }`

---

#### Update Task Active Status

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/update-task`

| Parameter | Type    | Required | Description                               |
| --------- | ------- | -------- | ----------------------------------------- |
| `id`      | string  | Yes      | ID of the task to update                  |
| `active`  | boolean | Yes      | `true` to activate, `false` to deactivate |

**Response:** `{ "success": true }`

---

#### Delete Task

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/delete-task`

| Parameter | Type   | Required | Description              |
| --------- | ------ | -------- | ------------------------ |
| `id`      | string | Yes      | ID of the task to delete |

**Response:** `{ "success": true }`

---

#### Get Tasks

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/get-tasks`

| Parameter | Type    | Required | Description              |
| --------- | ------- | -------- | ------------------------ |
| `page`    | integer | No       | Page number (default: 1) |

**Response:**

```json
{
  "tasks": [
    {
      "id": "task_id",
      "type": "email",
      "value": "example@example.com",
      "active": true,
      "created": "2023-01-01T12:00:00.000000Z",
      "updated": "2023-01-01T12:00:00.000000Z"
    }
  ],
  "total": 1,
  "active": 1,
  "inactive": 0,
  "max": 10,
  "next_page": false
}
```

---

#### Get Task

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/get-task`

| Parameter | Type   | Required | Description                |
| --------- | ------ | -------- | -------------------------- |
| `id`      | string | Yes      | ID of the task to retrieve |

**Response:**

```json
{
  "type": "email",
  "value": "example@example.com",
  "active": true,
  "created": "2023-01-01T12:00:00.000000Z",
  "updated": "2023-01-01T12:00:00.000000Z"
}
```

---

### Reports

#### Get Reports

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/get-reports`

| Parameter | Type    | Required | Description              |
| --------- | ------- | -------- | ------------------------ |
| `page`    | integer | No       | Page number (default: 1) |

**Response:**

```json
{
  "reports": [
    {
      "id": "report_id",
      "timestamp": "2023-01-01T12:00:00.000000Z"
    }
  ],
  "next_page": false
}
```

---

#### Get Report

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/get-report`

| Parameter | Type   | Required | Description                  |
| --------- | ------ | -------- | ---------------------------- |
| `id`      | string | Yes      | ID of the report to retrieve |

**Response:**

```json
{
  "tasks": [
    {
      "id": "reference_id",
      "key": "task-key",
      "value": "task-value",
      "results_count": 1,
      "timestamp": "2023-01-01T12:00:00.000000Z",
      "results": [
        {
          "id": "result_id",
          "email": ["test@example.com"],
          "ip_address": ["127.0.0.1"],
          "username": ["username@example.com"],
          "password": ["examplepassword"],
          "hashed_password": ["password:salt||passwordhash"],
          "name": ["name"],
          "dob": ["01/02/60"],
          "license_plate": ["123456"],
          "address": ["example address"],
          "phone": ["+18005551234"],
          "company": ["example company"],
          "url": ["url.com"],
          "social": ["social username"],
          "cryptocurrency_address": ["0xcryptocurrencyaddress"],
          "database_name": "Example Database Name",
          "raw_record": {
            "le_only": true,
            "unstructured": true
          }
        }
      ]
    }
  ]
}
```

> **Note:** Result fields are omitted from the response if they are null.

---

### Notification Channels

Available channel types: `webhook`, `email`

#### Get Channels

**Endpoint:** `GET https://api.dehashed.com/v2/monitoring/get-channels`

No request body required.

**Response:**

```json
{
  "channels": [
    {
      "id": "channel_id",
      "type": "webhook",
      "value": "https://example.com/webhook",
      "updated_at": "2023-01-01T12:00:00.000000Z"
    }
  ]
}
```

> Response will be empty if no active notification channels are configured.

---

#### Update Channel

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/update-channel`

| Parameter | Type   | Required | Description                              |
| --------- | ------ | -------- | ---------------------------------------- |
| `type`    | string | Yes      | `webhook` or `email`                     |
| `value`   | string | Yes      | URL for webhook, email address for email |

**Response:** `{ "success": true }`

---

#### Delete Channel

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/delete-channel`

| Parameter | Type   | Required | Description                                  |
| --------- | ------ | -------- | -------------------------------------------- |
| `channel` | string | Yes      | Channel type to delete: `webhook` or `email` |

**Response:** `{ "success": true }`

---

### Domains

#### Get Domains

**Endpoint:** `GET https://api.dehashed.com/v2/monitoring/get-domains`

No request body required.

**Response:**

```json
{
  "domains": [
    {
      "id": "domain_id",
      "domain": "example.com",
      "updated": "2023-01-01T12:00:00.000000Z"
    }
  ]
}
```

---

#### Update Domain

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/update-domain`

| Parameter | Type   | Required | Description                                                  |
| --------- | ------ | -------- | ------------------------------------------------------------ |
| `id`      | string | Yes      | ID of the domain to update                                   |
| `domain`  | string | Yes      | New domain value (format: `example.com` — no `http://` or `https://`) |

**Response:** `{ "success": true }`

---

#### Clear Domain

Resets a domain monitoring task.

**Endpoint:** `POST https://api.dehashed.com/v2/monitoring/clear-domain`

| Parameter | Type   | Required | Description               |
| --------- | ------ | -------- | ------------------------- |
| `id`      | string | Yes      | ID of the domain to clear |

> **Note:** To unsubscribe from a domain or reduce your subscribed domain count, use the Subscriptions page on the website — this cannot be done via the API.

**Response:** `{ "success": true }`

---

### Webhooks

When a new monitoring report is generated, the service sends a `POST` request to your configured webhook URL with the following payload:

```json
{ "id": "report_id" }
```

Use this `id` to retrieve the full report via [Get Report](#get-report).

---

## WHOIS API

All WHOIS search operations share the same endpoint, differentiated by the `search_type` field.

**Common Headers:**
```
Dehashed-Api-Key: <your-api-key>
Content-Type: application/json
```

---

### WHOIS Search

Look up WHOIS registration information for a domain.

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter     | Type   | Required | Description                             |
| ------------- | ------ | -------- | --------------------------------------- |
| `search_type` | string | Yes      | Must be `"whois"`                       |
| `domain`      | string | Yes      | Domain to look up (e.g., `example.com`) |

---

### WHOIS History

Look up historical WHOIS records for a domain.

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter     | Type   | Required | Description                             |
| ------------- | ------ | -------- | --------------------------------------- |
| `search_type` | string | Yes      | Must be `"whois-history"`               |
| `domain`      | string | Yes      | Domain to look up (e.g., `example.com`) |

> **Cost:** 25 credits per search.

---

### Reverse WHOIS

Look up domains matching specific WHOIS parameters.

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter      | Type     | Required | Description                                  |
| -------------- | -------- | -------- | -------------------------------------------- |
| `search_type`  | string   | Yes      | Must be `"reverse-whois"`                    |
| `include`      | string[] | No       | Terms to include in search (max: 4)          |
| `exclude`      | string[] | No       | Terms to exclude from search (max: 4)        |
| `reverse_type` | string   | No       | `current` or `historic` (default: `current`) |

> **Note:** At least one term must be present in either `include` or `exclude`.

---

### WHOIS IP Search

Look up WHOIS information for an IP address.

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter     | Type   | Required | Description                             |
| ------------- | ------ | -------- | --------------------------------------- |
| `search_type` | string | Yes      | Must be `"reverse-ip"`                  |
| `domain`      | string | Yes      | IP address to look up (e.g., `8.8.8.8`) |

---

### WHOIS MX Search

Look up WHOIS information for a mail exchange (MX) server.

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter     | Type   | Required | Description                                   |
| ------------- | ------ | -------- | --------------------------------------------- |
| `search_type` | string | Yes      | Must be `"reverse-mx"`                        |
| `domain`      | string | Yes      | MX address to look up (e.g., `mx.google.com`) |

---

### WHOIS NS Search

Look up WHOIS information for a nameserver (NS).

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter     | Type   | Required | Description                                   |
| ------------- | ------ | -------- | --------------------------------------------- |
| `search_type` | string | Yes      | Must be `"reverse-ns"`                        |
| `domain`      | string | Yes      | NS address to look up (e.g., `ns.google.com`) |

---

### WHOIS Subdomain Scan

Find subdomains for a given domain using WHOIS data.

**Endpoint:** `POST https://api.dehashed.com/v2/whois/search`

| Parameter     | Type   | Required | Description                         |
| ------------- | ------ | -------- | ----------------------------------- |
| `search_type` | string | Yes      | Must be `"subdomain-scan"`          |
| `domain`      | string | Yes      | Domain to scan (e.g., `google.com`) |

---

### WHOIS Credits

Check your remaining WHOIS credit balance.

**Endpoint:** `GET https://api.dehashed.com/v2/whois/credits`

No request body required.

**Response:**

```json
{ "whois_credits": 1 }
```

**Python Example:**

```python
import requests

api_key = "<your-api-key>"

def whois_credits() -> dict:
    res = requests.get(
        "https://api.dehashed.com/v2/whois/credits",
        headers={"Dehashed-Api-Key": api_key}
    )
    return res.json()
```
```

---

That's the full reference document. A few things worth noting for your dev work:

- **The example API key in the docs is a placeholder** — replace it with your actual key wherever you use it.
- The `search_type` field on WHOIS endpoints is what determines which lookup is performed — all six WHOIS operations hit the same `POST /v2/whois/search` endpoint.
- Deep pagination (past 10,000 results) requires sequential page fetching and sessions expire after 10 minutes, so keep that in mind if you're building a bulk data retrieval flow.
- Password search is completely free and doesn't touch your credit balance — useful for lightweight exposure checks.