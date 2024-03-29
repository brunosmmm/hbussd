"""Data structures and functions related to device data."""
import struct
from array import array
from math import log

from hbussd.hbus.datahandlers import HbusFixPHandler, HbusIntHandler
from hbussd.hbus.constants import HBUS_UNITS


class HbusObjLevel:
    """Object level identifier."""

    # Object has level 0
    level0 = 0x00
    # Object has level 1
    level1 = 0x40
    # Object has level 2
    level2 = 0x80
    # Object has level 3
    level3 = 0xC0


class HbusObjDataType:
    """Object data type identifier."""

    # Byte type
    type_byte = 0x30
    # Integer type
    dataTypeInt = 0x00
    # Unsigned integer type
    dataTypeUnsignedInt = 0x10
    # Fixed point type
    dataTypeFixedPoint = 0x20

    # Byte parsed as hexadecimal
    dataTypeByteHex = 0x01
    # Byte parsed as decimal
    dataTypeByteDec = 0x02

    # Byte parsed as octal
    dataTypeByteOct = 0x03
    # Byte parsed as binary
    dataTypeByteBin = 0x07
    # Byte parsed as boolean
    dataTypeByteBool = 0x08

    # Unsigned integer parsed as percent
    dataTypeUintPercent = 0x04
    # Unsigned integer parsed as linear scale
    dataTypeUintLinPercent = 0x05
    # Unsigned integer parsed as logarithm scale
    dataTypeUintLogPercent = 0x06
    # Unsigned integer parsed as time format
    dataTypeUintTime = 0x09
    # Unsigned integer parsed as date format
    dataTypeUintDate = 0x0A

    # Raw unsigned integer
    dataTypeUintNone = 0x00

    @staticmethod
    def unpack_uint(data):
        """Unpack received data string.

        @param data Data string received from device
        @return value parsed as unsigned integer
        """
        x = [0]
        while len(data) < 4:
            x.extend(data)
            data = x
            x = [0]

        byte_list = array("B", data)

        return struct.unpack(">I", byte_list)[0]

    @staticmethod
    def format_byte_bool(data, extinfo, size, decode=False):
        """Parse data as boolean.

        @param data received data
        @param extinfo dummy parameter
        @param size dummy parameter
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:
            if data == "ON":
                return [1]

            return [0]

        if data[0] > 0:
            return "ON"
        else:
            return "OFF"

    @staticmethod
    def format_byte_hex(data, extinfo, size, decode=False):
        """Parse data as a hexadecimal number.

        @param data received data
        @param extinfo dummy parameter
        @param size data size in bytes
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:
            return [0 * x for x in range(0, size)]

        return ", ".join(["%X" % x for x in data])

    @staticmethod
    def format_byte_dec(data, extinfo, size, decode=False):
        """Parse data as a decimal number.

        @param data received data
        @param extinfo dummy parameter
        @param size data size in bytes
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:
            return [0 * x for x in range(0, size)]

        return ", ".join(["%d" % x for x in data])

    @staticmethod
    def format_byte_oct(data, extinfo, size, decode=False):
        """Parse data as an octal number.

        @param data received data
        @param extinfo dummy parameter
        @param size data size in bytes
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:
            return [0 * x for x in range(0, size)]

        return ", ".join(["%o" % x for x in data])

    @staticmethod
    def format_byte_bin(data, extinfo, size, decode=False):
        """Parse data as a binary number.

        @param data received data
        @param extinfo dummy parameter
        @param size data size in bytes
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:
            return [0 * x for x in range(0, size)]

        return ", ".join(["0b{0:b}".format(x) for x in data])

    @classmethod
    def format_uint(cls, data, extinfo, size, decode=False):
        """Parse data as raw unsigned integer.

        Allows the use of units
        @param data received data
        @param extinfo extended object property list
        @param size data size in bytes
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:
            return [ord(x) for x in struct.pack(">I", data)[size:]]

        value = str(cls.unpack_uint(data))

        try:
            unit = extinfo["UNIT"]
            value = str(value) + " " + HBUS_UNITS[chr(unit[0])]
        except Exception:
            pass

        return value

    @staticmethod
    def format_percent(data, extinfo, size, decode=False):
        """Parse data as percent (0-100).

        @param data received data
        @param extinfo dummy parameter
        @param size dummy parameter
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        if decode:

            data = int(data)
            if data > 100:
                data = 100

            output = []
            for i in range(0, size):
                output.append((data & (0xFF << i * 8)) >> i * 8)

            return output

        # basically ignore size because a percentual value is 0 < val < 100,
        # which only needs one byte
        if isinstance(data, list):
            data = data[0]

        return "{}%".format(data)

    @classmethod
    def format_lin_percent(cls, data, extinfo, size, decode=False):
        """Parse data as a value in a linear scale.

        @param data received data
        @param extinfo extended object property list
        @param size dummy parameter
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        try:
            # Try to set the minimum value for the scale based on the presence
            # of the hidden object MIN
            min_val = cls.unpack_uint(extinfo["MIN"])
        except Exception:
            min_val = 0

        if decode:

            try:
                # Same as the minimum value, extracts maximum value from hidden
                # object MAX if present
                max_val = cls.unpack_uint(extinfo["MAX"])
            except Exception:
                max_val = 2 ** (8 * size) - 1

            # Normalizes value to a percent (0-100) scale
            value = int((float(data) / 100.0) * (max_val - min_val) + min_val)

            output = []
            for i in range(0, size):
                output.append((value & (0xFF << i * 8)) >> i * 8)

            return value

        if data is None:
            return "?"

        # This is encoding, retrieve information and calculate
        try:
            max_val = cls.unpack_uint(extinfo["MAX"])
        except Exception:
            max_val = 2 ** (8 * len(data)) - 1

        value = cls.unpack_uint(data)

        # Maps a percentual value to the object native linear scale
        return "%.2f%%" % (
            (float(value - min_val) / float(max_val - min_val)) * 100
        )

    @classmethod
    def format_log_percent(cls, data, extinfo, size, decode=False):
        """Parse data as a value in a logarithmic scale.

        @param data received data
        @param extinfo extended object property list
        @param size dummy parameter
        @param decode indicates if decoding or encoding data
        @return formatted string
        """
        # Similar to the linear scale processing
        try:
            min_val = cls.unpack_uint(extinfo["MIN"])
        except Exception:
            min_val = 0

        if decode:

            try:
                max_val = cls.unpack_uint(extinfo["MAX"])
            except Exception:
                max_val = 2 ** (8 * size) - 1

            # Maps log scale value to a percent (0-100) scale
            value = int(
                10 ** ((float(data) / 100.0) * log(max_val - min_val))
                + min_val
            )

            output = []
            for i in range(0, size):
                output.append((value & (0xFF << i * 8)) >> i * 8)

            return output

        if data is None:
            return "?"

        # This is the encoding portion
        try:
            max_val = cls.unpack_uint(extinfo["MAX"])
        except Exception:
            max_val = 2 ** (8 * len(data)) - 1

        value = cls.unpack_uint(data)

        # Maps value to object native scale
        try:
            percent = (
                log(float(value - min_val)) / log(float(max_val - min_val))
            ) * 100
        except Exception:
            percent = 0

        return "%.2f%%" % percent

    @staticmethod
    def format_time(data, extinfo, size, decode=False):
        """Parse data as time format.

        @param data received data
        @param extinfo dummy parameter
        @param size dummy parameter
        @param decode indicates if encoding or decoding data
        @return formatted string
        """
        if decode:
            return [0 * x for x in range(0, size)]

        tenth_sec = (data[3] & 0xF0) >> 4
        milli_sec = data[3] & 0x0F

        seconds = data[2] & 0x0F
        tens_sec = data[2] & 0xF0

        minutes = data[1] & 0x0F
        tens = (data[1] & 0xF0) >> 4

        hours24 = data[0] & 0x0F

        return "%2d:%2d:%2d,%2d" % (
            hours24,
            minutes + tens * 10,
            seconds + tens_sec * 10,
            milli_sec + tenth_sec * 10,
        )

        # TODO: missing encode portion

    @staticmethod
    def format_date(data, extinfo, size, decode=False):
        """Parse data as date format.

        @param data received data
        @param extinfo dummy parameter
        @param size dummy parameter
        @param decode indicates if encoding or decoding data
        @return formatted string
        """
        # TODO: implement this parser
        if decode:
            return [0 * x for x in range(0, size)]

        return "?"


# Data type and display string association dictionary
HBUS_DTYPE_NAMES = {
    HbusObjDataType.type_byte: "Byte",
    HbusObjDataType.dataTypeInt: "Int",
    HbusObjDataType.dataTypeUnsignedInt: "Unsigned Int",
    HbusObjDataType.dataTypeFixedPoint: "Fixed point",
}

# Extended data types decoding dictionary
HBUS_DTYPE_OPTIONS = {
    HbusObjDataType.type_byte: {
        HbusObjDataType.dataTypeByteHex: HbusObjDataType.format_byte_hex,
        HbusObjDataType.dataTypeByteDec: HbusObjDataType.format_byte_dec,
        HbusObjDataType.dataTypeByteOct: HbusObjDataType.format_byte_oct,
        HbusObjDataType.dataTypeByteBin: HbusObjDataType.format_byte_bin,
        HbusObjDataType.dataTypeByteBool: HbusObjDataType.format_byte_bool,
    },
    HbusObjDataType.dataTypeUnsignedInt: {
        HbusObjDataType.dataTypeUintNone: HbusObjDataType.format_uint,
        HbusObjDataType.dataTypeUintPercent: HbusObjDataType.format_percent,
        HbusObjDataType.dataTypeUintLinPercent: HbusObjDataType.format_lin_percent,
        HbusObjDataType.dataTypeUintLogPercent: HbusObjDataType.format_log_percent,
        HbusObjDataType.dataTypeUintTime: HbusObjDataType.format_time,
        HbusObjDataType.dataTypeUintDate: HbusObjDataType.format_date,
    },
    HbusObjDataType.dataTypeFixedPoint: HbusFixPHandler(),
    HbusObjDataType.dataTypeInt: HbusIntHandler(),
}


class HbusDeviceObjExtInfo:
    """Device object extended information."""

    # Maximum value
    max_value = None
    # Minimum value
    min_value = None

    # Object extended string
    ext_string = None


class HbusDeviceObject:
    """Device object main class."""

    # Object permissions
    permissions = 0
    # Indicates if data is encrypted
    is_crypto = False
    # Indicates if object is invisible
    # TODO: makes no sense as invisible and visible objects are separated into
    # two different lists
    hidden = False
    # Object descriptor string
    description = None
    # Object size in bytes
    size = 0
    # Object's last known value
    last_value = None

    # Object data type
    objectDataType = 0
    # Extended data type information
    objectDataTypeInfo = None
    # Object level
    objectLevel = 0
    # Object extended information
    objectExtendedInfo = None

    # Gets a formatted output for object's value
    # @return formatted string for display
    def getFormattedValue(self):

        if self.last_value is None:
            return None

        if self.objectDataType not in list(HBUS_DTYPE_OPTIONS.keys()):

            return str(self.last_value)  # has no explicit format

        # analyzes extended information
        if type(HBUS_DTYPE_OPTIONS[self.objectDataType]) == dict:

            if self.objectDataTypeInfo not in list(
                HBUS_DTYPE_OPTIONS[self.objectDataType].keys()
            ):

                return str(self.last_value)  # has no explicit format

        return HBUS_DTYPE_OPTIONS[self.objectDataType][
            self.objectDataTypeInfo
        ](
            data=self.last_value,
            size=self.size,
            extinfo=self.objectExtendedInfo,
        )

    # Object string representation
    # @return descriptive string for logging
    def __repr__(self):

        return self.description


# Device endpoint main class
class HbusEndpoint:

    # Endpoint direction: read, write or both
    endpointDirection = 0
    # Endpoint descriptive string
    endpointDescription = None
    # Data block size in bytes
    endpointBlockSize = 0

    # String representation
    # @return descriptive string for logging
    def __repr__(self):

        return self.endpointDescription


# Device interrupts main class
class HbusInterrupt:

    # Interrupt flags
    interruptFlags = 0
    # Interrupt descriptive string
    interruptDescription = None

    # String representation
    # @return descriptive string for logging
    def __repr__(self):

        return self.interruptDescription


# Device information main class
class HbusDevice:

    # Virtual devices
    hbusSlaveIsVirtual = False

    # Device address
    hbusSlaveAddress = None

    # Device descriptive string
    hbusSlaveDescription = None
    # Device UID
    hbusSlaveUniqueDeviceInfo = None
    # Object count
    # TODO: verify if invisible objects are being counted here
    hbusSlaveObjectCount = 0
    # Endpoint count
    hbusSlaveEndpointCount = 0
    # Interrupt count
    hbusSlaveInterruptCount = 0
    # Device capabilities/features
    hbusSlaveCapabilities = 0

    # Flags if basic device information has been received
    basicInformationRetrieved = False
    # Flags if extended device information has been received
    extendedInformationRetrieved = False

    # Device object dictionary
    hbusSlaveObjects = {}
    # Device endpoint dictionary
    hbusSlaveEndpoints = {}
    # Device interrupt dictionary
    hbusSlaveInterrupts = {}
    # Device invisible object dictionary
    hbusSlaveHiddenObjects = {}

    # TODO: see where is this used
    waitFlag = False

    # Failure flags
    # Initial scanning fail count
    scanRetryCount = 0
    # Consecutive ping fail count
    pingRetryCount = 0
    # Total ping failures that resulted in device eviction from bus
    pingFailures = 0

    # String representation for serialization
    # @return internal data in a string dictionary
    def __repr__(self):
        return str(self.__dict__)

    # Constructor
    # @param explicitSlaveAddress new device address
    def __init__(self, explicitSlaveAddress):
        self.hbusSlaveAddress = explicitSlaveAddress

    # Separates invisible and visible objects
    #
    # Both kinds of objects will be in hbusSlaveObjects after initial scanning.
    # This function is called after that to sort objects by type
    def sortObjects(self):

        self.hbusSlaveHiddenObjects = {}

        for key, val in self.hbusSlaveObjects.items():

            if val.hidden is False:
                continue

            self.hbusSlaveHiddenObjects[key] = val

        for key in list(self.hbusSlaveHiddenObjects.keys()):

            if key in self.hbusSlaveObjects:
                self.hbusSlaveObjects.pop(key)
