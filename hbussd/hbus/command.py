"""HBUS command."""


class HbusCommand:
    """HBUS commands."""

    def __init__(self, value, minimumSize, maximumSize, descStr):
        """Initialize.

        @param value command identifier byte value
        @param minimumSize maximum command length in bytes
        @param maximumSize minimum command length in bytes
        @param descStr descriptive string
        """
        # byte value (ID)
        self.cmd_byte = value
        # minimum length
        self.min_len = minimumSize
        # maximum length
        self.max_len = maximumSize
        # descriptive string
        self.desc_str = descStr

    def __repr__(self):
        """Get command representation.

        @return string representation of command
        """
        return self.desc_str + "(" + str(hex(self.cmd_byte)) + ")"

    def __eq__(self, other):
        """Check equality.

        @return returns equal or not
        """
        if isinstance(other, HbusCommand):
            return self.cmd_byte == other.cmd_byte
        return NotImplemented

    # TODO: check if this is being used
    def __hash__(self):
        """Get hash."""
        return hash(self.cmd_byte)
