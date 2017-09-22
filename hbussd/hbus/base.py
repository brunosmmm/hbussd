#coding=utf-8

"""hbussd general purpose data structures
@package hbus_base
@author Bruno Morais <brunosmmm@gmail.com>
@date 2013
"""

import struct
from . import constants as hbusconst
import re


class HbusCommand(object):
    """HBUS commands"""

    def __init__(self, value, minimumSize, maximumSize, descStr):
        """Constructor
        @param value command identifier byte value
        @param minimumSize maximum command length in bytes
        @param maximumSize minimum command length in bytes
        @param descStr descriptive string
        """

        ##byte value (ID)
        self.cmd_byte = value
        ##minimum length
        self.min_len = minimumSize
        ##maximum length
        self.max_len = maximumSize
        ##descriptive string
        self.desc_str = descStr

    def __repr__(self):
        """Command representation
        @return string representation of command
        """
        return self.desc_str+"("+str(hex(self.cmd_byte))+")"

    def __eq__(self, other):
        """Equal operator
        @return returns equal or not
        """
        if isinstance(other, HbusCommand):
            return self.cmd_byte == other.cmd_byte
        return NotImplemented

    ##@todo check if this is being used
    def __hash__(self):

        return hash(self.cmd_byte)

class HbusInstruction(object):
    """HBUS bus instructions (complete commands)"""

    def __init__(self, command, paramSize=0, params=()):
        """Constructor
        @param command instruction command
        @param paramSize parameter size in bytes
        @param params parameters to be sent
        """

        ##Parameter list
        self.params = []
        ##Parameter list size
        self.param_size = 0
        ##HBUS command
        self.command = command

        if command not in hbusconst.HBUS_COMMANDLIST:
            if command == None:
                raise ValueError("Undefined error")
            else:
                raise ValueError("Invalid command: %d" % ord(command.cmd_byte))

        self.param_size = paramSize
        self.params = params

        if (len(params)) > command.max_len:

            raise ValueError("Malformed command, "+str(len(params))+" > "+str(command.max_len))

        if (len(params)+1) < command.min_len:

            raise ValueError("Malformed command, "+str(len(params))+" < "+str(command.min_len))

    def __repr__(self):
        """Instruction representation
        @return string representation of instruction
        """
        if self.param_size > 0:

            try:
                return str(self.command)+str([hex(ord(x)) for x in self.params])
            except TypeError:
                return str(self.command)+str(self.params)
        else:
            return str(self.command)

class HbusDeviceAddress(object):
    """HBUS device addresses"""

    def __init__(self, busID, devID):
        """Constructor
        @param busID bus number
        @param devID device number
        """
        if (devID > 32) and (devID != 255):
            raise ValueError("Invalid address")

        ##Bus number
        self.bus_number = busID
        ##Device number in this bus
        self.dev_number = devID

    def __repr__(self):
        """Address representation
        @return string representation of address
        """
        return "("+str(self.bus_number)+":"+str(self.dev_number)+")"

    def __eq__(self, other):
        """Equal operator for addresses
        @return equal or not
        """
        if isinstance(other, HbusDeviceAddress):
            return self.bus_number == other.bus_number and self.dev_number == other.dev_number
        return NotImplemented

    def global_id(self):
        """Calculates a global ID for an address
        Global IDs are calculated by doing ID = busNumber*32 + deviceNumber
        @return address global ID
        """
        return self.bus_number*32 + self.dev_number


def hbus_address_from_string(addr):
    """Parse a string and create an address from it
    String format is (X:Y) where X is the bus number and Y the device number
    @return HBUS address object
    """
    addr_match = re.match(r'\(([0-9]+):([0-9]+)\)', addr)

    if addr_match != None:

        try:
            return HbusDeviceAddress(int(addr_match.group(1)), int(addr_match.group(2)))
        except:
            raise ValueError
    else:
        raise ValueError


class HbusOperation(object):
    """HBUS bus operation
    Bus operations are composed of an instruction, and message source and destination
    """

    def __init__(self, instruction, destination, source):
        """Constructor
        @param instruction a HbusInstruction object
        @param destination destination device address
        @param source source device address
        """
        ##HBUS instruction
        self.instruction = instruction

        ##Destination address
        self.destination = destination
        ##Source address
        self.source = source

    def __repr__(self):
        """Operation representation
        @return string representation of operation
        """
        return "HBUSOP: "+str(self.source)+"->"+str(self.destination)+" "+str(self.instruction)

    def get_string(self):
        """Generates data string to be sent by master
        @return data string to be sent to bus
        @todo automatically generate parameter size field which depends on command
        """

        header = struct.pack('4c',
                             bytes([self.source.bus_number]),
                             bytes([self.source.dev_number]),
                             bytes([self.destination.bus_number]),
                             bytes([self.destination.dev_number]))

        instruction = struct.pack('c',
                                  bytes([self.instruction.command.cmd_byte]))

        terminator = b'\xFF'
        if isinstance(self.instruction.params, bytes):
            return header+instruction+self.instruction.params+terminator

        for param in self.instruction.params:

            if isinstance(param, str):
                if len(param) == 1:
                    instruction = instruction + struct.pack('c',
                                                            param)
                else:
                    instruction = instruction + param
            elif isinstance(param, int):
                instruction = instruction + struct.pack('c', bytes([param]))
            else:
                instruction = instruction + struct.pack('c', param)

        return header+instruction+terminator
