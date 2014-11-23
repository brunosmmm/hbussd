#coding=utf-8
##@package hbusslaves
# Data structures and functions related to enumeration and parsing of device data
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 18/02/2014

from hbus_datahandlers import *
import struct
from array import array
from math import log

##Object level identifier
class hbusSlaveObjectLevel:
    
    ##Object has level 0
    level0  = 0x00
    ##Object has level 1
    level1  = 0x40
    ##Object has level 2
    level2  = 0x80
    ##Object has level 3
    level3  = 0xC0

##Object data type identifier
class hbusSlaveObjectDataType:
    ##Byte type
    dataTypeByte        = 0x30
    ##Integer type
    dataTypeInt         = 0x00
    ##Unsigned integer type
    dataTypeUnsignedInt = 0x10
    ##Fixed point type
    dataTypeFixedPoint  = 0x20
    
    ##Byte parsed as hexadecimal
    dataTypeByteHex     = 0x01
    ##Byte parsed as decimal
    dataTypeByteDec     = 0x02
    ##Byte parsed as octal
    dataTypeByteOct     = 0x03
    ##Byte parsed as binary
    dataTypeByteBin     = 0x07
    ##Byte parsed as boolean
    dataTypeByteBool    = 0x08
    
    ##Unsigned integer parsed as percent
    dataTypeUintPercent     = 0x04
    ##Unsigned integer parsed as linear scale
    dataTypeUintLinPercent  = 0x05
    ##Unsigned integer parsed as logarithm scale 
    dataTypeUintLogPercent  = 0x06
    ##Unsigned integer parsed as time format
    dataTypeUintTime        = 0x09
    ##Unsigned integer parsed as date format
    dataTypeUintDate        = 0x0A
    
    ##Raw unsigned integer
    dataTypeUintNone        = 0x00
    
    ##Unpacks received data string
    #@param data Data string received from device
    #@return value parsed as unsigned integer
    def unpackUINT(self,data):

        x = [0]
        while (len(data) < 4):
            x.extend(data)
            data = x
            x = [0]
        
        byteList = array('B',data)
        
        return struct.unpack('>I',byteList)[0]
    
    ##Parses data as boolean
    #@param data received data
    #@param extInfo dummy parameter
    #@param size dummy parameter
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatBoolBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            if data == "ON":
                return [1];
            
            return [0];
        
        if (data[0] > 0):
            return 'ON'
        else:
            return 'OFF'
    
    ##Parses data as a hexadecimal number
    #@param data received data
    #@param extInfo dummy parameter
    #@param size data size in bytes
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatHexBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%X' % x for x in data])
   
    ##Parses data as a decimal number
    #@param data received data
    #@param extInfo dummy parameter
    #@param size data size in bytes
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatDecBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%d' % x for x in data])
   
    ##Parses data as an octal number
    #@param data received data
    #@param extInfo dummy parameter
    #@param size data size in bytes
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatOctBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%o' % x for x in data])
    
    ##Parses data as a binary number
    #@param data received data
    #@param extInfo dummy parameter
    #@param size data size in bytes
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatBinBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['0b{0:b}'.format(x) for x in data])
    
    ##Parses data as raw unsigned integer. Allows the use of units
    #@param data received data
    #@param extInfo extended object property list
    #@param size data size in bytes
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatUint(self,data,extInfo,size,decode=False):
        
        if decode:
            return [ord(x) for x in struct.pack('>I',data)[size:]]
        
        value = str(self.unpackUINT(data))
        
        try:
            unit = extInfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass
        
        return value

    ##Parses data as percent (0-100)
    #@param data received data
    #@param extInfo dummy parameter
    #@param size dummy parameter
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatPercent(self,data,extInfo,size,decode=False):
        
        if len(data) > 0:
            try:
                data = int(data[::-1])
            except:
                data = 0
            
        if data > 100:
            data = 100
            
        if decode:
            return [ord(x) for x in struct.pack('>I',data)[size:]]
            
        return "%d%%" % data

    ##Parses data as a value in a linear scale
    #@param data received data
    #@param extInfo extended object property list
    #@param size dummy parameter
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatRelLinPercent(self,data,extInfo,size,decode=False):
        
        try:
            #Try to set the minimum value for the scale based on the presence of the hidden object MIN
            minimumValue = self.unpackUINT(extInfo['MIN'])
        except:
            minimumValue = 0
        
        if decode:
            
            try:
                #Same as the minimum value, extracts maximum value from hidden object MAX if present
                maximumValue = self.unpackUINT(extInfo['MAX'])
            except:
                maximumValue = 2**(8*size) - 1
                
            #Normalizes value to a percent (0-100) scale
            value = int((float(data)/100.0)*(maximumValue-minimumValue) + minimumValue)
            
            return [ord(x) for x in struct.pack('>I',value)[size:]]
        
        if data == None:
            return "?"
        
        #This is encoding, retrieve information and calculate 
        try:
            maximumValue = self.unpackUINT(extInfo['MAX'])
        except:
            maximumValue = 2**(8*len(data)) - 1
        
        value = self.unpackUINT(data)
        
        #Maps a percentual value to the object native linear scale 
        return "%.2f%%" % ((float(value-minimumValue)/float(maximumValue-minimumValue))*100)

    ##Parse data as a value in a logarithmic scale
    #@param data received data
    #@param extInfo extended object property list
    #@param size dummy parameter
    #@param decode indicates if decoding or encoding data
    #@return formatted string
    def formatRelLogPercent(self,data,extInfo,size,decode=False):
        
        #Similar to the linear scale processing
        try:
            minimumValue = self.unpackUINT(extInfo['MIN'])
        except:
            minimumValue = 0
        
        if decode:
            
            try:
                maximumValue = self.unpackUINT(extInfo['MAX'])
            except:
                maximumValue = 2**(8*size) - 1
                
            #Maps log scale value to a percent (0-100) scale
            value = int(10**((float(data)/100.0)*log(maximumValue-minimumValue)) + minimumValue)
            
            return [ord(x) for x in struct.pack('>I',value)[size:]]
        
        if data == None:
            return "?"
        
        #This is the encoding portion
        try:
            maximumValue = self.unpackUINT(extInfo['MAX'])
        except:
            maximumValue = 2**(8*len(data)) - 1
            
        
        value = self.unpackUINT(data)
        
        #Maps value to object native scale
        try:
            percent = (log(float(value-minimumValue))/log(float(maximumValue-minimumValue)))*100
        except:
            percent = 0
            
        
        return "%.2f%%" % percent
    
    ##Parses data as time format
    #@param data received data
    #@param extInfo dummy parameter
    #@param size dummy parameter
    #@param decode indicates if encoding or decoding data
    #@return formatted string
    def formatTime(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        tenthSeconds = (data[3] & 0xF0)>>4
        milliSeconds = data[3] & 0x0F
        
        seconds = data[2] & 0x0F
        tensOfSeconds = data[2] & 0xF0
        
        minutes = data[1] & 0x0F
        tens = (data[1] & 0xF0) >> 4
        
        hours24 = data[0] & 0x0F
        
        return "%2d:%2d:%2d,%2d" % (hours24,minutes+tens*10,seconds+tensOfSeconds*10,milliSeconds+tenthSeconds*10)

        ##@todo missing encode portion
    
    ##Parse data as date format
    #@param data received data
    #@param extInfo dummy parameter
    #@param size dummy parameter
    #@param decode indicates if encoding or decoding data
    #@return formatted string
    def formatDate(self,data,extInfo,size,decode=False):
        
        ##@todo implement this parser

        if decode:
            return [0*x for x in range(0,size)]
        
        return "?"
    
    ##Data type and display string association dictionary
    dataTypeNames = {dataTypeByte : 'Byte', 
                     dataTypeInt : 'Int', 
                     dataTypeUnsignedInt : 'Unsigned Int', 
                     dataTypeFixedPoint : 'Fixed point'}

    ##Extended data types decoding dictionary
    dataTypeOptions = {dataTypeByte : {dataTypeByteHex : formatHexBytes, 
                                       dataTypeByteDec : formatDecBytes,
                                       dataTypeByteOct : formatOctBytes,
                                       dataTypeByteBin : formatBinBytes, 
                                       dataTypeByteBool : formatBoolBytes},
                       dataTypeUnsignedInt : {dataTypeUintNone : formatUint, 
                                              dataTypeUintPercent : formatPercent, 
                                              dataTypeUintLinPercent : formatRelLinPercent, 
                                              dataTypeUintLogPercent : formatRelLogPercent, 
                                              dataTypeUintTime : formatTime, 
                                              dataTypeUintDate : formatDate},
                       dataTypeFixedPoint : hbusFixedPointHandler(),
                       dataTypeInt : hbusIntHandler()}

##Devcice object extended information
class hbusSlaveObjectExtendedInfo:
    
    ##Maximum value
    objectMaximumValue = None
    ##Minimum value
    objectMinimumValue = None
    
    ##Object extended string
    objectExtendedString = None

##Device object main class
class hbusSlaveObjectInfo:

    ##Object permissions
    objectPermissions = 0
    ##Indicates if data is encrypted
    objectCrypto = False
    ##Indicates if object is invisible
    #@todo makes no sense as invisible and visible objects are separated into two different lists
    objectHidden = False
    ##Object descriptor string
    objectDescription = None
    ##Object size in bytes
    objectSize = 0
    ##Object's last known value
    objectLastValue = None
    
    ##Object data type
    objectDataType = 0
    ##Extended data type information
    objectDataTypeInfo = None
    ##Object level
    objectLevel = 0
    ##Object extended information
    objectExtendedInfo = None
    
    ##Gets a formatted output for object's value
    #@return formatted string for display
    def getFormattedValue(self):
        
        if self.objectLastValue == None:
            return None
        
        if self.objectDataType not in hbusSlaveObjectDataType.dataTypeOptions.keys():
            
            return str(self.objectLastValue) #has no explicit format
        
        #analyzes extended information
        if type(hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType]) == dict: 
        
            if self.objectDataTypeInfo not in hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType].keys():
            
                return str(self.objectLastValue) #has no explicit format
                
        return hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType][self.objectDataTypeInfo](hbusSlaveObjectDataType(),data=self.objectLastValue,size=self.objectSize,extInfo=self.objectExtendedInfo)
        
    ##Object string representation
    #@return descriptive string for logging
    def __repr__(self):
        
        return self.objectDescription

##Device endpoint main class
class hbusSlaveEndpointInfo:
    
    ##Endpoint direction: read, write or both
    endpointDirection = 0
    ##Endpoint descriptive string
    endpointDescription = None
    ##Data block size in bytes
    endpointBlockSize = 0
    
    ##String representation
    #@return descriptive string for logging
    def __repr__(self):
        
        return self.endpointDescription

##Device interrupts main class
class hbusSlaveInterruptInfo:
    
    ##Interrupt flags
    interruptFlags = 0
    ##Interrupt descriptive string
    interruptDescription = None
    
    ##String representation
    #@return descriptive string for logging
    def __repr__(self):
        
        return self.interruptDescription

##Device information main class
class hbusSlaveInfo:
    
    ##Virtual devices
    hbusSlaveIsVirtual = False

    ##Device address
    hbusSlaveAddress = None
    
    ##Device descriptive string
    hbusSlaveDescription = None
    ##Device UID
    hbusSlaveUniqueDeviceInfo = None
    ##Object count
    #@todo verify if invisible objects are being counted here
    hbusSlaveObjectCount = 0
    ##Endpoint count
    hbusSlaveEndpointCount = 0
    ##Interrupt count
    hbusSlaveInterruptCount = 0
    ##Device capabilities/features
    hbusSlaveCapabilities = 0
    
    ##Flags if basic device information has been received
    basicInformationRetrieved = False
    ##Flags if extended device information has been received
    extendedInformationRetrieved = False
    
    ##Device object dictionary
    hbusSlaveObjects = {}
    ##Device endpoint dictionary
    hbusSlaveEndpoints = {}
    ##Device interrupt dictionary
    hbusSlaveInterrupts = {}
    ##Device invisible object dictionary
    hbusSlaveHiddenObjects = {}
    
    ##@todo see where is this used
    waitFlag = False
    
    #Failure flags
    ##Initial scanning fail count
    scanRetryCount = 0
    ##Consecutive ping fail count
    pingRetryCount = 0
    ##Total ping failures that resulted in device eviction from bus
    pingFailures = 0
    
    ##String representation for serialization
    #@return internal data in a string dictionary
    def __repr__(self):
        return str(self.__dict__)
    
    ##Constructor
    #@param explicitSlaveAddress new device address
    def __init__(self,explicitSlaveAddress):
        self.hbusSlaveAddress = explicitSlaveAddress
    
    ##Separates invisible and visible objects
    #
    #Both kinds of objects will be in hbusSlaveObjects after initial scanning. This function is called after that to sort objects by type
    def sortObjects(self):
        
        self.hbusSlaveHiddenObjects = {}
        
        for key,val in self.hbusSlaveObjects.viewitems():
            
            if val.objectHidden == False:
                continue
            
            self.hbusSlaveHiddenObjects[key] = val
            
        for key in self.hbusSlaveHiddenObjects.keys():
            
            if key in self.hbusSlaveObjects:
                self.hbusSlaveObjects.pop(key)
                