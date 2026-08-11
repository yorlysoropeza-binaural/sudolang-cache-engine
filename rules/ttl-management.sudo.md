# TTL Management — SudoLang Constraints

You manage cache TTL (Time-To-Live) based on subscription tier.

## TTL Rules

| Subscription | TTL | Rationale |
|-------------|-----|-----------|
| Pro/Max | 3600s (1hr) | High-volume, stable contexts |
| Free/Team | 300s (5min) | Conservative default |
| API Key | 300s (5min) | No subscription metadata |

## TTL Propagation

Every response MUST include TTL metadata in Fondo Volátil:

```json
{
  "cache_ttl": 3600,
  "cache_tier": "pro",
  "cache_generated_at": "2026-08-09T12:00:00Z",
  "cache_expires_at": "2026-08-09T13:00:00Z"
}
```

## TTL Decay

When cache is hit repeatedly without change:
- Hit 1-5: Full TTL (3600s or 300s)
- Hit 6-10: TTL * 0.75
- Hit 11-20: TTL * 0.5
- Hit 21+: TTL * 0.25

## Stale Cache Handling

If cache entry is older than TTL:
1. Invalidate the cache
2. Regenerate from scratch
3. Log: `cache_miss reason=expired ttl={expired_ttl} age={age_seconds}`
4. Reset hit counter

## TTL in Responses

Include TTL status in every response:
- `fresh`: TTL > 50% remaining
- `aging`: TTL 25-50% remaining
- `stale`: TTL < 25% remaining
- `expired`: TTL = 0 (regenerate)
