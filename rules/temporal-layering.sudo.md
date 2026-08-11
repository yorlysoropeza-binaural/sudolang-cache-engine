# Temporal Layering — SudoLang Constraints

You enforce strict temporal separation in all generated content.

## Forbidden in Frente Estable

NEVER include these in the cache-stable prefix:
- Current date/time (`2026-08-09`, `now()`)
- UUIDs or random identifiers
- File hashes or checksums
- User-specific paths (`/home/user/...`)
- Session IDs or request IDs
- Any value from `datetime.now()`, `uuid4()`, `os.urandom()`

## Required in Fondo Volátil

ALWAYS push these to the dynamic suffix:
- Timestamps and dates
- Hashes and checksums
- User input verbatim
- File paths and names
- Execution results
- Error messages
- Cache metadata (TTL, hit count)

## Pattern: Stable Schema + Dynamic Data

```markdown
## Response Schema (STABLE — never changes)
All responses MUST contain:
- `status`: "success" | "error" | "partial"
- `data`: structured payload
- `metadata`: { timestamp, cache_hit, ttl_remaining }

## Current Response (DYNAMIC — changes each turn)
- timestamp: {{CURRENT_TIME}}
- cache_hit: {{HIT_OR_MISS}}
- ttl_remaining: {{TTL_SECONDS}}
```

## Anti-Pattern Detection

Scan generated content for cache pollution:
- If you find a date/time in the first 80% → MOVE to Fondo Volátil
- If you find a UUID in the first 80% → MOVE to Fondo Volátil
- If you find a file path in the first 80% → MOVE to Fondo Volátil
- If you find user input in the first 80% → MOVE to Fondo Volátil
