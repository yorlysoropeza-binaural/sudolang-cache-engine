---
description: Analyze recent responses for cache hit rate and identify cache pollution
allowed-tools: Read, Grep, Glob
disable-model-invocation: false
---

# Cache Audit

Analyze the current conversation for cache performance:

1. **Scan for Cache Pollution**
   - Search the last 10 responses for dynamic content in the first 80%
   - Look for: timestamps, UUIDs, file paths, user input in static zone
   - Report each violation with line position

2. **Calculate Cache Hit Rate**
   - Compare first 80% of consecutive responses
   - Report: identical / changed / total
   - Calculate hit rate percentage

3. **TTL Compliance Check**
   - Verify TTL metadata exists in each response
   - Check tier-appropriate TTL values (Pro=3600, default=300)
   - Report missing or incorrect TTL

4. **Token Budget Analysis**
   - Measure Frente Estable token count (target: 2000-4000)
   - Measure Fondo Volátil token count (target: 500-2000)
   - Report over/under budget zones

5. **Generate Report**
   ```json
   {
     "audit_timestamp": "2026-08-09T12:00:00Z",
     "cache_hit_rate": 0.85,
     "pollution_violations": 2,
     "ttl_compliance": 0.95,
     "token_budget": {
       "frene_estable": 3200,
       "fondo_volatil": 800,
       "total": 4000
     },
     "recommendations": ["...", "..."]
   }
   ```
