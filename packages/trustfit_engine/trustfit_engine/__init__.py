"""TrustFit scoring engine.

Pure and deterministic: no database, network or clock access. The scoring date
(`as_of`) and the config (loaded from the repo's `config/*.yaml`) are always
passed in, so the same inputs always give the same result.
"""

__version__ = "0.1.0"
