"""General purpose data structures for hbuss.

@package hbus_base
@author Bruno Morais <brunosmmm@gmail.com>
@date 2013
"""

import re

import hbussd.hbus.constants as hbusconst


class HbusInstruction:
    """HBUS bus instructions (complete commands)."""

    def __init__(self, command, paramSize=0, params=()):
        """Initialize.

        @param command instruction command
        @param paramSize parameter size in bytes
        @param params parameters to be sent
        """
        # Parameter list
        self.params = []
        # Parameter list size
        self.param_size = 0
        # HBUS command
        self.command = command

        if command not in hbusconst.HBUS_COMMANDLIST:
            if command is None:
                raise ValueError("Undefined error")
            else:
                raise ValueError("Invalid command: %d" % ord(command.cmd_byte))

        self.param_size = paramSize
        self.params = params

        if (len(params)) > command.max_len:

            raise ValueError(
                "Malformed command, "
                + str(len(params))
                + " > "
                + str(command.max_len)
            )

        if (len(params) + 1) < command.min_len:

            raise ValueError(
                "Malformed command, "
                + str(len(params))
                + " < "
                + str(command.min_len)
            )

    def __repr__(self):
        """Get instruction representation.

        @return string representation of instruction
        """
        if self.param_size > 0:

            try:
                return str(self.command) + str(
                    [hex(ord(x)) for x in self.params]
                )
            except TypeError:
                return str(self.command) + str(self.params)
        else:
            return str(self.command)


class HbusDeviceAddress:
    """HBUS device addresses."""

    def __init__(self, busID, devID):
        """Initialize.

        @param busID bus number
        @param devID device number
        """
        if (devID > 32) and (devID != 255):
            raise ValueError("Invalid address")

        # Bus number
        self.bus_number = busID
        # Device number in this bus
        self.dev_number = devID

    def __repr__(self):
        """Get legible address representation.

        @return string representation of address
        """
        return "(" + str(self.bus_number) + ":" + str(self.dev_number) + ")"

    def __eq__(self, other):
        """Check equality.

        @return equal or not
        """
        if isinstance(other, HbusDeviceAddress):
            return (
                self.bus_number == other.bus_number
                and self.dev_number == other.dev_number
            )
        return False

    def __hash__(self):
        """Get hash."""
        return hash(tuple(self.bus_number, self.dev_number))

    @property
    def global_id(self):
        """Calculate global ID for an address.

        Global IDs are calculated by doing ID = busNumber*32 + deviceNumber
        @return address global ID
        """
        return self.bus_number * 32 + self.dev_number


def hbus_address_from_string(addr):
    """Parse a string and create an address from it.

    String format is (X:Y) where X is the bus number and Y the device number
    @return HBUS address object
    """
    addr_match = re.match(r"\(([0-9]+):([0-9]+)\)", addr)

    if addr_match is not None:

        try:
            return HbusDeviceAddress(
                int(addr_match.group(1)), int(addr_match.group(2))
            )
        except Exception:
            raise ValueError
    else:
        raise ValueError


class HbusOperation:
    """HBUS bus operation.

    Bus operations are composed of an instruction
    and message source and destination
    """

    def __init__(self, instruction, destination, source):
        """Initialize.

        @param instruction a HbusInstruction object
        @param destination destination device address
        @param source source device address
        """
        # HBUS instruction
        self.instruction = instruction

        # Destination address
        self.destination = destination
        # Source address
        self.source = source

    def __repr__(self):
        """Get operation representation.

        @return string representation of operation
        """
        return (
            "HBUSOP: "
            + str(self.source)
            + "->"
            + str(self.destination)
            + " "
            + str(self.instruction)
        )

    def get_packed(self):
        """Generate data string to be sent by master.

        @return data string to be sent to bus
        @todo automatically generate parameter size field which
        depends on command
        """
        header = (
            bytes([self.source.bus_number])
            + bytes([self.source.dev_number])
            + bytes([self.destination.bus_number])
            + bytes([self.destination.dev_number])
        )

        instruction = bytes([self.instruction.command.cmd_byte])

        terminator = b"\xFF"
        if isinstance(self.instruction.params, bytes):
            return header + instruction + self.instruction.params + terminator

        for param in self.instruction.params:

            if isinstance(param, str):
                instruction += param.encode("ascii")
            elif isinstance(param, int):
                instruction += bytes([param])
            elif isinstance(param, bytes):
                instruction += param
            else:
                raise TypeError("unsupported type: {}".format(type(param)))

        return header + instruction + terminator
