#coding=utf-8
##@package hbus_datahandlers
#Data parsers for data received and sent by master
#@author Bruno Morais <brunosmmm@gmail.com>
#@since 18/02/2014

from array import array
import struct
from hbus_constants import HBUS_UNITS
from bitstring import BitArray  # @UnresolvedImport

##Fixed point formatting
class hbusFixedPointHandler:
    
    pointLocation = None

    def formatFixedPoint(self,dummy,data,extInfo,size,decode=False):
        
        x = [0]
        while (len(data) < 4):
            x.extend(data)
            data = x
            x = [0]
        
        byteList = array('B',data)
        
        value = float(struct.unpack('>i',byteList)[0])/(10**float(self.pointLocation))
        
        try:
            unit = extInfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass
        
        return  value
    
    def __getitem__(self,key):
        
        #hack
        self.pointLocation = int(key)
        
        return self.formatFixedPoint

##Integer type formatting
class hbusIntHandler:
    
    def formatInt(self,dummy,data,extInfo,size,decode=False):
        
        value = BitArray(bytes=''.join([chr(x) for x in data])).int
        
        try:
            unit = extInfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass
        
        return str(value)
    
    def __getitem__(self,key):
        
        return self.formatInt
