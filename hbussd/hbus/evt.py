"""HBUS master events."""

# @brief Master event system
# @since 11/23/2014
# @author Bruno Morais <brunosmmm@gmail.com>


class HbusMasterEventType:
    """Master event types."""

    # Master started
    eventStarted = 0
    # Master entered operational phase
    eventOperational = 1
    # Master received interruption
    eventInterruption = 2
    # Master kicked device from bus
    eventDeviceKicked = 3
    # Master registered new device in bus
    eventDeviceAdded = 4
    # Unknown
    eventNone = 5


class HbusMasterEvent:
    """Master event."""

    eventType = HbusMasterEventType.eventNone

    def __init__(self, eventType=HbusMasterEventType.eventNone):
        """Initialize."""
        self.eventType = eventType
