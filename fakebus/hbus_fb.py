#coding=utf-8

"""Fake bus for debugging without actual hardware connected
  @package hbus_fb
  @author Bruno Morais <brunosmmm@gmail.com>
  @since 11/17/2014
  @todo implement fake bus device structure
  @todo load device configuration from files
"""

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
import struct
import logging
from hbus_base import *
from hbus_constants import *
from hbusslaves import *
from collections import deque

import ConfigParser ##for fakebus device tree emulation
import os

##Configuration file options equivalence
CONFIG_DATA_TYPE = {'I' : HbusObjDataType.dataTypeInt,
                    'U' : HbusObjDataType.dataTypeUnsignedInt,
                    'B' : HbusObjDataType.dataTypeByte,
                    'F' : HbusObjDataType.dataTypeFixedPoint}

CONFIG_DATA_TYPE_INFO = {'h' : HbusObjDataType.dataTypeByteHex,
                         'd' : HbusObjDataType.dataTypeByteDec,
                         'o' : HbusObjDataType.dataTypeByteOct,
                         'b' : HbusObjDataType.dataTypeByteBin,
                         'B' : HbusObjDataType.dataTypeByteBool,
                         'p' : HbusObjDataType.dataTypeUintPercent,
                         'L' : HbusObjDataType.dataTypeUintLinPercent,
                         'l' : HbusObjDataType.dataTypeUintLogPercent,
                         't' : HbusObjDataType.dataTypeUintTime,
                         'D' : HbusObjDataType.dataTypeUintDate,
                         'u' : HbusObjDataType.dataTypeUintNone}

CONFIG_LEVEL = {0 : HbusObjLevel.level0,
                1 : HbusObjLevel.level1,
                2 : HbusObjLevel.level2,
                3 : HbusObjLevel.level3}

FAKEBUS_MASTER_ADDRESS = hbusDeviceAddress(0, 0)


class FakeBusDeviceStatus(object):
    """Device internal status emulation for addressing simulation"""
    deviceIdle = 0
    deviceAddressing1 = 1 #first stage, device does buslock
    deviceAddressing2 = 2 #second stage, device awaits
    deviceAddressing3 = 3 #finishes addressing
    deviceEnumerated = 4

class FakeBusDevice(HbusDevice):
    """Device data structure, inherits HbusSlaveInfo
    and adds objects to emulate adressing"""

    ##Device internal status emulation
    deviceStatus = FakeBusDeviceStatus.deviceIdle

    def create_query_response(self, objnum):
        if objnum == 0:
            #special case
            #OBJECT_INFO data

            objectInfo = (0,
                          4+len(self.hbusSlaveDescription),
                          hbusSlaveObjectPermissions.hbusSlaveObjectRead,
                          8, 0,
                          len(self.hbusSlaveDescription),
                          self.hbusSlaveDescription)

            return objectInfo

        elif objnum in self.hbusSlaveObjects.keys():
            objectInfo = (objnum,
                          4+len(self.hbusSlaveObjects[objnum].objectDescription),
                          self.hbusSlaveObjects[objnum].objectPermissions,
                          self.hbusSlaveObjects[objnum].objectSize,
                          self.hbusSlaveObjects[objnum].objectDataTypeInfo,
                          len(self.hbusSlaveObjects[objnum].objectDescription),
                          self.hbusSlaveObjects[objnum].objectDescription)
            return objectInfo
        else:
            #object does not exist
            return None

    def create_read_response(self, objnum):
        if objnum == 0:

            uid = struct.pack('i', self.hbusSlaveUniqueDeviceInfo)

            objectListInfo = (0, 8, self.hbusSlaveObjectCount, self.hbusSlaveEndpointCount, self.hbusSlaveInterruptCount, self.hbusSlaveCapabilities,uid)

            return objectListInfo
        elif objnum in self.hbusSlaveObjects.keys():

            ##@todo generate proper object size!
            objectRead = (0, self.hbusSlaveObjects[objnum].objectSize, self.hbusSlaveObjects[objnum].objectLastValue)

            return objectRead
        else:
            return None

class FakeBusSerialPort(Protocol):
    """Fake bus main class"""

    ##Constructor, initializes
    def __init__(self):
        self.logger = logging.getLogger('hbussd.fakebus')
        self.logger.debug("fakebus active")
        self.dataBuffer = []
        self.rxState = hbusMasterRxState.hbusRXSBID
        self.config = ConfigParser.ConfigParser()
        self.deviceList = {}
        try:
            self.config.read('fakebus/fakebus.config')
            self.build_bus()
        except:
            self.logger.debug("no configuration file found")

        self.busAddrToUID = {}
        self.busState = hbusBusStatus.hbusBusFree
        self.addressingDevice = None
        self.addressingQueue = deque()

    ##Master connected to fakebus
    def connectionMade(self):
        self.logger.debug("hbus master connected to fakebus")

    ##Data reception state machine, similar to master's
    # @param data data chunk received
    def dataReceived(self, data):

        #make state machine work byte by byte
        for byte in data:

            if self.rxState == hbusMasterRxState.hbusRXSBID:
                self.dataBuffer.append(byte)
                self.rxState = hbusMasterRxState.hbusRXSDID
            elif self.rxState == hbusMasterRxState.hbusRXSDID:
                self.dataBuffer.append(byte)
                self.rxState = hbusMasterRxState.hbusRXTBID
            elif self.rxState == hbusMasterRxState.hbusRXTBID:
                self.dataBuffer.append(byte)
                self.rxState = hbusMasterRxState.hbusRXTDID
            elif self.rxState == hbusMasterRxState.hbusRXTDID:
                self.dataBuffer.append(byte)
                self.rxState = hbusMasterRxState.hbusRXCMD
            elif self.rxState == hbusMasterRxState.hbusRXCMD:
                self.dataBuffer.append(byte)
                if ord(byte) in HBUS_SCMDBYTELIST:
                    self.rxState = hbusMasterRxState.hbusRXSTP
                elif ord(byte) == HBUSCOMMAND_SOFTRESET.commandByte: #softreset is different, doesnt specify addr field
                    self.rxState = hbusMasterRxState.hbusRXPSZ
                else:
                    self.rxState = hbusMasterRxState.hbusRXADDR
            elif self.rxState == hbusMasterRxState.hbusRXADDR:
                self.dataBuffer.append(byte)
                if ord(self.dataBuffer[4]) in HBUS_SACMDBYTELIST:
                    self.rxState = hbusMasterRxState.hbusRXSTP
                else:
                    self.rxState = hbusMasterRxState.hbusRXPSZ
            elif self.rxState == hbusMasterRxState.hbusRXPSZ:
                self.lastParamSize = ord(byte)
                self.dataBuffer.append(byte)
                if ord(self.dataBuffer[4]) == HBUSCOMMAND_STREAMW.commandByte or ord(self.dataBuffer[4]) == HBUSCOMMAND_STREAMR.commandByte:
                    self.rxState = hbusMasterRxState.hbusRXSTP
                else:
                    if ord(byte) > 0:
                        self.rxState = hbusMasterRxState.hbusRXPRM
                    else:
                        self.rxState = hbusMasterRxState.hbusRXSTP
            elif self.rxState == hbusMasterRxState.hbusRXPRM:
                #softreset has no addr field
                ##@todo must update whole specification and force softreset command to have an addr field to avoid further problems
                ##@todo undo this hack when modification is done
                #start hack
                if ord(self.dataBuffer[4]) == HBUSCOMMAND_SOFTRESET.commandByte:
                    count = 5
                else:
                    count = 6
                if len(self.dataBuffer) <= (count + self.lastParamSize):
                #end hack
                    self.dataBuffer.append(byte)
                else:
                    if ord(byte) == 0xFF:
                        self.dataBuffer.append(byte)
                        #finished Packet

                        self.rxState = hbusMasterRxState.hbusRXSBID
                        self.parse_packet(self.dataBuffer)
                        self.dataBuffer = []
                        return
                    else:
                        #malformed packet, ignore
                        self.rxState = hbusMasterRxState.hbusRXSBID
                        self.logger.debug("ignored malformed packet from master")
                        self.logger.debug("packet size %d, dump: %s", len(self.dataBuffer), [hex(ord(x)) for x in self.dataBuffer])
                        self.dataBuffer = []
                        return
            elif self.rxState == hbusMasterRxState.hbusRXSTP:
                self.dataBuffer.append(byte)
                if ord(byte) == 0xFF:
                    #finished
                    self.rxState = hbusMasterRxState.hbusRXSBID
                    self.parse_packet(self.dataBuffer)
                    self.dataBuffer = []
                    return
                else:
                    #malformed packet, ignore
                    self.rxState = hbusMasterRxState.hbusRXSBID
                    self.logger.debug("ignored malformed packet from master")
                    self.logger.debug("packet size %d dump: %s", len(self.dataBuffer), [hex(ord(x)) for x in self.dataBuffer])
                    self.dataBuffer = []
                    return
            else:
                #unknown state!
                self.logger.error("unknown state reached!")
                raise IOError("fatal fakebus error")
                self.rxState = hbusMasterRxState.hbusRXSBID
                self.dataBuffer = []
                return

    ##Parse a complete packet
    # @param packet packet received by state machine
    def parse_packet(self, packet):

        psource = hbusDeviceAddress(ord(packet[0]), ord(packet[1]))
        pdest = hbusDeviceAddress(ord(packet[2]), ord(packet[3]))

        #decode packets, respond on BUS 0
        if ord(packet[2]) != 0 and ord(packet[2]) != 0xff:
            return

        #check if bus is locked
        if self.busState == hbusBusStatus.hbusBusLockedOther:
            return #locked with others, we do nothing
        elif self.busState == hbusBusStatus.hbusBusLockedThis:
            #look for special cases such as when receiving SEARCH or KEYSET commands indicating attribution of an address
            if self.addressingDevice != None:
                if ord(packet[4]) == HBUSCOMMAND_GETCH.commandByte and ord(packet[5]) == 0 and self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing2:
                    #send object 0 to master
                    ##@todo MAKE object 0 from internal info
                    #self.send_packet()
                    params = self.deviceList[self.addressingDevice].create_read_response(0)

                    self.send_packet(HBUSCOMMAND_RESPONSE, FAKEBUS_MASTER_ADDRESS, hbusDeviceAddress(0, 255), params)
                    self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceAddressing3
                    return

                elif ord(packet[4]) == HBUSCOMMAND_SEARCH.commandByte or ord(packet[4]) == HBUSCOMMAND_KEYSET.commandByte and self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing3:
                    #attribute new address and register
                    self.deviceList[self.addressingDevice].hbusSlaveAddress = hbusDeviceAddress(ord(packet[2]), ord(packet[3]))
                    self.busAddrToUID[pdest.getGlobalID()] = self.deviceList[self.addressingDevice].hbusSlaveUniqueDeviceInfo
                    #self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceEnumerated

                    #addressing will finish when device sends a busunlock
                    self.address_next_dev()
                    return
                else:
                    #makes no sense
                    return

        #detect buslock commands globally
        if ord(packet[4]) == HBUSCOMMAND_BUSLOCK.commandByte:
            if pdest.getGlobalID() in self.busAddrToUID.keys():
                #locking with one of the fake devices
                self.busState = hbusBusStatus.hbusBusLockedThis
            else:
                self.busState = hbusBusStatus.hbusBusLockedOther
            return

        #detect busunlock commands
        if ord(packet[4]) == HBUSCOMMAND_BUSUNLOCK.commandByte:
            self.busState = hbusBusStatus.hbusBusFree
            return

        #detect broadcast messages
        if ord(packet[3]) == 0xff:
            #this is a broadcast message

            if ord(packet[4]) == HBUSCOMMAND_SEARCH.commandByte:
                #this is a SEARCH command, see if there are slaves
                #that were not enumerated and starts addressing
                for device in self.deviceList.values():
                    if device.deviceStatus == FakeBusDeviceStatus.deviceIdle:
                        #start addressing
                        device.deviceStatus = FakeBusDeviceStatus.deviceAddressing1
                        #queue for addressing
                        self.addressingQueue.appendleft(device.hbusSlaveUniqueDeviceInfo)

                self.address_next_dev()
                #done
                return
            elif ord(packet[4]) == HBUSCOMMAND_SOFTRESET.commandByte:
                #reset command
                return #ignore for now, nothing to do
            elif ord(packet[4]) == HBUSCOMMAND_KEYSET.commandByte:
                #this is quite uncharted territory yet
                return
            elif ord(packet[4]) == HBUSCOMMAND_KEYRESET.commandByte:
                return
            elif ord(packet[4]) == HBUSCOMMAND_SETCH.commandByte:
                #might be a broadcast object, this is not really implemented yet
                return
            else:
                return #other commands cannot be used on broadcast

        try:
            target_uid = self.busAddrToUID[pdest.getGlobalID()]
        except:
            #device is not enumerated in this bus
            return

        if ord(packet[4]) == HBUSCOMMAND_SEARCH.commandByte:
            #ping some device
            self.send_packet(HBUSCOMMAND_ACK, FAKEBUS_MASTER_ADDRESS, self.deviceList[target_uid].hbusSlaveAddress)
            return
        elif ord(packet[4]) == HBUSCOMMAND_QUERY.commandByte:
            #querying some object
            params = self.deviceList[target_uid].create_query_response(ord(packet[5]))
            if params == None:
                #problem retrieving object, ignore
                return
            self.send_packet(HBUSCOMMAND_QUERY_RESP, FAKEBUS_MASTER_ADDRESS, self.deviceList[target_uid].hbusSlaveAddress, params)
            return
        elif ord(packet[4]) == HBUSCOMMAND_GETCH.commandByte:
            #reading some object
            params = self.deviceList[target_uid].create_read_response(ord(packet[5]))
            if params == None:
                #problem retrieving object, ignore
                return
            self.send_packet(HBUSCOMMAND_RESPONSE, FAKEBUS_MASTER_ADDRESS, self.deviceList[target_uid].hbusSlaveAddress, params)
            return

    def send_packet(self, command, dest, source, params=()):

        busop = hbusOperation(hbusInstruction(command, len(params), params), dest, source)

        if command == HBUSCOMMAND_BUSLOCK:
            self.busState = hbusBusStatus.hbusBusLockedThis
        elif command == HBUSCOMMAND_BUSUNLOCK:
            self.busState = hbusBusStatus.hbusBusFree

        self.transport.write(busop.getString())

    ##Process addressing of devices
    def address_next_dev(self):

        if self.addressingDevice == None:
            if len(self.addressingQueue) > 0:
                self.addressingDevice = self.addressingQueue.pop()
            else:
                return

        #first stage
        if self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing1:
        #do a buslock
            self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceAddressing2
            self.send_packet(HBUSCOMMAND_BUSLOCK, FAKEBUS_MASTER_ADDRESS, hbusDeviceAddress(0, 255))

            #done for now
            return
        elif self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing3:
            #do a busunlock
            self.send_packet(HBUSCOMMAND_BUSUNLOCK, FAKEBUS_MASTER_ADDRESS, self.deviceList[self.addressingDevice].hbusSlaveAddress)
            self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceEnumerated
            self.addressingDevice = None

            #Must immediately start processing next slave!
            reactor.callLater(0.1, self.address_next_dev)

            return

    ##Parse configuration files and builds bus structure
    def build_bus(self):

        self.logger.debug("start adding fake devices...")
        #get device path
        devpath = 'fakebus/'+self.config.get('fakebus', 'object_dir')

        devfiles = [x for x in os.listdir(devpath) if x.endswith('.config')]

        #read device files to build tree
        devconf = ConfigParser.ConfigParser()
        for devfile in devfiles:
            device = FakeBusDevice(None)
            devconf.read(devpath+devfile)

            #start building device
            try:
                if devconf.getboolean('device', 'dont_read') == True:
                    continue
            except:
                pass

            #UID
            device.hbusSlaveUniqueDeviceInfo = int(devconf.get('device', 'uid'), 16)
            device.hbusSlaveDescription = devconf.get('device', 'descr')
            device.hbusSlaveObjectCount = devconf.getint('device', 'object_count')
            device.hbusSlaveEndpointCount = devconf.getint('device', 'endpoint_count')
            device.hbusSlaveInterruptCount = devconf.getint('device', 'int_count')

            #capabilities, must generate flags
            ##@todo generate flags for capabilities from configuration file

            for section in devconf.sections():
                m = re.match(r"object([0-9+])", section)
                if m == None:
                    continue


                obj = HbusDeviceObject()

                #generate flags for objectPermissions
                can_read = devconf.getboolean(section, 'can_read')
                can_write = devconf.getboolean(section, 'can_write')

                if can_read == True:
                    if can_write == True:
                        obj.objectPermissions = hbusSlaveObjectPermissions.hbusSlaveObjectReadWrite
                    else:
                        obj.objectPermissions = hbusSlaveObjectPermissions.hbusSlaveObjectRead
                elif can_write == True:
                    obj.objectPermissions = hbusSlaveObjectPermissions.hbusSlaveObjectWrite
                else:
                    #error!
                    pass #for now

                obj.objectCrypto = devconf.getboolean(section, 'is_crypto')
                obj.objectHidden = devconf.getboolean(section, 'hidden')
                obj.objectDescription = devconf.get(section, 'descr')
                obj.objectSize = devconf.getint(section, 'size')

                #must generate value from configfile
                data_type = devconf.get(section, 'data_type')
                data_type_info = devconf.get(section, 'data_type_info')
                level = devconf.getint(section, 'level')

                try:
                    obj.objectDataType = CONFIG_DATA_TYPE[data_type]
                    obj.objectDataTypeInfo = CONFIG_DATA_TYPE_INFO[data_type_info]
                    obj.objectLevel = CONFIG_LEVEL[level]
                except:
                    #invalid data type
                    pass #for now

                #must interpret dummy return value in file
                raw_value = devconf.get(section, 'value')
                obj.objectLastValue = self.list_val_to_int(raw_value, obj.objectDataType)

                #when finished
                ##add to obj list
                device.hbusSlaveObjects[int(m.group(1))] = obj

            #when finished
            ##add to device list
            self.deviceList[device.hbusSlaveUniqueDeviceInfo] = device
            self.logger.debug('fake device "'+device.hbusSlaveDescription+'" <'+hex(device.hbusSlaveUniqueDeviceInfo)+'> added')

    def list_val_to_int(self, value, valuetype):

        if valuetype == HbusObjDataType.dataTypeInt:
            return int(value)
        elif valuetype == HbusObjDataType.dataTypeByte:
            value = value.split(' ')
            int_value = 0
            for i in range(0, len(value)):
                int_value = int_value + int(value[i], 16) << i

            return int_value
        elif valuetype == HbusObjDataType.dataTypeFixedPoint:
            return 0 ##@todo fixed point parsing
        elif valuetype == HbusObjDataType.dataTypeUnsignedInt:
            return int(value)
        else:
            return 0

