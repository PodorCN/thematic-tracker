"""Shared independent-reviewer core for all trackers.

Product-agnostic mechanics live here (canonical freeze bytes, SHA binding,
role separation, verdict/severity coherence, flags coverage). Product-specific
judgment (structural checks, scoring rubrics, flags definitions) stays in each
product's own AGENT.md plus a small flags plugin under scripts/review/.
"""
