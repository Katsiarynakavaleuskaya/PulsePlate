"""Deterministic hash sampler for request-level full capture decisions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class SamplingDecision:
    """Deterministic full-capture decision payload."""

    capture_full: bool
    digest_prefix: str
    rate: float


class DeterministicHashSampler:
    """Hash-based sampler stable across retries and processes."""

    def __init__(self, rate: float = 0.01, salt: str = "pp#2026") -> None:
        self.rate = max(0.0, min(rate, 1.0))
        self.bound = int(self.rate * (2**32))
        self.salt = salt

    def decide(self, *, fingerprint: str) -> SamplingDecision:
        """Return a deterministic decision for the given fingerprint."""

        digest = hashlib.blake2s(
            f"{self.salt}:{fingerprint}".encode("utf-8"),
            digest_size=4,
        ).digest()
        value = int.from_bytes(digest, "big")
        return SamplingDecision(
            capture_full=value < self.bound,
            digest_prefix=digest.hex(),
            rate=self.rate,
        )

    def get_description(self) -> str:
        """Return human-readable sampler description for diagnostics."""

        return f"DeterministicHashSampler(rate={self.rate:.4f})"
