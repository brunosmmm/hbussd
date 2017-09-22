#coding=utf-8

##@package hbusjsonserver
# Manages information exchange & control with HTTP/JSON
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 13/02/2014

from txjsonrpc.web import jsonrpc
import simplejson
from serializers import *
from hbus.base import hbus_address_from_string
from master import hbusMasterState
import logging


##HTTP server for JSON connection
class HBUSJSONServer(jsonrpc.JSONRPC):

    ##Constructor
    #@param master main HBUS master object reference for manipulation
    #@todo decouple main hbus master and peripheral modules
    def __init__(self,master):
        
        ##Master object reference
        self.master = master
        self.logger = logging.getLogger('hbussd.jsonsrv')
        self.read_data = None
        self.waiting_for_read = False
        self.read_slave_addr = None
        self.read_slave_object = None
        self.read_finished = True

    def _is_operational(self):

        state = self.master.masterState != hbusMasterState.hbusMasterStarting
        if state is False:
            self.logger.warning('master not operational')

        return state

    ##Gets a list of the busses currently active
    #@return data to be JSON structured
    def jsonrpc_activebusses(self):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        return {'status': 'ok',  'list': self.master.getInformationData().activeBusses}
    
    ##Gets the current active device count
    #@return data to be JSON structured

    def jsonrpc_activeslavecount(self):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        return {'status': 'ok', 'list': self.master.getInformationData().activeSlaveCount}
    

    ##Gets a list of the UIDs from all currently active devices
    #@return data to be JSON structured

    def jsonrpc_activeslavelist(self):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        slaveList = [x.hbusSlaveUniqueDeviceInfo for x in self.master.detectedSlaveList.values()]
        
        return {'status': 'ok', 'list': slaveList}
    

    ##Gets detailed information from a device
    #@param uid device's UID
    #@return data to be JSON structured

    def jsonrpc_slaveinformation(self,uid):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        address = self.master.findDeviceByUID(uid)
        
        if address == None:
            return {'status': 'error',
                    'error': 'invalid_uid'}
        
        slave = self.master.detectedSlaveList[address.global_id()]
        
        ret = hbusSlaveSerializer(slave).getDict()
        ret['status'] = 'ok'

        return ret
    
    ##Gets a list of a device's objects
    #@param slaveuid device's UID
    #@return data to be JSON structured

    def jsonrpc_slaveobjectlist(self,slaveuid):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        address = self.master.findDeviceByUID(slaveuid)
        
        if address == None:
            return {'status': 'error',
                    'error': 'invalid_uid'}
        
        slave = self.master.detectedSlaveList[address.global_id()]
        
        objectList = [hbusObjectSerializer(x).getDict() for x in slave.hbusSlaveObjects.values()]
        
        return {'status': 'ok', 'list': objectList}
    
    ##Gets a list of all active devices UIDs in a bus
    #@param bus bus number
    #@return data to be JSON structured

    def jsonrpc_activeslavesbybus(self,bus):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        if int(bus) == 255:
            slaveList = self.hbusMaster.detectedSlaveList.values()
        else:
            slaveList = []
            for slave in self.hbusMaster.detectedSlaveList.values():
                if slave.hbusSlaveAddress.bus_number == int(bus):
                    slaveList.append(slave)
                    
        returnList = [x.hbusSlaveUniqueDeviceInfo for x in slaveList]
        
        return {'status': 'ok', 'list': returnList}
    
    ##Reads value from an object
    #@param address device address
    #@param number object number
    #@return data to be JSON structured

    def jsonrpc_readobject(self,address,number):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        #for now, make sure that we are not doing anything else (waiting)
        if self.read_finished == False:
            return {'status': 'error',
                    'error': 'busy'}

        addr = hbus_address_from_string(address)
        
        if not addr.global_id() in self.master.detectedSlaveList.keys():
            
            #device does not exist
            return {'status': 'error',
                    'error': 'invalid_device'}
        
        if not int(number) in self.master.detectedSlaveList[addr.global_id()].hbusSlaveObjects.keys():
            
            #object does not exist
            return {'status': 'error',
                    'error': 'invalid_object'}

        try:
            self.master.readSlaveObject(addr,
                                        int(number),
                                        self._read_object_callback,
                                        self._read_object_timeout_callback)
        except IOError:
            return {'status': 'write_only'}

        self.waiting_for_read = True
        self.read_slave_addr = addr
        self.read_slave_object = number
        self.read_finished = False
        return {'status': 'deferred'} ##deffered, use readfinished and retrievelastdata to receive


    ##Check if last read request has been finished
    ##@return error or value

    def jsonrpc_readfinished(self):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        if self.waiting_for_read == False:
            return {'status': 'error',
                    'error': 'not_waiting'}

        return {'status': 'ok', 'value': self.read_finished}

    ##Retrieve last data read from slave, if avaiable
    ##@return error or data

    def jsonrpc_retrievelastdata(self, formatted=True):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        if self.waiting_for_read == False:
            return {'status': 'error',
                    'error': 'no_request'}

        if self.read_finished == False:
            return {'status': 'error',
                    'error': 'waiting_read'}

        self.waiting_for_read = False

        if formatted:
            #get slave
            addr = self.read_slave_addr
            if addr.bus_number == 254:
                s = self.master.virtualDeviceList[addr.global_id()]
            else:
                s = self.master.detectedSlaveList[addr.global_id()]

            #send formatted data
            ret_data = s.hbusSlaveObjects[int(self.read_slave_object)].getFormattedValue()
        else:
            ret_data = [ord(x) for x in self.read_data]

        return {'status': 'ok', 'value': ret_data}

    ##Data read finished callback

    def _read_object_callback(self, data):
        self.read_finished = True
        #self.logger.debug('got: {}'.format(data))
        self.read_data = data

    ##Data read timeout callback

    def _read_object_timeout_callback(self, data):
        self.read_finished = True
        self.read_data =  {'status': 'error',
                           'error': 'read_timeout'}
        
    ##Writes a value to an object
    #@param address device address
    #@param number object number
    #@param value value to be written
    #@return data to be JSON structured
    def jsonrpc_writeobject(self,address,number,value):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        try:
            addr = hbus_address_from_string(address)
        except ValueError:
            return {'status' : 'error',
                    'error' : 'malformed address'}
        
        if not addr.global_id() in self.master.detectedSlaveList.keys():
            
            #device does not exist
            return {'status': 'error',
                    'error': 'invalid_device'}
        
        if not int(number) in self.master.detectedSlaveList[addr.global_id()].hbusSlaveObjects.keys():
            
            #object does not exist
            return {'status': 'error',
                    'error': 'invalid_object'}
        
        #value formatting IS MISSING
        if self.master.writeSlaveObject(addr,int(number), int(value)):
            return {'status': 'ok'}

        return {'status': 'error',
                'error': 'read_only'}

    def jsonrpc_checkslaves(self):
        if self._is_operational() is False:
            return {'status': 'error', 'error': 'not_available'}
        self.master.checkSlaves()

    def jsonrpc_masterstate(self):
        return {'status': 'ok', 'value': self.master.masterState}
