#coding=utf-8

##@package hbustcpserver
# Communication and control through a TCP server
# @author Bruno Morais <brunosmmm@gmail.com>
# @date 2013-2014
# @todo better documentation of some functions

import logging
from hbusmaster import *
import re
import string

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

##TCP command specification class
class HBUSTCPCommand:
    
    ##Constructor
    #@param CMDSTR Command string
    #@param NPARAM Command parameter count
    def __init__(self, CMDSTR, NPARAM):
        
        ##string
        self.cmdstr = CMDSTR
        ##parameter count
        self.numParam = NPARAM
    
    ##Match using regular expressions
    #@return compiled regex 
    def compile(self):
        
        if (self.numParam > 0):
            
            compileString = r"^"+self.cmdstr
            
            for i in range(self.numParam+1):
                
                compileString.join((r'\s*([a-z0-9:]+)'))
                
            return re.compile(compileString, re.IGNORECASE)
            
            
        else:
            return re.compile(r"^"+self.cmdstr, re.IGNORECASE)
    
##@defgroup hbusTCPCommands TCP commands
#@{
#Commands recognized by TCP server specification

##SEARCH - Bus search operation
HBUSTCPCMD_SEARCH = HBUSTCPCommand("SEARCH",0)
##SCOUNT - Gets the number of currently active devices
HBUSTCPCMD_SCOUNT = HBUSTCPCommand("SCOUNT",0)
##NAME - Gets the name of a device
HBUSTCPCMD_NAME = HBUSTCPCommand("NAME",1)
##OCOUNT - Gets a device's object count
HBUSTCPCMD_OCOUNT = HBUSTCPCommand("OCOUNT",1)
##READ - Reads a device object and returns its value
HBUSTCPCMD_READ = HBUSTCPCommand("READ",1)
##WRITE - Writes a device object
HBUSTCPCMD_WRITE = HBUSTCPCommand("WRITE",2)
##QUERY - Gets information on a device object
HBUSTCPCMD_QUERY = HBUSTCPCommand("QUERY",1)
##FIND - ?
HBUSTCPCMD_FIND = HBUSTCPCommand("FIND",1)
##INCR - Increments value of a device object
HBUSTCPCMD_INCR = HBUSTCPCommand("INCR",1)
##DECR - Decrements value of a device object
HBUSTCPCMD_DECR = HBUSTCPCommand("DECR",1)
##ACTIVE - Gets a list of all currently active devices
HBUSTCPCMD_ACTIVE = HBUSTCPCommand("ACTIVE",0)
##RAW - Sends raw data to the bus
HBUSTCPCMD_RAW = HBUSTCPCommand("RAW",1)

##Command list
HBUSTCPCMDLIST = (HBUSTCPCMD_SEARCH,HBUSTCPCMD_SCOUNT,HBUSTCPCMD_NAME,HBUSTCPCMD_OCOUNT,HBUSTCPCMD_READ,HBUSTCPCMD_WRITE,HBUSTCPCMD_QUERY,HBUSTCPCMD_FIND,HBUSTCPCMD_INCR,HBUSTCPCMD_DECR,HBUSTCPCMD_ACTIVE,HBUSTCPCMD_RAW)
##@}

def incrementByteList(byteList):
    
    byteList.reverse()
    
    for b in byteList:
        
        if b < 255:
            b = b + 1
            break
        
    byteList.reverse()
        
    return byteList
    

##Twisted TCP server
class HBUSTCP(LineReceiver):
    
    def __init__(self, hbusMaster, tcpLogger):
        self.hbusMaster = hbusMaster
        self.logger = tcpLogger
        
        ##Commands and functions
        self.commandDict = {HBUSTCPCMD_SEARCH : self.executeSearchCommand, HBUSTCPCMD_SCOUNT : self.executeScountCommand, 
                            HBUSTCPCMD_NAME : self.executeNameCommand, HBUSTCPCMD_OCOUNT : self.executeOCOUNTCommand, 
                            HBUSTCPCMD_QUERY : self.executeQUERYCommand, HBUSTCPCMD_READ : self.executeREADCommand,
                            HBUSTCPCMD_FIND : self.executeFINDCommand, HBUSTCPCMD_WRITE : self.executeWRITECommand,
                            HBUSTCPCMD_INCR :self.executeINCRCommand,
                            HBUSTCPCMD_ACTIVE : self.executeACTIVECommand,
                            HBUSTCPCMD_RAW    : self.executeRAWCommand}
    
    ##New line event
    #@param line received string
    def lineReceived(self, line):
        
        self.parseCommand(line)
    
    ##Connection made event
    def connectionMade(self):
        
        self.logger.info("New connection made")
        
        self.sendLine("HBUS SERVER @ "+str(self.hbusMaster.hbusMasterAddr.hbusAddressBusNumber)+":0")
    
    ##Disconnect event
    #@param reason disconnection reason
    def connectionLost(self, reason):
        self.logger.debug("Connection closed")
    
    ##Parses received command
    #@param command received string
    def parseCommand(self, command):
        
        command = command.strip()
        
        for cmd in self.commandDict.keys():
            
            if cmd.compile().match(command):
                
                paramList = string.split(command,' ')[1::]
                
                if len(paramList) > cmd.numParam:
                    #error
                    self.logger.warning("Malformed command, removing extra parameters")
                    paramList = paramList[0:cmd.numParam]
                    
                elif len(paramList) < cmd.numParam:
                    #error
                    self.logger.warning("Malformed command, missing parameters")
                    break
                
                self.commandDict[cmd](paramList)
                break
            
    ##Executes search command
    #@param param dummy parameter
    def executeSearchCommand(self, param):
        
        self.hbusMaster.detectSlaves(callBack=self.searchCommandEnded)
    
    ##Executes ACTIVE command
    #@param param dummy parameter
    def executeACTIVECommand(self, param):
        
        for s in self.hbusMaster.detectedSlaveList.values():
            
            self.sendLine(str(s.hbusSlaveAddress.hbusAddressBusNumber)+":"+str(s.hbusSlaveAddress.hbusAddressDevNumber)+", "+s.hbusSlaveDescription+", "+hex(s.hbusSlaveUniqueDeviceInfo))
    
    ##SEARCH end callback
    def searchCommandEnded(self):
        
        self.sendLine("OK")
    
    ##Executes SCOUNT command
    #@param param dummy parameter
    def executeScountCommand(self, param):
        
        self.sendLine(str(len(self.hbusMaster.detectedSlaveList)))
    
    ##Executes RAW command
    #@param data raw data to be sent
    def executeRAWCommand(self,data):
        
        byteList = []

        hexStr = ''.join( data[0].split(",") )

        for i in range(0, len(hexStr), 2):
            byteList.append(int (hexStr[i:i+2], 16 ) )
            
        byteList = ''.join([chr(x) for x in byteList])
        
        self.hbusMaster.serialWrite(byteList)
    
    ##Executes NAME command
    #@param param device address
    def executeNameCommand(self, param):
        
        try:
            
            devAddr = string.split(param[0],':')
            
            self.sendLine(self.hbusMaster.detectedSlaveList[int(HbusDeviceAddress(int(devAddr[0]),int(devAddr[1])).getGlobalID())].hbusSlaveDescription)
            
        except:
            
            self.logger.warning("Malformed or non-existent device address")
            self.sendLine("ERROR")
    
    ##Executes OCOUNT command
    #@param param device address
    def executeOCOUNTCommand(self,param):
        
        try:
            
            devAddr = string.split(param[0],':')
            
            self.sendLine(str(self.hbusMaster.detectedSlaveList[int(HbusDeviceAddress(int(devAddr[0]),int(devAddr[1])).getGlobalID())].hbusSlaveObjectCount))
            
        except:
            
            self.logger.warning("Malformed or non-existent device address")
            self.sendLine("ERROR")
    
    ##Executes QUERY command
    #@param param device address
    def executeQUERYCommand(self,param):
        
        try:
            devAddr = string.split(param[0],":")
            
            if len(devAddr) < 2:
            
                if len(devAddr) < 1:
            
                    self.logger.warning("malformed device address")
                    self.sendLine("ADDRESS ERROR")
                    return None
                
                else:
                    
                    devUID = string.split(devAddr[0],"0x")
                    
                    if len(devUID) < 2:
                        
                        self.logger.warning("malformed device address")
                        self.sendLine("ADDRESS ERROR")
                        return None
                    
                    else:
                        
                        device = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
                        
                        if device == None:
                            
                            self.logger.warning("the specified device does not exist")
                            self.sendLine("UNKNOWN SLAVE")
                            return None
                        
            else:
                
                device = HbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
            
            i = 1
            for slaveObject in self.hbusMaster.detectedSlaveList[device.getGlobalID()].hbusSlaveObjects.values():
                
                if slaveObject.objectHidden:
                    continue
            
                self.sendLine(param[0]+":"+str(i)+", "+str(slaveObject.objectDescription)+", "+str(slaveObject.objectSize)+", "+
                                        ("R" if slaveObject.permissions == 1 else ("W" if slaveObject.permissions == 2 else "RW")))
                
                i = i + 1
            
        except:
            self.logger.warning("malformed or non-existant object and/or device address")
            self.sendLine("ERROR")
    
    ##Executes READ command
    # @param param device address
    def executeREADCommand(self,param):
        
        try:
            devAddr = string.split(param[0],':')
            
            if len(devAddr) < 3:
                
                self.logger.warning("malformed device address")
                self.sendLine("ADDRESS ERROR")
                return None
            
            self.hbusMaster.readSlaveObject(HbusDeviceAddress(int(devAddr[0]),int(devAddr[1])), int(devAddr[2]),callBack=self.readCommandEnded)
            
        except:
            self.logger.warning("endereço de objeto e/ou dispositivo mal-formado ou inexistente")
            self.sendLine("ERROR")
            
    ##READ command end callback
    # @param slaveObjectData data read from device object
    def readCommandEnded(self, slaveObjectData):

        if slaveObjectData != None:
            
            self.sendLine(''.join( [ "%02X " % ord( x ) for x in slaveObjectData ] ).strip())
        else:
            self.sendLine("ERROR")

    ##Executes WRITE command
    # @param param value to be written
    def executeWRITECommand(self,param):
        
        devAddr = string.split(param[0],":")
        
        if len(devAddr) < 3:
        
            if len(devAddr) < 2:
        
                self.logger.warning("malformed device address")
                self.sendLine("ADDRESS ERROR")
                return None
            
            else:
                
                devUID = string.split(devAddr[0],"0x")
                
                if len(devUID) < 2:
                    
                    self.logger.warning("malformed device address")
                    self.sendLine("ADDRESS ERROR")
                    return None
                
                else:
                    
                    device = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
                    
                    if device == None:
                        
                        self.logger.warning("specified device does not exist")
                        self.sendLine("UNKNOWN SLAVE")
                        return None
                    
                    objNumber = devAddr[1]
                    
        else:
            
            objNumber = devAddr[2]
            device = HbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
        
        byteList = []

        hexStr = ''.join( param[1].split(",") )

        for i in range(0, len(hexStr), 2):
            byteList.append(int (hexStr[i:i+2], 16 ) )
            
        
        if self.hbusMaster.detectedSlaveList[device.getGlobalID()].hbusSlaveObjectCount < int(objNumber):
            
            self.logger.warning("specified object does not exist")
            self.sendLine("UNKNOWN OBJECT")
            return None
        
        self.hbusMaster.writeSlaveObject(device, int(objNumber), byteList)
        
    
    ##Executes FIND command
    # @param param dummy parameter
    def executeFINDCommand(self,param):
        
        address = self.hbusMaster.findDeviceByUID(int(param[0]))
        
        if address != None:
        
            self.sendLine(str(address.hbusAddressBusNumber)+":"+str(address.hbusAddressDevNumber))
        else:
            self.sendLine("ERROR")
            
    ##Executes INCR command
    # @param param device/object address
    def executeINCRCommand(self,param):
        
        devAddr = string.split(param[0],":")
        
        if len(devAddr) < 3:
        
            self.logger.warning("malformed device address")
            return None
        
        slaveObjectValue = self.hbusMaster.detectedSlaveList[HbusDeviceAddress(int(devAddr[0]),int(devAddr[1])).getGlobalID()].hbusSlaveObjects[int(devAddr[2])].objectLastValue
        
        self.hbusMaster.writeSlaveObject(HbusDeviceAddress(int(devAddr[0]),int(devAddr[1])), int(devAddr[2]), incrementByteList(slaveObjectValue))

##TCP server instance
class HBUSTCPFactory(Factory):
    def __init__(self,hbusMaster):
        self.hbusMaster = hbusMaster
        
        self.logger = logging.getLogger('hbussd.hbustcpserver')
    
    def buildProtocol(self,addr):
        
        return HBUSTCP(self.hbusMaster,self.logger)
    
