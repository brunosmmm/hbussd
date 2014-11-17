#coding=utf-8

##@package hbus_serializers
# Functions and classes for serialization of objects, JSON use
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 13/02/2014

##hbusSlaveInformation object type preserializer 
class hbusSlaveSerializer:

    ##Constructor
    #@param slave device object for information extraction
    def __init__(self,slave):
        
        ##Object's description string (device name)
        self.description = slave.hbusSlaveDescription
        ##Device's UID
        self.uid = slave.hbusSlaveUniqueDeviceInfo
        ##Device's object count
        self.objectcount = slave.hbusSlaveObjectCount
        ##Device's endpoint count
        self.endpointcount = slave.hbusSlaveEndpointCount
        ##Device's interrupt count
        self.interruptcount = slave.hbusSlaveInterruptCount
        
        ##Current device address in bus
        self.currentaddress = str(slave.hbusSlaveAddress)
        ##Device capabilities
        self.capabilities = slave.hbusSlaveCapabilities
        
    ##Generates device information dictionary
    #@return dictionary for serialization
    def getDict(self):
        return self.__dict__

##hbusSlaveInformation object type preserializer
class hbusObjectSerializer:
    
    ##Constructor
    #@param obj device object object for data extraction
    def __init__(self,obj):
        
        ##Object permissions
        self.permissions = obj.objectPermissions
        ##Object descriptor string (name)
        self.description = obj.objectDescription
        ##Object size in bytes
        self.size = obj.objectSize
        ##Object last known value
        self.lastvalue = obj.objectLastValue
        ##Object data type
        self.datatype = obj.objectDataType
        ##Object data type information
        self.datatypeinfo = obj.objectDataTypeInfo
        ##Object extended information
        self.extendedinfo = obj.objectExtendedInfo
        ##Object level
        self.objectlevel = obj.objectLevel
    
    ##Generates device object information dictionary
    #@return dictionary for serialization
    def getDict(self):
        return self.__dict__
