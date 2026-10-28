# Verification Template

Each resolved finding should capture:

- Validation method: test | build | lint | targeted repro | static proof
- Command:
  - `[exact command]`
- Result:
  - `passed`, `failed`, or `partial`
- Evidence:
  - [short result summary, request trace, or reasoning]
- Residual risk:
  - [if any]

If verification is partial, keep the finding `blocked` or `needs-context`.
