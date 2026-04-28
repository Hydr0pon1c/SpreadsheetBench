# Trace2Skill Variant Comparison

Split: `data/splits/verified_test_200.json`

| Condition | Count | Hard Pass | Hard Rate | Soft Avg | Delta vs skill0 | Delta vs No Skill |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| No Skill | 200 | 49 | 24.50% | 24.50% | -2.00 pp | +0.00 pp |
| skill0 Parametric | 200 | 53 | 26.50% | 26.50% | +0.00 pp | +2.00 pp |
| Error-only skill* | 200 | 57 | 28.50% | 28.50% | +2.00 pp | +4.00 pp |
| Success-only skill* | 200 | 56 | 28.00% | 28.00% | +1.50 pp | +3.50 pp |
| Combined skill* | 200 | 56 | 28.00% | 28.00% | +1.50 pp | +3.50 pp |

## Pairwise Changes vs skill0

| Variant | Improved Tasks | Regressed Tasks | Net |
| --- | ---: | ---: | ---: |
| Error-only skill* | 29 | 25 | +4 |
| Success-only skill* | 29 | 26 | +3 |
| Combined skill* | 30 | 27 | +3 |

## Notes

- Error-only is the best variant in this run by hard pass count.
- Success-only and combined tie on aggregate hard rate.
- Combined has the most improvements over skill0, but also the most regressions, so its net gain is the same as success-only.
- Soft average equals hard rate here because these evaluated records effectively have binary per-task outcomes.
