#coding=utf-8

##@package hbus_fb
# fake bus for debugging without actual hardware connected
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 11/17/2014
# @todo implement fake bus device structure
# @todo load device configuration from files


from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
import struct
import logging
from hbus_base import *
from hbus_constants import *
from hbusslaves import *

import ConfigParser ##for fakebus device tree emulation
import os

##Configuration file options equivalence
configDataType = { 'I' : hbusSlaveObjectDataType.dataTypeInt,
                   'U' : hbusSlaveObjectDataType.dataTypeUnsignedInt,
                   'B' : hbusSlaveObjectDataType.dataTypeByte,
                   'F' : hbusSlaveObjectDataType.dataTypeFixedPoint
                 }

configDataTypeInfo = { 'h' : hbusSlaveObjectDataType.dataTypeByteHex,
                       'd' : hbusSlaveObjectDataType.dataTypeByteDec,
                       'o' : hbusSlaveObjectDataType.dataTypeByteOct,
                       'b' : hbusSlaveObjectDataType.dataTypeByteBin,
                       'B' : hbusSlaveObjectDataType.dataTypeByteBool,
                       'p' : hbusSlaveObjectDataType.dataTypeUintPercent,
                       'L' : hbusSlaveObjectDataType.dataTypeUintLinPercent,
                       'l' : hbusSlaveObjectDataType.dataTypeUintLogPercent,
                       't' : hbusSlaveObjectDataType.dataTypeUintTime,
                       'D' : hbusSlaveObjectDataType.dataTypeUintDate,
                       'u' : hbusSlaveObjectDataType.dataTypeUintNone
                     }

configLevel = { 0 : hbusSlaveObjectLevel.level0,
                1 : hbusSlaveObjectLevel.level1,
                2 : hbusSlaveObjectLevel.level2,
                3 : hbusSlaveObjectLevel.level3
                }

##Device internal status emulation for addressing simulation
class FakeBusDeviceStatus:
    deviceIdle = 0
    deviceAddressing = 1
    deviceEnumerated = 2

##Device data structure
# inherits hbusSlaveInfo and adds objects to emulate addressing of devices
class FakeBusDevice(hbusSlaveInfo):
    
    ##Device internal status emulation
    deviceStatus = FakeBusDeviceStatus.deviceIdle
    

##Fake bus main class
class FakeBusSerialPort(Protocol):

    ##Constructor, initializes
    def __init__(self):
        self.logger = logging.getLogger('hbussd.fakebus')
        self.logger.debug("fakebus active")
        self.dataBuffer = []
        self.rxState = hbusMasterRxState.hbusRXSBID
        self.config = ConfigParser.ConfigParser()
        self.deviceList = {}
        try:
            self.config.read('fakebus.config')
            self.buildBus()
        except:
            self.logger.debug("no configuration file found")

    ##Master connected to fakebus
    def connectionMade(self):
        self.logger.debug("hbus master connected to fakebus")

    ##Data reception state machine, similar to master's
    # @param data data chunk received
    def dataReceived(self,data):
        
        #make state machine work byte by byte
        for d in data:
            
            if self.rxState == hbusMasterRxState.hbusRXSBID:
                self.dataBuffer.append(d)
                self.rxState = hbusMasterRxState.hbusRXSDID
            elif self.rxState == hbusMasterRxState.hbusRXSDID:
                self.dataBuffer.append(d)
                self.rxState = hbusMasterRxState.hbusRXTBID
            elif self.rxState == hbusMasterRxState.hbusRXTBID:
                self.dataBuffer.append(d)
                self.rxState = hbusMasterRxState.hbusRXTDID
            elif self.rxState == hbusMasterRxState.hbusRXTDID:
                self.dataBuffer.append(d)
                self.rxState = hbusMasterRxState.hbusRXCMD
            elif self.rxState == hbusMasterRxState.hbusRXCMD:
                self.dataBuffer.append(d)
                if ord(d) in HBUS_SCMDBYTELIST:
                    self.rxState = hbusMasterRxState.hbusRXSTP
                elif ord(d) == HBUSCOMMAND_SOFTRESET.commandByte: #softreset is different, doesnt specify addr field
                    self.rxState = hbusMasterRxState.hbusRXPSZ
                else:
                    self.rxState = hbusMasterRxState.hbusRXADDR
            elif self.rxState == hbusMasterRxState.hbusRXADDR:
                self.dataBuffer.append(d)
                if ord(self.dataBuffer[4]) in HBUS_SACMDBYTELIST:
                    self.rxState = hbusMasterRxState.hbusRXSTP
                else:
                    self.rxState = hbusMasterRxState.hbusRXPSZ
            elif self.rxState == hbusMasterRxState.hbusRXPSZ:
                self.lastParamSize = ord(d)
                self.dataBuffer.append(d)
                if ord(self.dataBuffer[4]) == HBUSCOMMAND_STREAMW.commandByte or ord(self.dataBuffer[4]) == HBUSCOMMAND_STREAMR.commandByte:
                    self.rxState = hbusMasterRxState.hbusRXSTP
                else:
                    if ord(d) > 0:
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
                    self.dataBuffer.append(d)
                else:
                    if ord(d) == 0xFF:
                        self.dataBuffer.append(d)
                        #finished Packet

                        self.rxState = hbusMasterRxState.hbusRXSBID
                        self.parsePacket(self.dataBuffer)
                        self.dataBuffer = []
                        return
                    else:
                        #malformed packet, ignore
                        self.rxState = hbusMasterRxState.hbusRXSBID
                        self.logger.debug("ignored malformed packet from master")
                        self.logger.debug("packet size %d, dump: %s",len(self.dataBuffer),[hex(ord(x)) for x in self.dataBuffer])
                        self.dataBuffer = []
                        return
            elif self.rxState == hbusMasterRxState.hbusRXSTP:
                self.dataBuffer.append(d)
                if ord(d) == 0xFF:
                    #finished
                    self.rxState = hbusMasterRxState.hbusRXSBID
                    self.parsePacket(self.dataBuffer)
                    self.dataBuffer = []
                    return
                else:
                    #malformed packet, ignore
                    self.rxState = hbusMasterRxState.hbusRXSBID
                    self.logger.debug("ignored malformed packet from master")
                    self.logger.debug("packet size %d dump: %s",len(self.dataBuffer),[hex(ord(x)) for x in self.dataBuffer])
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
    def parsePacket(self,packet):
        self.logger.debug("I got a packet!")
        pass

    ##Parse configuration files and builds bus structure
    def buildBus(self):
        
        #get device path
        devicePath = self.config.get('fakebus','object_dir')
        
        deviceFiles = [x for x in os.listdir(devicePath) if x.endswith('.config')]

        #read device files to build tree
        devConfig = ConfigParser.ConfigParser()
        for device in deviceFiles:
            device = FakeBusDevice(None)
            devConfig.read(devicePath+device)
            
            #start building device
            try:
                if devConfig.getboolean('device','dont_read') == True:
                    continue
            except:
                pass

            #UID
            device.hbusSlaveUniqueDeviceInfo = devConfig.getint('device','uid')
            device.hbusSlaveDescription = devConfig.get('device','descr')
            device.hbusSlaveObjectCount = devConfig.getint('device','object_count')
            device.hbusSlaveEndpointCount = devConfig.getint('device','endpoint_count')
            device.hbusSlaveInterruptCount = devConfig.getint('device','int_count')
            
            #capabilities, must generate flags
            ##@todo generate flags for capabilities from configuration file

            for section in devConfig.sections():
                m = re.match(r"object([0-9+])",section)
                if m == None:
                    continue
                

                obj = hbusSlaveObjectInfo()
                
                #generate flags for permissions
                canRead = devConfig.getboolean(section,'can_read')
                canWrite = devconfig.getboolean(section, 'can_write')
                
                if canRead == True:
                    if canWrite == True:
                        obj.objectPermissions = hbusSlaveObjectPermissions.hbusSlaveObjectReadWrite
                    else:
                        obj.objectPermissions = hbusSlaveObjectPermissions.hbusSlaveObjectRead
                elif canWrite == True:
                    obj.objectPermissions = hbusSlaveObjectPermissions.hbusSlaveObjectWrite
                else:
                    #error!
                    pass #for now
                
                obj.objectCrypto = devConfig.getboolean(section,'is_crypto')
                obj.objectHidden = devConfig.getboolean(section,'hidden')
                obj.objectDescription = devConfig.get(section,'descr')
                obj.objectSize = devConfig.getint(section,'size')
                
                #must generate value from configfile
                dataType = devConfig.get(section,'data_type')
                dataTypeInfo = devconfig.get(section,'data_type_info')
                level = devconfig.getint(section,'level')
                
                try:
                    obj.objectDataType = configDataType[dataType]
                    obj.objectDataTypeInfo = configDataTypeInfo[dataTypeInfo]
                    obj.objectLevel = configLevel[level]
                except:
                    #invalid data type
                    pass #for now

                obj.objectLevel = devConfig.getint(section,'level')

                #must interpret dummy return value in file
                rawValue = devConfig.get(section,'value')

                #when finished
                ##add to obj list
                device.hbusSlaveObjects[int(m.group(1))] = obj
                
            #when finished
            ##add to device list
            self.deviceList[device.hbusSlaveUniqueDeviceInfo] = device
