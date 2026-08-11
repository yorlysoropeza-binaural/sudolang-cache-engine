---
description: Test cache stability by verifying byte-for-byte consistency across simulated turns
allowed-tools: Read, Bash
disable-model-invocation: false
---

# Cache Test

Verify that a prompt maintains cache stability across multiple turns:

## Input
The user provides a prompt to test.

## Process

1. **Generate Baseline Response**
   - Process the prompt normally
   - Capture the full response
   - Split into Frente Estable (first 80%) and Fondo Volátil (last 20%)
   - Store as baseline

2. **Simulate Turn 2**
   - Process the same prompt with different dynamic context
   - Capture the full response
   - Split into Frente Estable and Fondo Volátil

3. **Compare Prefixes**
   - Byte-compare the two Frente Estable sections
   - Report: identical / different
   - If different: show exact diff

4. **Check for Pollution**
   - Scan baseline prefix for dynamic content
   - Scan turn-2 prefix for dynamic content
   - Report any violations

5. **Measure Cache Efficiency**
   ```
   Cache Efficiency Score = (identical_prefix_bytes / total_prefix_bytes) * 100
   ```

6. **Output Report**
   ```json
   {
     "test_timestamp": "2026-08-09T12:00:00Z",
     "baseline_prefix_tokens": 3200,
     "turn2_prefix_tokens": 3180,
     "cache_efficiency": 99.4,
     "prefix_identical": true,
     "pollution_detected": false,
     "verdict": "PASS"
   }
   ```

## Verdicts

- **PASS**: Prefix identical, no pollution, efficiency > 95%
- **WARN**: Prefix identical but pollution detected
- **FAIL**: Prefix differs or efficiency < 95%
