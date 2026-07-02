"""Stage 3.5 wiring — per-resource specs + a driver that carries a dataset to a resolved state.

The archive's non-flagship datasets are wired by DATA, not code: ``resource_specs.json`` (generated
from the archive, reviewed and committed) gives each resource either a spec the general machinery
runs or an honest deferral reason. Nothing is dropped — every on-disk dataset ends resolved
(geo-anchored or national) or quarantined/deferred with a reason.
"""
