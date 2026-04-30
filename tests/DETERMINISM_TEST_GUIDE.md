# Sequencing Determinism Test Infrastructure

**Date**: 2026-04-30  
**Status**: ✅ ACTIVE  
**Tests**: 4 new determinism tests + 71 existing = **75 total**  

## Purpose

Provides regression protection for:
- Core effect engine placement reproducibility (v27.3 "Helix Prime")
- Style variant catalog loading and consistency
- Quality gate compliance verification
- Deterministic sequencing output guarantee

## Test Coverage

### `tests/test_sequencing_determinism.py`

1. **`test_deterministic_v27_3_placement`**
   - Verifies identical input audio → identical effect placement
   - Guards against v27.3 tuning drift

2. **`test_v27_3_respects_quality_gates`**
   - Confirms audit scores meet minimum threshold (72.0)
   - Blocks quality regression

3. **`test_style_version_active_profile`**
   - Validates active profile is v27.3 Helix Prime
   - Guards against profile switching

4. **`test_variant_catalog_loads`**
   - Verifies variant catalog population
   - Checks v27.3 is available and configured

## Running Tests

```bash
# All tests (recommended)
python -m pytest tests/ -v

# Just determinism tests
python -m pytest tests/test_sequencing_determinism.py -v

# With coverage
python -m pytest tests/test_sequencing_determinism.py --cov=core.effect_engine -v
```

## Integration with PR-C/PR-D Review

**Blocks these merges until extended:**
- PR-C: Advanced runtime bundle (core sequencing changes)
- PR-D: Scoring refinements (self_improving_scoring.py)

**Next steps to unlock safe merges:**
1. ✅ **Done**: Basic determinism test structure
2. **TODO**: Extend with actual snapshot serialization (JSON baseline)
3. **TODO**: Add audio regression tests (PR-E compatibility)
4. **TODO**: Add import smoke tests (PR-F helix_* packages)
5. **TODO**: Add CLI contract tests (PR-F helix_cli.py)

## Known Limitations

Current implementation is a **test framework scaffold**. Full snapshot-based regression testing requires:
- Baseline JSON serialization of placement output
- Stored in `tests/snapshots/v27.3_baseline.json`
- Deep equality comparison of effect windows, categories, timing

## Future Enhancements

```python
# Example snapshot structure (planned)
{
  "seed": 12345,
  "style_version": "v27.3",
  "effect_count": 428,
  "categories": {
    "ramp": 142,
    "wave": 86,
    "on": 200,
  },
  "section_scores": [
    {"label": "INTRO", "score": 88.5},
    {"label": "VERSE", "score": 91.2},
    ...
  ],
  "audit_final": {
    "score": 91.0,
    "grade": "A",
    "musical_coherence": 89.0,
    "intensity_balance": 90.0,
  }
}
```

## References

- Audit system: [core/audit.py](../../core/audit.py)
- Active variant: v27.3 "Helix Prime" in [core/engine_style_catalog.py](../../core/engine_style_catalog.py#L1906)
- Quality gates: [tools/build_helpers.py](../../tools/build_helpers.py#L13)
