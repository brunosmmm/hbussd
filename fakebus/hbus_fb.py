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
from collections import deque

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

FakeBusMasterAddress = hbusDeviceAddress(0,0)

##Device internal status emulation for addressing simulation
class FakeBusDeviceStatus:
    deviceIdle = 0
    deviceAddressing1 = 1 #first stage, device does buslock
    deviceAddressing2 = 2 #second stage, device awaits
    deviceAddressing3 = 3 #finishes addressing
    deviceEnumerated = 4

##Device data structure
# inherits hbusSlaveInfo and adds objects to emulate addressing of devices
class FakeBusDevice(hbusSlaveInfo):
    
    ##Device internal status emulation
    deviceStatus = FakeBusDeviceStatus.deviceIdle

    def makeQueryResponse(self,objnum):
        if objnum == 0:
            #special case
            
            #OBJECT_INFO data

            objectInfo = (0,4+len(self.hbusSlaveDescription),hbusSlaveObjectPermissions.hbusSlaveObjectRead,8,0,len(self.hbusSlaveDescription),self.hbusSlaveDescription)

            return objectInfo

        elif objnum in self.hbusSlaveObjects.keys():
            objectInfo = (objnum,4+len(self.hbusSlaveObjects[objnum].objectDescription),self.hbusSlaveObjects[objnum].objectPermissions,self.hbusSlaveObjects[objnum].objectSize,self.hbusSlaveObjects[objnum].objectDataTypeInfo,len(self.hbusSlaveObjects[objnum].objectDescription),self.hbusSlaveObjects[objnum].objectDescription)
            
            return objectInfo
        else:
            #object does not exist
            return None

    def makeReadResponse(self,objnum):
        if objnum == 0:

            uid = struct.pack('i',self.hbusSlaveUniqueDeviceInfo)

            objectListInfo = (0,8,self.hbusSlaveObjectCount,self.hbusSlaveEndpointCount,self.hbusSlaveInterruptCount,self.hbusSlaveCapabilities,uid)

            return objectListInfo
        elif objnum in self.hbusSlaveObjects.keys():

            ##@todo generate proper object size!
            objectRead = (0,self.hbusSlaveObjects[objnum].objectSize,self.hbusSlaveObjects[objnum].objectLastValue)
            
            return objectRead
        else:
            return None
    

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
            self.config.read('fakebus/fakebus.config')
            self.buildBus()
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

        pSource = hbusDeviceAddress(ord(packet[0]),ord(packet[1]))
        pDest = hbusDeviceAddress(ord(packet[2]),ord(packet[3]))
        
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
                    #self.sendPacket()
                    params = self.deviceList[self.addressingDevice].makeReadResponse(0)

                    self.sendPacket(HBUSCOMMAND_RESPONSE,FakeBusMasterAddress,hbusDeviceAddress(0,255),params)
                    self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceAddressing3
                    return
                    
                elif ord(packet[4]) == HBUSCOMMAND_SEARCH.commandByte or ord(packet[4]) == HBUSCOMMAND_KEYSET.commandByte and self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing3:
                    #attribute new address and register
                    self.deviceList[self.addressingDevice].hbusSlaveAddress = hbusDeviceAddress(ord(packet[2]),ord(packet[3]))
                    self.busAddrToUID[pDest.getGlobalID()] = self.deviceList[self.addressingDevice].hbusSlaveUniqueDeviceInfo
                    #self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceEnumerated
                    
                    #addressing will finish when device sends a busunlock
                    self.addressNextDevice()
                    return
                else:
                    #makes no sense
                    return

        #detect buslock commands globally
        if ord(packet[4]) == HBUSCOMMAND_BUSLOCK.commandByte:
            if pDest.getGlobalID() in self.busAddrToUID.keys():
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
                #this is a SEARCH command, see if there are slaves that were not enumerated and starts addressing
                for device in self.deviceList.values():
                    if device.deviceStatus == FakeBusDeviceStatus.deviceIdle:
                        #start addressing
                        device.deviceStatus = FakeBusDeviceStatus.deviceAddressing1
                        #queue for addressing
                        self.addressingQueue.appendleft(device.hbusSlaveUniqueDeviceInfo)
                
                self.addressNextDevice()
                #done
                return
            elif ord(packet[4]) == HBUSCOMMAND_SOFTRESET.commandByte:
                #reset command
                return #ignore for now, nothing to do
            elif ord(packet[4]) == HBUSCOMMAND_SETKEY.commandByte:
                #this is quite uncharted territory yet
                return
            elif ord(packet[4]) == HBUSCOMMAND_RESETKEY.commandByte:
                return
            elif ord(packet[4]) == HBUSCOMMAND_SETCH.commandByte:
                #might be a broadcast object, this is not really implemented yet
                return
            else:
                return #other commands cannot be used on broadcast
        
        try:
            targetUID = self.busAddrToUID[pDest.getGlobalID()]
        except:
            #device is not enumerated in this bus
            return

        if ord(packet[4]) == HBUSCOMMAND_QUERY.commandByte:
            #querying some object
            params = self.deviceList[targetUID].makeQueryResponse(ord(packet[5]))
            if params == None:
                #problem retrieving object, ignore
                return
            self.sendPacket(HBUSCOMMAND_QUERY_RESP,FakeBusMasterAddress,self.deviceList[targetUID].hbusSlaveAddress,params)
            return
        elif ord(packet[4]) == HBUSCOMMAND_GETCH.commandByte:
            #reading some object
            params = self.deviceList[targetUID].makeReadResponse(ord(packet[5]))
            if params == None:
                #problem retrieving object, ignore
                return
            self.sendPacket(HBUSCOMMAND_RESPONSE,FakeBusMasterAddress,self.deviceList[targetUID].hbusSlaveAddress,params)
            return

    def sendPacket(self,command, dest, source, params=()):
        
        busOp = hbusOperation(hbusInstruction(command,len(params),params),dest,source)

        if command == HBUSCOMMAND_BUSLOCK:
            self.busState = hbusBusStatus.hbusBusLockedThis
        elif command == HBUSCOMMAND_BUSUNLOCK:
            self.busState = hbusBusStatus.hbusBusFree

        self.transport.write(busOp.getString())
        
            
    ##Process addressing of devices
    def addressNextDevice(self):
        
        if self.addressingDevice == None:
            if len(self.addressingQueue) > 0:
                self.addressingDevice = self.addressingQueue.pop()
            else:
                return
        
        #first stage
        if self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing1:
        #do a buslock
            self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceAddressing2
            self.sendPacket(HBUSCOMMAND_BUSLOCK,FakeBusMasterAddress,hbusDeviceAddress(0,255))
        
            #done for now
            return
        elif self.deviceList[self.addressingDevice].deviceStatus == FakeBusDeviceStatus.deviceAddressing3:
            #do a busunlock
            self.sendPacket(HBUSCOMMAND_BUSUNLOCK,FakeBusMasterAddress,self.deviceList[self.addressingDevice].hbusSlaveAddress)
            self.deviceList[self.addressingDevice].deviceStatus = FakeBusDeviceStatus.deviceEnumerated
            self.addressingDevice = None
            
            return

    ##Parse configuration files and builds bus structure
    def buildBus(self):
        
        self.logger.debug("start adding fake devices...")
        #get device path
        devicePath = 'fakebus/'+self.config.get('fakebus','object_dir')
        
        deviceFiles = [x for x in os.listdir(devicePath) if x.endswith('.config')]

        #read device files to build tree
        devConfig = ConfigParser.ConfigParser()
        for devFile in deviceFiles:
            device = FakeBusDevice(None)
            devConfig.read(devicePath+devFile)
            
            #start building device
            try:
                if devConfig.getboolean('device','dont_read') == True:
                    continue
            except:
                pass

            #UID
            device.hbusSlaveUniqueDeviceInfo = int(devConfig.get('device','uid'),16)
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
                canWrite = devConfig.getboolean(section, 'can_write')
                
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
                dataTypeInfo = devConfig.get(section,'data_type_info')
                level = devConfig.getint(section,'level')
                
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
            self.logger.debug('fake device "'+device.hbusSlaveDescription+'" <'+hex(device.hbusSlaveUniqueDeviceInfo)+'> added')
