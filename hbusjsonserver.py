#coding=utf-8

##@package hbusjsonserver
# Manages information exchange & control with HTTP/JSON
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 13/02/2014

from txjsonrpc.web import jsonrpc
import simplejson
from hbus_serializers import *
from hbus_base import hbus_address_from_string

##HTTP server for JSON connection
class HBUSJSONServer(jsonrpc.JSONRPC):

    ##Constructor
    #@param master main HBUS master object reference for manipulation
    #@todo decouple main hbus master and peripheral modules
    def __init__(self,master):
        
        ##Master object reference
        self.master = master
    
    ##Gets a list of the busses currently active
    #@return data to be JSON structured
    def jsonrpc_activebusses(self):
        return self.master.getInformationData().activeBusses
    
    ##Gets the current active device count
    #@return data to be JSON structured
    def jsonrpc_activeslavecount(self):
        
        return self.master.getInformationData().activeSlaveCount
    

    ##Gets a list of the UIDs from all currently active devices
    #@return data to be JSON structured
    def jsonrpc_activeslavelist(self):

        slaveList = [x.hbusSlaveUniqueDeviceInfo for x in self.master.detectedSlaveList.values()]
        
        return slaveList
    

    ##Gets detailed information from a device
    #@param uid device's UID
    #@return data to be JSON structured   
    def jsonrpc_slaveinformation(self,uid):

        address = self.master.findDeviceByUID(uid)
        
        if address == None:
            return None
        
        slave = self.master.detectedSlaveList[address.global_id()]
        
        return hbusSlaveSerializer(slave).getDict()
    
    ##Gets a list of a device's objects
    #@param slaveuid device's UID
    #@return data to be JSON structured
    def jsonrpc_slaveobjectlist(self,slaveuid):
        
        address = self.master.findDeviceByUID(slaveuid)
        
        if address == None:
            return None
        
        slave = self.master.detectedSlaveList[address.global_id()]
        
        objectList = [hbusObjectSerializer(x).getDict() for x in slave.hbusSlaveObjects.values()]
        
        return objectList
    
    ##Gets a list of all active devices UIDs in a bus
    #@param bus bus number
    #@return data to be JSON structured
    def jsonrpc_activeslavesbybus(self,bus):
        
        if int(bus) == 255:
            slaveList = self.hbusMaster.detectedSlaveList.values()
        else:
            slaveList = []
            for slave in self.hbusMaster.detectedSlaveList.values():
                if slave.hbusSlaveAddress.bus_number == int(bus):
                    slaveList.append(slave)
                    
        returnList = [x.hbusSlaveUniqueDeviceInfo for x in slaveList]
        
        return returnList
    
    ##Reads value from an object
    #@param address device address
    #@param number object number
    #@return data to be JSON structured
    def jsonrpc_readobject(self,address,number):

        addr = hbus_address_from_string(address)
        
        if not addr.global_id() in self.master.detectedSlaveList.keys():
            
            #device does not exist
            return
        
        if not int(number) in self.master.detectedSlaveList[addr.global_id()].hbusSlaveObjects.keys():
            
            #object does not exist
            return
        
        #deferred?
        
        ##@todo use deferreds to return data
        
    ##Writes a value to an object
    #@param address device address
    #@param number object number
    #@param value value to be written
    #@return data to be JSON structured
    def jsonrpc_writeobject(self,address,number,value):
        
        addr = hbus_address_from_string(address)
        
        if not addr.global_id() in self.master.detectedSlaveList.keys():
            
            #device does not exist
            return
        
        if not int(number) in self.master.detectedSlaveList[addr.global_id()].hbusSlaveObjects.keys():
            
            #object does not exist
            return
        
        #value formatting
        self.master.writeSlaveObject(addr,int(number),int(value))
        
        return 'OK'
