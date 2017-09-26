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
from ..hbus.base import HbusDeviceAddress, HbusOperation, HbusInstruction
from ..hbus.constants import (HbusObjectPermissions, HbusRXState,
                              HbusBusState, HBUS_SCMDBYTELIST,
                              HBUS_SACMDBYTELIST,
                              HBUSCOMMAND_SOFTRESET, HBUSCOMMAND_STREAMR,
                              HBUSCOMMAND_STREAMW, HBUSCOMMAND_GETCH,
                              HBUSCOMMAND_SETCH, HBUSCOMMAND_SEARCH,
                              HBUSCOMMAND_KEYSET, HBUSCOMMAND_KEYRESET,
                              HBUSCOMMAND_QUERY, HBUSCOMMAND_RESPONSE,
                              HBUSCOMMAND_BUSLOCK, HBUSCOMMAND_BUSUNLOCK,
                              HBUSCOMMAND_ACK, HBUSCOMMAND_QUERY_RESP)
from ..hbus.slaves import (HbusObjDataType, HbusObjLevel, HbusDevice,
                           HbusDeviceObject)
from collections import deque
import re

import configparser ##for fakebus device tree emulation
import os

##Configuration file options equivalence
CONFIG_DATA_TYPE = {'I': HbusObjDataType.dataTypeInt,
                    'U': HbusObjDataType.dataTypeUnsignedInt,
                    'B': HbusObjDataType.type_byte,
                    'F': HbusObjDataType.dataTypeFixedPoint}

CONFIG_DATA_TYPE_INFO = {'h': HbusObjDataType.dataTypeByteHex,
                         'd': HbusObjDataType.dataTypeByteDec,
                         'o': HbusObjDataType.dataTypeByteOct,
                         'b': HbusObjDataType.dataTypeByteBin,
                         'B': HbusObjDataType.dataTypeByteBool,
                         'p': HbusObjDataType.dataTypeUintPercent,
                         'L': HbusObjDataType.dataTypeUintLinPercent,
                         'l': HbusObjDataType.dataTypeUintLogPercent,
                         't': HbusObjDataType.dataTypeUintTime,
                         'D': HbusObjDataType.dataTypeUintDate,
                         'u': HbusObjDataType.dataTypeUintNone}

CONFIG_LEVEL = {0: HbusObjLevel.level0,
                1: HbusObjLevel.level1,
                2: HbusObjLevel.level2,
                3: HbusObjLevel.level3}

FAKEBUS_MASTER_ADDRESS = HbusDeviceAddress(0, 0)
SYS_CONFIG_PATH = '/etc/hbussd/fakebus'


class FakeBusDeviceStatus(object):
    """Device internal status emulation for addressing simulation"""
    deviceIdle = 0
    deviceAddressing1 = 1  # first stage, device does buslock
    deviceAddressing2 = 2  # second stage, device awaits
    deviceAddressing3 = 3  # finishes addressing
    deviceEnumerated = 4

class FakeBusDevice(HbusDevice):
    """Device data structure, inherits HbusSlaveInfo
    and adds objects to emulate adressing"""

    def __init__(self, static_address=None):
        super(FakeBusDevice, self).__init__(static_address)

        ##Device internal status emulation
        self.deviceStatus = FakeBusDeviceStatus.deviceIdle

        if static_address is not None:
            self.deviceStatus = FakeBusDeviceStatus.deviceEnumerated

    def create_query_response(self, objnum):
        """Creates a response to a QUERY command sent by the master
        @param objnum object number
        """
        if objnum == 0:
            #special case
            #OBJECT_INFO data

            objectinfo = (0,
                          4+len(self.hbusSlaveDescription),
                          HbusObjectPermissions.READ,
                          8, 0,
                          len(self.hbusSlaveDescription),
                          self.hbusSlaveDescription)

            return objectinfo

        elif objnum in list(self.hbusSlaveObjects.keys()):
            # why is different from the standard implementation?

            object_flags = self.hbusSlaveObjects[objnum].permissions +\
                           self.hbusSlaveObjects[objnum].objectLevel +\
                           self.hbusSlaveObjects[objnum].objectDataType

            objectinfo = (objnum,
                          4+len(self.hbusSlaveObjects[objnum].description),
                          object_flags,
                          self.hbusSlaveObjects[objnum].size,
                          self.hbusSlaveObjects[objnum].objectDataTypeInfo,
                          len(self.hbusSlaveObjects[objnum].description),
                          self.hbusSlaveObjects[objnum].description)
            return objectinfo
        else:
            #object does not exist
            return None

    def create_read_response(self, objnum):
        """Creates a response to a GETCH command sent by the master
        @param objnum object number"""
        if objnum == 0:

            uid = struct.pack('I', self.hbusSlaveUniqueDeviceInfo)

            obj_list_info = (0,
                             8,
                             self.hbusSlaveObjectCount+1,
                             self.hbusSlaveEndpointCount,
                             self.hbusSlaveInterruptCount,
                             self.hbusSlaveCapabilities,
                             uid)

            return obj_list_info

        elif objnum in list(self.hbusSlaveObjects.keys()):

            ##@todo generate proper object size!
            value_list = []
            last_value = self.hbusSlaveObjects[objnum].last_value
            for i in range(0, self.hbusSlaveObjects[objnum].size):
                value_list.append((last_value & (0xff << i*8)) >> i*8)

            object_read = [0,
                           self.hbusSlaveObjects[objnum].size]
            object_read.extend(value_list)

            return object_read
        else:
            return None

class FakeBusSerialPort(Protocol):
    """Fake bus main class"""

    ##Constructor, initializes
    def __init__(self):
        self.logger = logging.getLogger('hbussd.fakebus')
        self.logger.debug("fakebus active")
        self.dataBuffer = []
        self.rxState = HbusRXState.SBID
        self.config = configparser.ConfigParser()
        self.deviceList = {}
        self.busAddrToUID = {}

        self.config_path = 'config/fakebus'
        try:
            self.config.read_file(open(os.path.join(self.config_path,
                                                    'fakebus.config')))
        except:
            self.logger.info("reading default configuration file")
            self.config.read_file(open(os.path.join(SYS_CONFIG_PATH,
                                                    'fakebus.config')))
            self.config_path = SYS_CONFIG_PATH

        self.build_bus()

        self.busState = HbusBusState.FREE
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

            if self.rxState == HbusRXState.SBID:
                self.dataBuffer.append(byte)
                self.rxState = HbusRXState.SDID
            elif self.rxState == HbusRXState.SDID:
                self.dataBuffer.append(byte)
                self.rxState = HbusRXState.TBID
            elif self.rxState == HbusRXState.TBID:
                self.dataBuffer.append(byte)
                self.rxState = HbusRXState.TDID
            elif self.rxState == HbusRXState.TDID:
                self.dataBuffer.append(byte)
                self.rxState = HbusRXState.CMD
            elif self.rxState == HbusRXState.CMD:
                self.dataBuffer.append(byte)
                if byte in HBUS_SCMDBYTELIST:
                    self.rxState = HbusRXState.STP
                elif byte == HBUSCOMMAND_SOFTRESET.cmd_byte: #softreset is different, doesnt specify addr field
                    self.rxState = HbusRXState.PSZ
                else:
                    self.rxState = HbusRXState.ADDR
            elif self.rxState == HbusRXState.ADDR:
                self.dataBuffer.append(byte)
                if self.dataBuffer[4] in HBUS_SACMDBYTELIST:
                    self.rxState = HbusRXState.STP
                else:
                    self.rxState = HbusRXState.PSZ
            elif self.rxState == HbusRXState.PSZ:
                self.lastParamSize = byte
                self.dataBuffer.append(byte)
                if self.dataBuffer[4] == HBUSCOMMAND_STREAMW.cmd_byte or\
                   self.dataBuffer[4] == HBUSCOMMAND_STREAMR.cmd_byte:
                    self.rxState = HbusRXState.STP
                else:
                    if byte > 0:
                        self.rxState = HbusRXState.PRM
                    else:
                        self.rxState = HbusRXState.STP
            elif self.rxState == HbusRXState.PRM:
                #softreset has no addr field
                ##@todo must update whole specification and force softreset command to have an addr field to avoid further problems
                ##@todo undo this hack when modification is done
                #start hack
                if self.dataBuffer[4] == HBUSCOMMAND_SOFTRESET.cmd_byte:
                    count = 5
                else:
                    count = 6
                if len(self.dataBuffer) <= (count + self.lastParamSize):
                #end hack
                    self.dataBuffer.append(byte)
                else:
                    if byte == 0xFF:
                        self.dataBuffer.append(byte)
                        #finished Packet

                        self.rxState = HbusRXState.SBID
                        self.parse_packet(self.dataBuffer)
                        self.dataBuffer = []
                        return
                    else:
                        #malformed packet, ignore
                        self.rxState = HbusRXState.SBID
                        self.logger.debug("ignored malformed packet from master @PRM")
                        self.logger.debug("info: expected to have received {} bytes".format(count+self.lastParamSize))
                        self.logger.debug("packet size %d, dump: %s", len(self.dataBuffer), [hex(ord(x)) for x in self.dataBuffer])
                        self.dataBuffer = []
                        return
            elif self.rxState == HbusRXState.STP:
                self.dataBuffer.append(byte)
                if byte == 0xFF:
                    #finished
                    self.rxState = HbusRXState.SBID
                    self.parse_packet(self.dataBuffer)
                    self.dataBuffer = []
                    return
                else:
                    #malformed packet, ignore
                    self.rxState = HbusRXState.SBID
                    self.logger.debug("ignored malformed packet from master @STP")
                    self.logger.debug("packet size %d dump: %s", len(self.dataBuffer), [hex(ord(x)) for x in self.dataBuffer])
                    self.dataBuffer = []
                    return
            else:
                #unknown state!
                self.logger.error("unknown state reached!")
                raise IOError("fatal fakebus error")
                self.rxState = HbusRXState.SBID
                self.dataBuffer = []
                return

    ##Parse a complete packet
    # @param packet packet received by state machine
    def parse_packet(self, packet):

        psource = HbusDeviceAddress(packet[0], packet[1])
        pdest = HbusDeviceAddress(packet[2], packet[3])

        #decode packets, respond on BUS 0
        if packet[2] != 0 and packet[2] != 0xff:
            return

        #check if bus is locked
        if self.busState == HbusBusState.LOCKED_OTHER:
            return #locked with others, we do nothing
        elif self.busState == HbusBusState.LOCKED_THIS:
            #look for special cases such as when receiving SEARCH or KEYSET commands indicating attribution of an address
            if self.addressingDevice != None:
                if packet[4] == HBUSCOMMAND_GETCH.cmd_byte and\
                   packet[5] == 0 and\
                   self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing2:
                    #send object 0 to master
                    ##@todo MAKE object 0 from internal info
                    #self.send_packet()
                    params = self.deviceList[self.addressingDevice].create_read_response(0)

                    self.send_packet(HBUSCOMMAND_RESPONSE, FAKEBUS_MASTER_ADDRESS, HbusDeviceAddress(0, 255), params)
                    self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceAddressing3
                    return

                elif packet[4] == HBUSCOMMAND_SEARCH.cmd_byte or\
                     packet[4] == HBUSCOMMAND_KEYSET.cmd_byte and\
                     self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing3:
                    #attribute new address and register
                    self.deviceList[self.addressingDevice].hbusSlaveAddress =\
                        HbusDeviceAddress (packet[2], packet[3])
                    self.busAddrToUID[pdest.global_id()] = self.deviceList[self.addressingDevice].hbusSlaveUniqueDeviceInfo
                    #self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceEnumerated

                    #addressing will finish when device sends a busunlock
                    self.address_next_dev()
                    return
                else:
                    #makes no sense
                    return

        #detect buslock commands globally
        if packet[4] == HBUSCOMMAND_BUSLOCK.cmd_byte:
            if pdest.global_id() in list(self.busAddrToUID.keys()):
                #locking with one of the fake devices
                self.busState = HbusBusState.LOCKED_THIS
            else:
                self.busState = HbusBusState.LOCKED_OTHER
            return

        #detect busunlock commands
        if packet[4] == HBUSCOMMAND_BUSUNLOCK.cmd_byte:
            self.busState = HbusBusState.FREE
            return

        #detect broadcast messages
        if packet[3] == 0xff:
            #this is a broadcast message

            if packet[4] == HBUSCOMMAND_SEARCH.cmd_byte:
                #this is a SEARCH command, see if there are slaves
                #that were not enumerated and starts addressing
                for device in list(self.deviceList.values()):
                    if device.deviceStatus == FakeBusDeviceStatus.deviceIdle:
                        #start addressing
                        device.deviceStatus = FakeBusDeviceStatus.deviceAddressing1
                        #queue for addressing
                        self.addressingQueue.appendleft(device.hbusSlaveUniqueDeviceInfo)

                self.address_next_dev()
                #done
                return
            elif packet[4] == HBUSCOMMAND_SOFTRESET.cmd_byte:
                #reset command
                return #ignore for now, nothing to do
            elif packet[4] == HBUSCOMMAND_KEYSET.cmd_byte:
                #this is quite uncharted territory yet
                return
            elif packet[4] == HBUSCOMMAND_KEYRESET.cmd_byte:
                return
            elif packet[4] == HBUSCOMMAND_SETCH.cmd_byte:
                #might be a broadcast object, this is not really implemented yet
                return
            else:
                return #other commands cannot be used on broadcast

        try:
            target_uid = self.busAddrToUID[pdest.global_id()]
        except:
            #device is not enumerated in this bus
            return

        if packet[4] == HBUSCOMMAND_SEARCH.cmd_byte:
            #ping some device
            self.send_packet(HBUSCOMMAND_ACK, FAKEBUS_MASTER_ADDRESS, self.deviceList[target_uid].hbusSlaveAddress)
            return
        elif packet[4] == HBUSCOMMAND_QUERY.cmd_byte:
            #querying some object
            params = self.deviceList[target_uid].create_query_response(packet[5])
            if params == None:
                #problem retrieving object, ignore
                return
            self.send_packet(HBUSCOMMAND_QUERY_RESP,
                             FAKEBUS_MASTER_ADDRESS,
                             self.deviceList[target_uid].hbusSlaveAddress,
                             params)
            return
        elif packet[4] == HBUSCOMMAND_GETCH.cmd_byte:
            #reading some object
            params = self.deviceList[target_uid].create_read_response(packet[5])
            if params == None:
                #problem retrieving object, ignore
                return
            self.send_packet(HBUSCOMMAND_RESPONSE, FAKEBUS_MASTER_ADDRESS, self.deviceList[target_uid].hbusSlaveAddress, params)
            return

    def send_packet(self, command, dest, source, params=()):

        busop = HbusOperation(HbusInstruction(command,
                                              len(params),
                                              params),
                              dest,
                              source)

        if command == HBUSCOMMAND_BUSLOCK:
            self.busState = HbusBusState.LOCKED_THIS
        elif command == HBUSCOMMAND_BUSUNLOCK:
            self.busState = HbusBusState.FREE

        #self.logger.debug('writing: {}'.format(busop.get_string()))
        self.transport.write(busop.get_string())

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
            self.send_packet(HBUSCOMMAND_BUSLOCK, FAKEBUS_MASTER_ADDRESS, HbusDeviceAddress(0, 255))

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
        devpath = os.path.join(self.config_path,
                               self.config.get('fakebus', 'object_dir'))

        devfiles = [x for x in os.listdir(devpath) if x.endswith('.config')]

        #read device files to build tree
        for devfile in devfiles:

            #read config
            devconf = configparser.ConfigParser()
            devconf.read(devpath+devfile)

            #detect static addressed device
            static_addr = None
            try:
                static_addr = devconf.get('device', 'static_addr')
            except:
                pass

            if static_addr is not None:
                m = re.match(r'([0-9]+):([0-9]+)', static_addr.strip())

                if m is not None:
                    static_addr = HbusDeviceAddress(int(m.group(1)), int(m.group(2)))


            device = FakeBusDevice(static_addr)

            #start building device
            try:
                if devconf.getboolean('device', 'dont_read') == True:
                    self.logger.debug('ignored device description in {}'.format(devfile))
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

            #store addr->id correlation
            if static_addr is not None:
                self.busAddrToUID[static_addr.global_id()] = device.hbusSlaveUniqueDeviceInfo

            for section in devconf.sections():
                m = re.match(r"object([0-9]+)", section)
                if m == None:
                    continue

                obj = HbusDeviceObject()

                #generate flags for objectPermissions
                can_read = devconf.getboolean(section, 'can_read')
                can_write = devconf.getboolean(section, 'can_write')

                if can_read == True:
                    if can_write == True:
                        obj.permissions = HbusObjectPermissions.READ_WRITE
                    else:
                        obj.permissions = HbusObjectPermissions.READ
                elif can_write == True:
                    obj.permissions = HbusObjectPermissions.WRITE
                else:
                    #error!
                    pass #for now

                obj.is_crypto = devconf.getboolean(section, 'is_crypto')
                obj.hidden = devconf.getboolean(section, 'hidden')
                obj.description = devconf.get(section, 'descr')
                size = devconf.getint(section, 'size')
                if size < 1 or size > 4:
                    # invalid size
                    self.logger.warning('invalid object size detected')
                    if size < 1:
                        obj.size = 1
                    elif size > 4:
                        obj.size = 4
                else:
                    obj.size = size

                #must generate value from configfile
                data_type = devconf.get(section, 'data_type')
                data_type_info = devconf.get(section, 'data_type_info')
                level = devconf.getint(section, 'level')

                try:
                    obj.objectDataType = CONFIG_DATA_TYPE[data_type]
                    if obj.objectDataType != HbusObjDataType.dataTypeFixedPoint:
                        obj.objectDataTypeInfo = CONFIG_DATA_TYPE_INFO[data_type_info]
                    else:
                        obj.objectDataTypeInfo = int(data_type_info)
                    obj.objectLevel = CONFIG_LEVEL[level]
                except:
                    #invalid data type
                    obj.objectDataType = CONFIG_DATA_TYPE['U']
                    obj.objectDataTypeInfo = CONFIG_DATA_TYPE_INFO['u']

                #must interpret dummy return value in file
                raw_value = devconf.get(section, 'value')
                obj.last_value = self.list_val_to_int(raw_value, obj.objectDataType)

                #when finished
                ##add to obj list
                device.hbusSlaveObjects[int(m.group(1))] = obj

            #when finished
            ##add to device list
            self.deviceList[device.hbusSlaveUniqueDeviceInfo] = device
            self.logger.debug('fake device "'+device.hbusSlaveDescription+'" <'+hex(device.hbusSlaveUniqueDeviceInfo)+'> added')

    def list_val_to_int(self, value, valuetype):

        if valuetype == HbusObjDataType.dataTypeInt:
            try:
                return int(value)
            except:
                self.logger.warning('invalid value in config file')
                return 0
        elif valuetype == HbusObjDataType.type_byte:
            value = value.split(' ')
            int_value = 0
            for i in range(0, len(value)):
                int_value = int_value + int(value[i], 16) << i

            return int_value
        elif valuetype == HbusObjDataType.dataTypeFixedPoint:
            return 0 ##@todo fixed point parsing
        elif valuetype == HbusObjDataType.dataTypeUnsignedInt:
            try:
                return int(value)
            except:
                self.logger.warning('invalid value in virtual device config')
                return 0
        else:
            return 0
