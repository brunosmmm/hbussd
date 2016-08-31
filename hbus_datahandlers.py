#coding=utf-8

"""Data parsers for data received and sent by master
@package hbus_datahandlers
@author Bruno Morais <brunosmmm@gmail.com>
@since 18/02/2014
"""

from array import array
import struct
from hbus_constants import HBUS_UNITS
from bitstring import BitArray


class HbusFixPHandler(object):
    """Fixed point formatting"""

    point_loc = None

    def format_fixed_point(self, data, extinfo, size, decode=False):

	#currently the working/testing device is sending data in BIG endian format
	#because of this, invert data here before any other operations
	data = data[::-1]

        x = [0]
        while len(data) < 4:
            x.extend(data)
            data = x
            x = [0]

        byte_list = array('B', data)

        value = float(struct.unpack('>i', byte_list)[0])/(10**float(self.point_loc))

        try:
            unit = extinfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass

        return  value

    def __getitem__(self, key):

        #hack
        self.point_loc = int(key)

        return self.format_fixed_point


class HbusIntHandler(object):
    """Integer type formatting"""

    def format_int(self, data, extinfo, size, decode=False):

        value = BitArray(bytes=''.join([chr(x) for x in data])).int

        try:
            unit = extinfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass

        return str(value)

    def __getitem__(self, key):

        return self.format_int
