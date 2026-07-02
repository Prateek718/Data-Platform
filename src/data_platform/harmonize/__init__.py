"""Stage 4 — metric harmonization.

Cross-source reconciliation to one trustworthy canonical value per metric per canonical key, or a
recorded disagreement. Per the project's harmonization philosophy (CLAUDE.md): normalize
aggressively (this module's units/rollup transforms), resolve conservatively, publish divergence,
never invent a value or unit the source does not support.
"""
