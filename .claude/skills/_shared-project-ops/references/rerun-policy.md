# Rerun Policy

After each fix:

1. Rerun the most local verification first.
2. Rerun any skill whose surface was directly changed.
3. Rerun adjacent security or contract checks if auth, serialization, config, or persistence changed.
4. Reconcile findings and issues before moving to the next fix.

Stop only when there are no `confirmed-open` or `in-progress` findings remaining.
