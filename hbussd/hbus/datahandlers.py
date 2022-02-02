"""Data parsers for data received and sent by master."""

import struct
from array import array

from bitstring import BitArray
from hbussd.hbus.constants import HBUS_UNITS


class HbusDataFormatter:
    """Data formatter."""

    def format_data(self, data, extinfo, size, decode=False):
        """Format data."""
        raise NotImplementedError

    def prepare_data(self, requested_key):
        """Prepare data."""
        pass

    def __getitem__(self, key):
        """Get byte from formatted data."""
        self.prepare_data(key)
        return self.format_data


class HbusFixPHandler(HbusDataFormatter):
    """Fixed point formatting."""

    point_loc = None

    def prepare_data(self, requested_key):
        """Prepare data."""
        self.point_loc = int(requested_key)

    def format_data(self, data, extinfo, size, decode=False):
        """Format fixed point data."""
        # currently the working/testing device is sending data in
        # BIG endian format
        # because of this, invert data here before any other operations
        data = data[::-1]
        x = [0]
        while len(data) < 4:
            x.extend(data)
            data = x
            x = [0]

        byte_list = array("B", data)

        value = float(struct.unpack(">i", byte_list)[0]) / (
            10 ** float(self.point_loc)
        )

        try:
            unit = extinfo["UNIT"]
            value = str(value) + " " + HBUS_UNITS[chr(unit[0])]
        except Exception:
            pass

        return value


class HbusIntHandler(HbusDataFormatter):
    """Integer type formatting."""

    def format_data(self, data, extinfo, size, decode=False):
        """Format data."""
        value = BitArray(bytes="".join([chr(x) for x in data])).int

        try:
            unit = extinfo["UNIT"]
            value = str(value) + " " + HBUS_UNITS[chr(unit[0])]
        except Exception:
            pass

        return str(value)
