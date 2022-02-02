"""HBUS exceptions."""


class HbusException(Exception):
    """Base HBUS exception."""


class HBUSDoNotRetryException(HbusException):
    """Do not retry exception."""


class HBUSDataAlreadyReceived(HbusException):
    """Data already received exception."""


class HBUSTimeoutException(HbusException):
    """Timeout exception."""


class HBUSRetryInformation:
    """Retry information."""

    def __init__(self, attempts=0):
        """Initialize."""
        self.attempts = attempts
