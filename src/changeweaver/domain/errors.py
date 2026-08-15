"""Typed failures with stable exit-code mapping."""


class ChangeWeaverError(Exception):
    """Base class for expected, user-actionable failures."""


class ConfigurationError(ChangeWeaverError):
    """The contract is missing, malformed, or unsupported."""


class RepositoryError(ChangeWeaverError):
    """The target repository cannot be safely read."""


class SnapshotError(ChangeWeaverError):
    """A snapshot is invalid or cannot be compared safely."""


class ComparableError(ChangeWeaverError):
    """Two artifacts were produced from incompatible inputs."""
