"""HBUS exceptions."""


class HBUSDoNotRetryException(Exception):
    """Do not retry exception."""


class HBUSDataAlreadyReceived(Exception):
    """Data already received exception."""


class HBUSTimeoutException(IOError):
    """Timeout exception."""


class HBUSRetryInformation:
    """Retry information."""

    def __init__(self, attempts=0):
        """Initialize."""
        self.attempts = attempts
