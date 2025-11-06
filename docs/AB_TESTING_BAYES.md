# Bayesian A/B Overview (VIP/Paywall)

This document describes how we apply Bayes' theorem (Beta–Bernoulli) and Thompson Sampling to analyze conversion in VIP/paywall flows.

## Model
- Prior: Beta(α0, β0), typically α0=1, β0=1.
- Observations: s successes, f failures.
- Posterior: Beta(α0+s, β0+f).
- Mean: α/(α+β). Thompson Sampling draws p ~ Beta(α, β) per variant and picks max p.

## Implementation Notes
- Sampling via `random.betavariate(alpha, beta)` (no SciPy).
- Intervals optional (can add SciPy later).
- Nightly job can aggregate s/f per variant and report posterior means.

## CI/Nightly
- Nightly runs produce `bayesian_quality_report.json` artifact summarizing analyzer diagnostics.
