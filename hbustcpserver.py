#coding=utf-8
import logging
from hbusmaster import *
import re
import string

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

class HBUSTCPCommand:
    
    def __init__(self, CMDSTR, NPARAM):
        
        self.cmdstr = CMDSTR
        self.numParam = NPARAM
    
    def compile(self):
        
        if (self.numParam > 0):
            
            compileString = r"^"+self.cmdstr
            
            for i in range(self.numParam+1):
                
                compileString.join((r'\s*([a-z0-9:]+)'))
                
            return re.compile(compileString, re.IGNORECASE)
            
            
        else:
            return re.compile(r"^"+self.cmdstr, re.IGNORECASE)
    

HBUSTCPCMD_SEARCH = HBUSTCPCommand("SEARCH",0)
HBUSTCPCMD_SCOUNT = HBUSTCPCommand("SCOUNT",0)
HBUSTCPCMD_NAME = HBUSTCPCommand("NAME",1)
HBUSTCPCMD_OCOUNT = HBUSTCPCommand("OCOUNT",1)
HBUSTCPCMD_READ = HBUSTCPCommand("READ",1)
HBUSTCPCMD_WRITE = HBUSTCPCommand("WRITE",2)
HBUSTCPCMD_QUERY = HBUSTCPCommand("QUERY",1)
HBUSTCPCMD_FIND = HBUSTCPCommand("FIND",1)
HBUSTCPCMD_INCR = HBUSTCPCommand("INCR",1)
HBUSTCPCMD_DECR = HBUSTCPCommand("DECR",1)
HBUSTCPCMD_ACTIVE = HBUSTCPCommand("ACTIVE",0)
HBUSTCPCMD_RAW = HBUSTCPCommand("RAW",1)

HBUSTCPCMDLIST = (HBUSTCPCMD_SEARCH,HBUSTCPCMD_SCOUNT)

def incrementByteList(byteList):
    
    byteList.reverse()
    
    for b in byteList:
        
        if b < 255:
            b = b + 1
            break
        
    byteList.reverse()
        
    return byteList
    

class HBUSTCP(LineReceiver):
    
    def __init__(self, hbusMaster, tcpLogger):
        self.hbusMaster = hbusMaster
        self.logger = tcpLogger
    
        self.commandDict = {HBUSTCPCMD_SEARCH : self.executeSearchCommand, HBUSTCPCMD_SCOUNT : self.executeScountCommand, 
                            HBUSTCPCMD_NAME : self.executeNameCommand, HBUSTCPCMD_OCOUNT : self.executeOCOUNTCommand, 
                            HBUSTCPCMD_QUERY : self.executeQUERYCommand, HBUSTCPCMD_READ : self.executeREADCommand,
                            HBUSTCPCMD_FIND : self.executeFINDCommand, HBUSTCPCMD_WRITE : self.executeWRITECommand,
                            HBUSTCPCMD_INCR :self.executeINCRCommand,
                            HBUSTCPCMD_ACTIVE : self.executeACTIVECommand,
                            HBUSTCPCMD_RAW    : self.executeRAWCommand}
    
    def lineReceived(self, line):
        
        self.parseCommand(line)
    
    def connectionMade(self):
        
        self.logger.info("Nova conexão realizada")
        
        self.sendLine("HBUS SERVER @ "+str(self.hbusMaster.hbusMasterAddr.hbusAddressBusNumber)+":0")
        
    def connectionLost(self, reason):
        self.logger.debug("Conexão fechada")
        
    def parseCommand(self, command):
        
        command = command.strip()
        
        for cmd in self.commandDict.keys():
            
            if cmd.compile().match(command):
                
                paramList = string.split(command,' ')[1::]
                
                if len(paramList) > cmd.numParam:
                    #erro
                    self.logger.warning("Comando mal-formado, removendo parâmetros em excesso")
                    paramList = paramList[0:cmd.numParam]
                    
                elif len(paramList) < cmd.numParam:
                    #erro
                    self.logger.warning("Comando mal-formado, faltando parâmetros")
                    break
                
                self.commandDict[cmd](paramList)
                break
            
            
    def executeSearchCommand(self, param):
        
        self.hbusMaster.detectSlaves(callBack=self.searchCommandEnded)
        
    def executeACTIVECommand(self, param):
        
        for s in self.hbusMaster.detectedSlaveList.values():
            
            self.sendLine(str(s.hbusSlaveAddress.hbusAddressBusNumber)+":"+str(s.hbusSlaveAddress.hbusAddressDevNumber)+", "+s.hbusSlaveDescription+", "+hex(s.hbusSlaveUniqueDeviceInfo))
        
    def searchCommandEnded(self):
        
        self.sendLine("OK")
        
    def executeScountCommand(self, param):
        
        self.sendLine(str(len(self.hbusMaster.detectedSlaveList)))
        
    def executeRAWCommand(self,data):
        
        byteList = []

        hexStr = ''.join( data[0].split(",") )

        for i in range(0, len(hexStr), 2):
            byteList.append(int (hexStr[i:i+2], 16 ) )
            
        byteList = ''.join([chr(x) for x in byteList])
        
        self.hbusMaster.serialWrite(byteList)
        
    def executeNameCommand(self, param):
        
        try:
            
            devAddr = string.split(param[0],':')
            
            self.sendLine(self.hbusMaster.detectedSlaveList[int(hbusDeviceAddress(int(devAddr[0]),int(devAddr[1])).getGlobalID())].hbusSlaveDescription)
            
        except:
            
            self.logger.warning("endereço de dispositivo mal-formado ou inexistente")
            self.sendLine("ERROR")
            
    def executeOCOUNTCommand(self,param):
        
        try:
            
            devAddr = string.split(param[0],':')
            
            self.sendLine(str(self.hbusMaster.detectedSlaveList[int(hbusDeviceAddress(int(devAddr[0]),int(devAddr[1])).getGlobalID())].hbusSlaveObjectCount))
            
        except:
            
            self.logger.warning("endereço de dispositivo mal-formado ou inexistente")
            self.sendLine("ERROR")
            
    def executeQUERYCommand(self,param):
        
        try:
            devAddr = string.split(param[0],":")
            
            if len(devAddr) < 2:
            
                if len(devAddr) < 1:
            
                    self.logger.warning("endereço de dispositivo mal-formado")
                    self.sendLine("ADDRESS ERROR")
                    return None
                
                else:
                    
                    devUID = string.split(devAddr[0],"0x")
                    
                    if len(devUID) < 2:
                        
                        self.logger.warning("endereço de dispositivo mal-formado")
                        self.sendLine("ADDRESS ERROR")
                        return None
                    
                    else:
                        
                        device = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
                        
                        if device == None:
                            
                            self.logger.warning("dispositivo requisitado não existe")
                            self.sendLine("UNKNOWN SLAVE")
                            return None
                        
            else:
                
                device = hbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
            
            i = 1
            for slaveObject in self.hbusMaster.detectedSlaveList[device.getGlobalID()].hbusSlaveObjects.values():
            
                self.sendLine(param[0]+":"+str(i)+", "+str(slaveObject.objectDescription)+", "+str(slaveObject.objectSize)+", "+
                                        ("R" if slaveObject.objectPermissions == 1 else ("W" if slaveObject.objectPermissions == 2 else "RW")))
                
                i = i + 1
            
        except:
            self.logger.warning("endereço de objeto e/ou dispositivo mal-formado ou inexistente")
            self.sendLine("ERROR")
    
    def executeREADCommand(self,param):
        
        try:
            devAddr = string.split(param[0],':')
            
            if len(devAddr) < 3:
                
                self.logger.warning("endereço de dispositivo mal-formado")
                self.sendLine("ADDRESS ERROR")
                return None
            
            self.hbusMaster.readSlaveObject(hbusDeviceAddress(int(devAddr[0]),int(devAddr[1])), int(devAddr[2]),callBack=self.readCommandEnded)
            
        except:
            self.logger.warning("endereço de objeto e/ou dispositivo mal-formado ou inexistente")
            self.sendLine("ERROR")
            
    def readCommandEnded(self, slaveObjectData):

        if slaveObjectData != None:
            
            self.sendLine(''.join( [ "%02X " % ord( x ) for x in slaveObjectData ] ).strip())
        else:
            self.sendLine("ERROR")

    def executeWRITECommand(self,param):
        
        devAddr = string.split(param[0],":")
        
        if len(devAddr) < 3:
        
            if len(devAddr) < 2:
        
                self.logger.warning("endereço de dispositivo mal-formado")
                self.sendLine("ADDRESS ERROR")
                return None
            
            else:
                
                devUID = string.split(devAddr[0],"0x")
                
                if len(devUID) < 2:
                    
                    self.logger.warning("endereço de dispositivo mal-formado")
                    self.sendLine("ADDRESS ERROR")
                    return None
                
                else:
                    
                    device = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
                    
                    if device == None:
                        
                        self.logger.warning("dispositivo requisitado não existe")
                        self.sendLine("UNKNOWN SLAVE")
                        return None
                    
                    objNumber = devAddr[1]
                    
        else:
            
            objNumber = devAddr[2]
            device = hbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
        
        byteList = []

        hexStr = ''.join( param[1].split(",") )

        for i in range(0, len(hexStr), 2):
            byteList.append(int (hexStr[i:i+2], 16 ) )
            
        
        if self.hbusMaster.detectedSlaveList[device.getGlobalID()].hbusSlaveObjectCount < int(objNumber):
            
            self.logger.warning("objeto requisitado não existe")
            self.sendLine("UNKNOWN OBJECT")
            return None
        
        self.hbusMaster.writeSlaveObject(device, int(objNumber), byteList)
        
    
    def executeFINDCommand(self,param):
        
        address = self.hbusMaster.findDeviceByUID(int(param[0]))
        
        if address != None:
        
            self.sendLine(str(address.hbusAddressBusNumber)+":"+str(address.hbusAddressDevNumber))
        else:
            self.sendLine("ERROR")
            
    def executeINCRCommand(self,param):
        
        devAddr = string.split(param[0],":")
        
        if len(devAddr) < 3:
        
            self.logger.warning("endereço de dispositivo mal-formado")
            return None
        
        slaveObjectValue = self.hbusMaster.detectedSlaveList[hbusDeviceAddress(int(devAddr[0]),int(devAddr[1])).getGlobalID()].hbusSlaveObjects[int(devAddr[2])].objectLastValue
        
        #print slaveObjectValue
        
        self.hbusMaster.writeSlaveObject(hbusDeviceAddress(int(devAddr[0]),int(devAddr[1])), int(devAddr[2]), incrementByteList(slaveObjectValue))

class HBUSTCPFactory(Factory):
    def __init__(self,hbusMaster):
        self.hbusMaster = hbusMaster
        
        self.logger = logging.getLogger('hbus_skeleton.hbustcpserver')
    
    def buildProtocol(self,addr):
        
        return HBUSTCP(self.hbusMaster,self.logger)
    