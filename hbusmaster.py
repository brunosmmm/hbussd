# coding=utf-8

##@package hbusmaster
# main HBUS master module
# @author Bruno Morais <brunosmmm@gmail.com>
# @date 2012-2014
# @todo decouple and sanitize device scanning logic
# @todo translate documentation and comment strings

import struct
from datetime import datetime
import logging
from collections import deque
import hbus_crypto

from twisted.internet import reactor, defer
from twisted.internet.protocol import Factory

from hbus_constants import * 
from hbus_base import *
from hbus_except import *
from hbusslaves import *
from hbus_datahandlers import *
from hbusmasterobjects import *
from fakebus import hbus_fb
from hbussd_plugin import hbusPluginManager
from hbussd_evt import hbusMasterEvent, hbusMasterEventType

import re

BROADCAST_BUS = 255
VIRTUAL_BUS = 254

##Gets actual time in milliseconds
# @param td actual time
# @return actual time in milliseconds
def getMillis(td):
    
    return (td.days * 24 * 60 * 60 + td.seconds) * 1000 + td.microseconds / 1000.0

def nonBlockingDelay(td):
    
    now = datetime.now()
    
    while getMillis(datetime.now() - now) < td:
        pass
    
##Conjunto de chaves de segurança HBUS
#
#A chave é um par de números (p,q)
class hbusKeySet:
    
    ##Número p da chave
    privateq = None
    ##Número q da chave
    privatep = None
    
    ##Construtor
    #@param p número p
    #@param q número q
    def __init__(self,p,q):
        
        self.privatep = p
        self.privateq = q
    
    ##Gera chave pública
    #
    #A chave pública é obtida multiplicando-se p e q
    #@return chave pública
    def pubKeyInt(self):
        
        return self.privatep*self.privateq
    
    ##Gera string de chave pública
    #@return chave pública em string
    def pubKeyStr(self):
        
        h = hex(self.privatep*self.privateq)[2:].rstrip('L')
        
        if (len(h) % 2):
            h = '0%s' % h
            
        while (len(h) < HBUS_PUBKEY_SIZE*2):
            h = '00%s' % h
            
        h = h.decode('hex')
            
        #packStr = str(192)+'s'
        
        return list(h)#struct.pack(packStr,h)
    
p = 342604160482313166816112334007089110910258720251016392985178072980194817098198724574409056226636958394678465934459619696622719424740669649868502396485869067283396294556282972464396510025180816154985285048268006216979372669280971
q = 609828164381195487560324418811535461583859042182887774624946398207269636262857827797730598026846661116173290667288561275278714668006770186716586859843775717295061922379022086436506552898287802124771661400922779346993469164594119
HBUS_ASYMMETRIC_KEYS = hbusKeySet(p,q);
                
##HBUS master machine state
class hbusMasterState:
    
    hbusMasterStarting = 0
    hbusMasterIdle = 1
    hbusMasterSearching = 2
    hbusMasterAddressing = 3
    hbusMasterScanning = 4
    hbusMasterOperational = 5
    hbusMasterChecking = 6
    hbusMasterInterrupted = 7
    
##Pending answer system using deferreds
class hbusPendingAnswer:
    
    def __init__(self,command,source,timeout,callBackDefer,actionParameters=None,timeoutAction=None,timeoutActionParameters=None):
        
        self.command = command
        self.source = source
        self.timeout = timeout
        self.now = datetime.now()
        
        self.dCallback = callBackDefer
        #self.dCallback = defer.Deferred()
        
        #if action != None:
        #    self.dCallback.addCallback(action)
        
        #self.action= action
        self.actionParameters = actionParameters
        self.timeoutActionParameters = timeoutActionParameters
        
        #self.tCallback = defer.Deferred()
        #if timeoutAction != None:
        #    self.tCallback.addCallback(timeoutAction)
        
        #self.timeoutAction = timeoutAction

        
    def addTimeoutHandler(self,timeoutHandler):
        
        self.timeoutHandler = timeoutHandler

class hbusMasterInformationData:
    
    def __init__(self,slaveCount,activeBusses):
        
        self.activeSlaveCount = slaveCount
        self.activeBusses = activeBusses

class hbusMaster:
    
    pluginManager = None
    
    hbusSerialRxTimeout = 100
    
    hbusBusState = hbusBusStatus.hbusBusFree
    hbusBusLockedWith = None
    hbusRxState = hbusMasterRxState.hbusRXSBID
    
    communicationBuffer = []
    SearchTimer = None
    
    receivedMessages = []
    expectedResponseQueue = deque()
    
    awaitingFreeBus = deque()
    
    outgoingCommands = deque()
    
    removeQueue = []
    
    detectedSlaveList = {}
    virtualSlaveList = {}
    
    staticSlaveList = []
    
    registeredSlaveCount = 0
    virtualSlavecount = 0
    
    masterState = hbusMasterState.hbusMasterStarting
    
    commandDelay = datetime.now()
    
    hbusDeviceSearchTimer = datetime.now()
    
    hbusDeviceSearchInterval = 60000
    
    autoSearch = True
    
    nextSlaveCapabilities = None
    nextSlaveUID = None
    
    hbusDeviceScanningTimeout = False
    
    rxBytes = 0
    txBytes = 0
    
    def __init__(self, port, baudrate=100000, busno = 0,reactor = None):
        
        self.serialPort = port
        self.serialBaud = baudrate
        self.hbusMasterAddr = hbusDeviceAddress(busno, 0)
        
        self.logger = logging.getLogger('hbussd.hbusmaster')

        self.pluginManager = hbusPluginManager('./plugins',self)
        self.searchAndLoadPlugins()
        
        if port == None:
            #create fakebus system
            f = Factory()
            f.protocol = hbus_fb.FakeBusSerialPort
            reactor.listenTCP(9090,f)
            
            self.serialCreate(fake=True)
        else:
            self.serialCreate(fake=False)
        
        #system started event
        event = hbusMasterEvent(hbusMasterEventType.eventStarted)
        self.pluginManager.masterEventBroadcast(event)

    ##Search and load plugins using plugin manager
    def searchAndLoadPlugins(self):

        self.logger.debug("scanning plugins")

        self.pluginManager.scanPlugins()
        
        for plugin in self.pluginManager.getAvailablePlugins():
            try:
                self.logger.debug('loading plugin '+plugin)
                self.pluginManager.loadPlugin(plugin)
            except:
                self.logger.debug('error loading plugin '+plugin)

    ##Master entering operational phase
    def enterOperational(self):
        
        #broadcast event to plugin system
        event = hbusMasterEvent(hbusMasterEventType.eventOperational)
        self.pluginManager.masterEventBroadcast(event)
        
        
    def getInformationData(self):
        
        busses = list(set([slave.hbusSlaveAddress.hbusAddressBusNumber for slave in self.detectedSlaveList.values() if slave.basicInformationRetrieved == True]))
        
        return hbusMasterInformationData(len(self.detectedSlaveList),busses)
            
    
    def serialCreate(self):
        
        pass #overload!!
    
    def serialConnected(self):
        
        #reseta todos dispositivos
        self.logger.debug("Connected. Resetting all devices now")
        
        address = hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,HBUS_BROADCAST_ADDRESS)
        
        size = HBUS_SIGNATURE_SIZE+1
        
        myParamList = [chr(size)]
        
        msg = struct.pack('cccccc',chr(self.hbusMasterAddr.hbusAddressBusNumber),chr(self.hbusMasterAddr.hbusAddressDevNumber),chr(address.hbusAddressBusNumber),
                                chr(address.hbusAddressDevNumber),chr(HBUSCOMMAND_SOFTRESET.commandByte),myParamList[0])
                    
        sig = hbus_crypto.hbusCrypto_RabinWilliamsSign(msg, HBUS_ASYMMETRIC_KEYS.privatep, HBUS_ASYMMETRIC_KEYS.privateq,HBUS_SIGNATURE_SIZE)
        
        myParamList.extend(sig.getByteString())
        
        self.pushCommand(HBUSCOMMAND_SOFTRESET,address,params=myParamList)
        
        self.logger.debug("Waiting for device RESET to complete...")
        
        #signal.alarm(1)
        reactor.callLater(1,self.handleAlarm) #@UndefinedVariable
        
        #self.detectSlaves()
        self.serialRXMachineEnterIdle()
        
    def serialWrite(self, string):
        
        pass
    
    def serialRead(self,size):
        
        pass #overload
    
    def serialRXMachineTimeout(self):
        
        self.logger.warning("Packet receive timeout")
        self.logger.debug("packet dump: %s", self.communicationBuffer)
        
        self.serialRXMachineEnterIdle()
        
    def serialRXMachineEnterIdle(self):
        
        self.communicationBuffer = []
        
        self.hbusRxState = hbusMasterRxState.hbusRXSBID
        
        if len(self.outgoingCommands) > 0:
            d = self.outgoingCommands.pop()
            d.callback(None)
        
    
    def serialNewData(self,data):
        
        for d in data:
            
            self.rxBytes += 1
            
            if self.hbusRxState == hbusMasterRxState.hbusRXSBID:
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXSDID
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXSDID:
                
                self.RXTimeout.cancel()
                
                #endereço inválido
                if (ord(d) > 32) and (ord(d) != 255):
                    self.serialRXMachineEnterIdle()
                    
                    self.logger.debug("Invalid address in received packet")
                    return
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXTBID
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXTBID:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXTDID
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXTDID:
                
                self.RXTimeout.cancel()
                
                #endereço inválido
                if (ord(d) > 32) and (ord(d) != 255):
                    self.serialRXMachineEnterIdle()
                    
                    self.logger.debug("Invalid address in received packet")
                    return
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXCMD
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXCMD:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
            
                if ord(d) == HBUSCOMMAND_ACK.commandByte or ord(d) == HBUSCOMMAND_SEARCH.commandByte or ord(d) == HBUSCOMMAND_BUSLOCK.commandByte or ord(d) == HBUSCOMMAND_BUSUNLOCK.commandByte or ord(d) == HBUSCOMMAND_SOFTRESET.commandByte:
                    self.hbusRxState = hbusMasterRxState.hbusRXSTP
                else:
                    self.hbusRxState = hbusMasterRxState.hbusRXADDR
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                    
            elif self.hbusRxState == hbusMasterRxState.hbusRXADDR:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
                
                if ord(self.communicationBuffer[4]) == HBUSCOMMAND_GETCH.commandByte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY.commandByte or\
                ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY_EP.commandByte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY_INT.commandByte:
                    self.hbusRxState = hbusMasterRxState.hbusRXSTP
                else:
                    self.hbusRxState = hbusMasterRxState.hbusRXPSZ
                    
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXPSZ:
                
                self.RXTimeout.cancel()
                
                if ord(self.communicationBuffer[4]) != HBUSCOMMAND_STREAMW.commandByte and ord(self.communicationBuffer[4]) != HBUSCOMMAND_STREAMR.commandByte:
                    if ord(d) > 64:
                        d = chr(64)
                
                self.communicationBuffer.append(d)
                self.lastPacketParamSize = ord(d)
                
                if ord(self.communicationBuffer[4]) == HBUSCOMMAND_STREAMW.commandByte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_STREAMR.commandByte:
                    self.hbusRxState = hbusMasterRxState.hbusRXSTP
                else:
                    if ord(d) > 0:
                        self.hbusRxState = hbusMasterRxState.hbusRXPRM
                    else:
                        self.hbusRxState = hbusMasterRxState.hbusRXSTP
                        
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXPRM:
                
                self.RXTimeout.cancel()
                
                if len(self.communicationBuffer) <= (6 + self.lastPacketParamSize):
                    self.communicationBuffer.append(d)
                else:
                    
                #self.hbusRxState = hbusMasterRxState.hbusRXSTP
                    if ord(d) == 0xFF:
                        self.communicationBuffer.append(d)
                        
                        dataToParse = self.communicationBuffer
                        
                        self.serialRXMachineEnterIdle()
                        
                        self.parseReceivedData(dataToParse)
                        
                        return
                        
                    else:
                        self.logger.debug("malformed packet, termination error")
                        self.logger.debug("packet dump: %s" % [hex(ord(x)) for x in self.communicationBuffer])
                        
                        self.serialRXMachineEnterIdle()
                        
                        return

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable
            
            elif self.hbusRxState == hbusMasterRxState.hbusRXSTP:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
                
                if ord(d) == 0xFF:
                    
                    dataToParse = self.communicationBuffer
                    
                    self.serialRXMachineEnterIdle()
                    
                    self.parseReceivedData(dataToParse)
                    
                    return
                
                else:
                    self.logger.debug("malformed packet, termination error")
                    self.logger.debug("packet dump: %s" % [hex(ord(x)) for x in self.communicationBuffer])
                                        
                    self.serialRXMachineEnterIdle()
                    return
                
            else:
                self.logger.error("Fatal error receiving HBUSOP")
                raise IOError("Fatal error receiving")
            
                self.serialRXMachineEnterIdle()
                
                return
    
    def getCommand(self,cmdbyte):
        
        for c in HBUS_COMMANDLIST:
            
            if c.commandByte == cmdbyte:
                return c
            
        return None

    def getNewAddress(self, uid):
        """Get address for new slave
        @param uid slave's UID
        """
        UIDList = [x.hbusSlaveUniqueDeviceInfo for x in self.detectedSlaveList.values()]
        addressList = [x.hbusSlaveAddress for x in self.detectedSlaveList.values()]
        
        AddressByUID = dict(zip(UIDList, addressList))
        
        #see if already registered at some point
        if uid in AddressByUID.keys():
            return AddressByUID[uid].hbusAddressDevNumber
            self.logger.debug("Re-integrating device with UID %s", hex(uid))
        else:
            return self.registeredSlaveCount+1

    def getnewvirtualaddress(self, uid):
        uidList = [x.hbusSlaveUniqueDeviceInfo for x in self.virtualSlaveList.values()]
        addressList = [x.hbusSlaveAddress for x in self.virtualSlaveList.values()]
        addressByUid = dict(zip(uidList,addressList))
        
        if uid in addressByUid.keys():
            return addressByUid[uid].hbusAddressDevNumber
        else:
            return self.virtualSlaveCount+1
        

    def setNextSlaveCapabilities(self,params):
        
        self.nextSlaveCapabilities = ord(params[3])
        self.nextSlaveUID, = struct.unpack('I',''.join(params[4:8]))

        #get new address
        nextAddress = self.getNewAddress(self.nextSlaveUID)
        
        if (self.nextSlaveCapabilities & hbusSlaveCapabilities.hbusSlaveAuthSupport):
            self.logger.debug("New device has AUTH support")

        
        myParamList = [chr(HBUS_PUBKEY_SIZE)]
        myParamList.extend(HBUS_ASYMMETRIC_KEYS.pubKeyStr())
        
        #registra escravo no proximo endereço disponível
        if (self.nextSlaveCapabilities & hbusSlaveCapabilities.hbusSlaveAuthSupport):
            self.pushCommand(HBUSCOMMAND_KEYSET, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, nextAddress),myParamList)
        else:
            self.pushCommand(HBUSCOMMAND_SEARCH, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, nextAddress))
            
        #modifica estado interno do BUSLOCK
        self.hbusBusLockedWith = hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, nextAddress)
        
        #envia BUSUNLOCK imediatamente
        self.pushCommand(HBUSCOMMAND_BUSUNLOCK, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,nextAddress))
        
        self.registerNewSlave(hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,nextAddress))
        
        if nextAddress == (self.registeredSlaveCount+1):
            self.registeredSlaveCount = self.registeredSlaveCount + 1
        
        self.masterState = hbusMasterState.hbusMasterSearching
        
    def parseReceivedData(self,data):
        
        selectedR = None
        
        if len(data) < 7:
            pSize = 0
            params = ()
        else:
            pSize = ord(data[6])
            params = data[7:7+ord(data[6])]
            
        try:
            busOp = hbusOperation(hbusInstruction(self.getCommand(ord(data[4])), pSize, params), hbusDeviceAddress(ord(data[2]), ord(data[3])), hbusDeviceAddress(ord(data[0]),ord(data[1])))
        except:
            
            self.logger.warning("Invalid packet was received")
            return
        
        if busOp.hbusOperationSource.hbusAddressDevNumber == 0:
            self.logger.debug("Illegal packet ignored: reserved addres")
            return
            
        self.logger.debug(busOp)
        #print busOp
        
        if busOp.hbusOperationDestination == self.hbusMasterAddr:
            
            self.receivedMessages.append(busOp)
            
            if busOp.instruction.command == HBUSCOMMAND_BUSLOCK:
                self.hbusBusState = hbusBusStatus.hbusBusLockedThis
                self.hbusBusLockedWith = busOp.hbusOperationSource
                self.nextSlaveCapabilities = None
                self.nextSlaveUID = None
                
                #caso especial: buslock de (x,255)
                if busOp.hbusOperationSource.hbusAddressDevNumber == HBUS_BROADCAST_ADDRESS and self.masterState in [hbusMasterState.hbusMasterSearching,hbusMasterState.hbusMasterChecking]:

                    self.pushCommand(HBUSCOMMAND_GETCH, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,HBUS_BROADCAST_ADDRESS),params=[chr(0)],callBack=self.setNextSlaveCapabilities)

                    self.masterState = hbusMasterState.hbusMasterAddressing


            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:
                self.hbusBusState = hbusBusStatus.hbusBusFree
                self.hbusBusLockedWith = None

                self.onBusFree()

            #Interrupções
            elif busOp.instruction.command == HBUSCOMMAND_INT:

                self.masterState = hbusMasterState.hbusMasterInterrupted

                #Processa
                ##@todo implementar mecanismos de interrupções para que possa ser inserido o sistema de objetos especiais do mestre
            
            if len(self.expectedResponseQueue) > 0:
                
                selectedR = None
                for r in self.expectedResponseQueue:
                    
                    if r in self.removeQueue:
                        continue
                    
                    if r.source == busOp.hbusOperationSource and r.command == busOp.instruction.command:

                        selectedR = r
                        r.timeoutHandler.cancel()
                        self.removeQueue.append(r)
                        break
                            
            if selectedR != None:
                if selectedR.actionParameters != None:
                    selectedR.dCallback.callback((selectedR.actionParameters,busOp.instruction.params))
                else:
                    selectedR.dCallback.callback(busOp.instruction.params)
        else:
            
            if busOp.instruction.command == HBUSCOMMAND_BUSLOCK:
                
                self.hbusBusState = hbusBusStatus.hbusBusLockedOther
                
            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:
                
                self.hbusBusState = hbusBusStatus.hbusBusFree
                self.hbusBusLockedWith = None
                
                self.onBusFree()
                
    def pushCommand(self,command,dest,params=(),callBack=None,callBackParams=None,timeout=1000,timeoutCallBack=None,timeoutCallBackParams=None,immediate=False,deferredReturn=None):
        
        d = None
        
        if self.hbusRxState != hbusMasterRxState.hbusRXSBID and immediate == False:
            d = defer.Deferred()
            d.addCallback(self.pushCommand,command,dest,params,callBack,callBackParams,timeout,timeoutCallBack,timeoutCallBackParams)
            self.outgoingCommands.appendleft(d)
            
            return d
        else:
            if callBack != None:
                
                try:
                    d = self.expectResponse(HBUS_RESPONSEPAIRS[command],dest,action=callBack,actionParameters=callBackParams,timeout=timeout,
                                            timeoutAction=timeoutCallBack,timeoutActionParameters=timeoutCallBackParams)
                except:
                    d = None
            
            elif timeoutCallBack != None:
                
                try:
                    d = self.expectResponse(HBUS_RESPONSEPAIRS[command], dest, None, None, timeout, timeoutCallBack,timeoutCallBackParams)
                except:
                    d = None
            
            self.lastSent = (command,dest,params)
            self.sendCommand(command,dest,params)
            
            return d

    def sendCommand(self,command, dest, params=(),block=False):
        
        #blocante!!
        if block:
            while self.hbusRxState != 0:
                pass
        
        busOp = hbusOperation(hbusInstruction(command, len(params), params),dest,self.hbusMasterAddr)
        
        self.logger.debug(busOp)
        
        if command == HBUSCOMMAND_BUSLOCK:
            
            self.hbusBusState = hbusBusStatus.hbusBusLockedThis
            self.hbusBusLockedWith = dest
            
        elif command == HBUSCOMMAND_BUSUNLOCK:
            
            if self.hbusBusState == hbusBusStatus.hbusBusLockedThis and self.hbusBusLockedWith == dest:
                
                self.hbusBusState = hbusBusStatus.hbusBusFree
                self.hbusBusLockedWith = None
                self.onBusFree()
                
            else:
                
                self.logger.debug("BUSUNLOCK error: locked with %s, tried unlocking %s" % (self.hbusBusLockedWith,dest))
                
        self.txBytes += len(busOp.getString())
        if self.masterState == hbusMasterState.hbusMasterScanning:
            reactor.callFromThread(self.serialWrite,busOp.getString()) #@UndefinedVariable
        else:
            self.serialWrite(busOp.getString())
        
    def expectResponse(self, command, source, action=None, actionParameters=None, timeout=1000, timeoutAction=None, timeoutActionParameters=None):
        
        d = defer.Deferred()
        
        d.addCallback(action)
        d.addErrback(timeoutAction)
        
        pending = hbusPendingAnswer(command,source,timeout,d,actionParameters,timeoutAction,timeoutActionParameters)
        
        #timeout handler
        timeoutHandler = reactor.callLater(timeout/1000,self.responseTimeoutCallback,pending) #@UndefinedVariable
        pending.addTimeoutHandler(timeoutHandler)
        
        self.expectedResponseQueue.append(pending)
        
        return d
        
    def registerNewSlave(self, address, slaveInfo=None):
        """Registers a new device in the bus.
        @param address device address
        @param slaveInfo for virtual devices, complete description
        """
        if slaveInfo != None:
            if slaveInfo.virtual == True:
                #virtual device
                #doesn't know virtual bus number
                addr = hbusDeviceAddress(VIRTUAL_BUS,address)
                slaveInfo.hbusSlaveAddress = addr
                self.virtualDeviceList[addr.getGlobalID()] = slaveInfo
            else:
                #not supported
                raise UserWarning("adding pre-formed real device not supported")
                return
        else:
            self.detectedSlaveList[address.getGlobalID()] = hbusSlaveInfo(address)
        
        self.logger.info("New device registered at "+str(address))
        self.logger.debug("New device UID is "+str(address.getGlobalID()))
        
        #self.readBasicSlaveInformation(address)
        
    def unRegisterSlave(self, address, virtual=False):
        
        if virtual == True:
            del self.virtualSlaveList[hbusSlaveAddress(VIRTUAL_BUS,address).getGlobalID()]
        else:
            del self.detectedSlaveList[address.getGlobalID()]
        
        self.logger.info("Device at "+str(address)+" removed")
        
    def slaveReadStart(self):
        
        self.slaveReadDeferred.callback(None)
        
    def slaveReadEnded(self,callBackResult):
        
        #self.logger.debug("Device information retrieval ended.")
        
        #self.slaveReadDeferred = None
        
        self.masterState = hbusMasterState.hbusMasterOperational
        #reactor.callInThread(self.processHiddenObjects)
        self.logger.info("Device information retrieval finished.")
        self.logger.debug("tx: %d, rx %d bytes",self.txBytes,self.rxBytes)
        
        self.enterOperational()
        
    def readBasicSlaveInformationEnded(self,*params):
        
        d = defer.Deferred()
        d.addCallback(self.readExtendedSlaveInformation)
        
        if params[0].getGlobalID() == self.detectedSlaveList.keys()[-1]:
            self.slaveReadDeferred.addCallback(self.slaveReadEnded)
            
        reactor.callLater(0.1,d.callback,*params) #@UndefinedVariable
        
        return d
        
    def readSlaveObjectInformationFailed(self,params):
        
        self.logger.warning("Failure while analyzing device")
        
        self.slaveScanDeferred.errback(IOError("Failure while analyzing device"))
        
    def readBasicSlaveInformationFailed(self,*params):
        
        failure, address, = params
        
        #nova tentativa ao fim da enumeração
        if self.detectedSlaveList[address.getGlobalID()].scanRetryCount < 3:
            self.slaveReadDeferred.addCallback(self.readBasicSlaveInformation,address)
            self.detectedSlaveList[address.getGlobalID()].scanRetryCount += 1
        else:
            if address.getGlobalID() == self.detectedSlaveList.keys()[-1]:
                self.slaveReadDeferred.addCallback(self.slaveReadEnded)
    
    def readExtendedSlaveInformationEnded(self,*params):
        
        result,address = params
        
        self.detectedSlaveList[address.getGlobalID()].hbusSlaveHiddenObjects = None
        
        pass
    
    def readExtendedSlaveInformationFailed(self,*params):
        
        failure, address, = params
        
        #nova tentativa ao fim da enumeração
        #if self.detectedSlaveList[address.getGlobalID()].scanRetryCount < 3:
        #    self.slaveHiddenDeferred.addCallback(self.readExtendedSlaveInformation,address)
        #    self.detectedSlaveList[address.getGlobalID()].scanRetryCount += 1
    
    def readExtendedSlaveInformation(self,*params):
        
        self.logger.debug("Invisible objects being processed now")
        
        address = params[0]
        
        if address == None:
            address = params[1]
        
        self.detectedSlaveList[address.getGlobalID()].scanRetryCount = 0
        
        d = defer.Deferred()
        
        for obj in self.detectedSlaveList[address.getGlobalID()].hbusSlaveHiddenObjects.keys():
            d.addCallback(self.readSlaveHiddenObject,address,obj)
            d.addCallback(self.processHiddenObject,address,obj)
        
        d.addCallback(self.readExtendedSlaveInformationEnded,address)
        d.addErrback(self.readExtendedSlaveInformationFailed,address)
        self.slaveHiddenDeferred = d
        
        #inicia
        reactor.callLater(0.1,d.callback,None) #@UndefinedVariable
        
        return d
    
    def processHiddenObject(self,deferredResult,address,objectNumber):
        
        ##@todo verificar exceções aqui
        
        obj = self.detectedSlaveList[address.getGlobalID()].hbusSlaveHiddenObjects[objectNumber]
        slave = self.detectedSlaveList[address.getGlobalID()]
        
        objFunction = obj.objectDescription.split(':')
        objList = objFunction[0].split(',')
        
        for objSel in objList:
            x= re.match(r"([0-9]+)-([0-9]+)",objSel)
            
            if x != None:
                
                for rangeObj in range(int(x.group(1)),int(x.group(2))+1):
                    
                    if slave.hbusSlaveObjects[rangeObj].objectExtendedInfo == None:
                        slave.hbusSlaveObjects[rangeObj].objectExtendedInfo = {}
                        
                        slave.hbusSlaveObjects[rangeObj].objectExtendedInfo[objFunction[1]] = obj.objectLastValue
                        
            else:
                if slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo == None:
                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo = {}
                    
                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo[objFunction[1]] = obj.objectLastValue
        
    ##@todo this method is horrible
    def readBasicSlaveInformation(self,deferResult, address):
        
        self.logger.debug("Initializing device analysis "+str(address.getGlobalID()))
        
        d = defer.Deferred()
        d.addCallback(self.readBasicSlaveInformationEnded)
        d.addErrback(self.readBasicSlaveInformationFailed,address)
        self.slaveScanDeferred = d
        
        
        self.detectedSlaveList[address.getGlobalID()].readEndedCallback = d
        self.detectedSlaveList[address.getGlobalID()].readEndedParams = address
        
        #executa BUSLOCK
        #self.sendCommand(HBUSCOMMAND_BUSLOCK,address)
        
        #self.expectResponse(HBUSCOMMAND_QUERY_RESP,address,self.receiveSlaveInformation,actionParameters=("Q",address))
        self.pushCommand(HBUSCOMMAND_QUERY, address,params=[0],callBack=self.receiveSlaveInformation,callBackParams=("Q",address)
                         ,timeoutCallBack=self.readSlaveObjectInformationFailed)
        
        return d
    
    def receiveSlaveInformation(self, data):
        
        if data[0][0] == "Q":
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveDescription = ''.join(data[1][4::]) #descrição do escravo
            
            
            #lê informação sobre objetos do escravo
            #self.expectResponse(HBUSCOMMAND_RESPONSE,data[0][1],self.receiveSlaveInformation,actionParameters=("V",data[0][1]))
            self.pushCommand(HBUSCOMMAND_GETCH,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("V",data[0][1])
                             ,timeoutCallBack=self.readSlaveObjectInformationFailed)
            
        elif data[0][0] == "V":
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjectCount = ord(data[1][0])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpointCount = ord(data[1][1])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount = ord(data[1][2])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveCapabilities = ord(data[1][3])
            
            #capabilities
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveHasAUTH = True if ord(data[1][3]) & hbusSlaveCapabilities.hbusSlaveAuthSupport else False
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveHasCRYPTO = True if ord(data[1][3]) & hbusSlaveCapabilities.hbusSlaveCryptoSupport else False
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveHasEP = True if ord(data[1][3]) & hbusSlaveCapabilities.hbusSlaveEndpointSupport else False
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveHasINT = True if ord(data[1][3]) & hbusSlaveCapabilities.hbusSlaveIntSupport else False
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveHasUCODE = True if ord(data[1][3]) & hbusSlaveCapabilities.hbusSlaveUCODESupport else False
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveHasREVAUTH = True if ord(data[1][3]) & hbusSlaveCapabilities.hbusSlaveRevAuthSupport else False
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveUniqueDeviceInfo, = struct.unpack('I',''.join(data[1][4:8]))
            
            #self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
            
            self.logger.info("Device at "+str(data[0][1])+" identified as "+str(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveDescription)+"("+str(ord(data[1][0]))+","+str(ord(data[1][1]))+","+str(ord(data[1][2]))+") <"+str(
                hex(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveUniqueDeviceInfo))+">")
            
            self.logger.debug("Retrieving device's objects information "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects = {}
            
            #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
            self.pushCommand(HBUSCOMMAND_QUERY,data[0][1],params=[1],callBack=self.receiveSlaveInformation,callBackParams=("O",data[0][1])
                             ,timeoutCallBack=self.readSlaveObjectInformationFailed)
            
        elif data[0][0] == "O":
            
            currentObject = len(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects)+1
            
            self.logger.debug("Analysing object "+str(currentObject)+", in device with ID "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject] = hbusSlaveObjectInfo()
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectPermissions = ord(data[1][0]) & 0x03
            
            if ord(data[1][0]) & 0x04:
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectCrypto = True
                
            if ord(data[1][0]) & 0x08:
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectHidden = True
                
            if (ord(data[1][0]) & 0x30) == 0: 
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDataType = hbusSlaveObjectDataType.dataTypeInt
            else:
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDataType = ord(data[1][0]) & 0x30
                
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectLevel = (ord(data[1][0]) & 0xC0)>>6;
                            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectSize = ord(data[1][1])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDataTypeInfo = ord(data[1][2])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDescription = ''.join(data[1][4::])
            
            if currentObject+1 < self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjectCount:
                
                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY,data[0][1],params=[currentObject+1],callBack=self.receiveSlaveInformation,callBackParams=("O",data[0][1])
                                 ,timeoutCallBack=self.readSlaveObjectInformationFailed)
            else:
                
                #RECEBE ENDPOINT INFO
                if self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpointCount > 0:
                    
                    self.logger.debug("Retrieving device's endpoints information "+str(data[0][1].getGlobalID()))
                    
                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_EP,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("E",data[0][1]))
                    
                elif self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount > 0:
                    
                    self.logger.debug("Retrieving device's interrupts information "+str(data[0][1].getGlobalID()))
                    
                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1])
                                     ,timeoutCallBack=self.readSlaveObjectInformationFailed)
                
                else:
                    #self.pushCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug("Analysis of device "+str(data[0][1].getGlobalID())+" finished")
                    #self.processHiddenObjects(self.detectedSlaveList[data[0][1].getGlobalID()])
                    self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
                    
                    self.detectedSlaveList[data[0][1].getGlobalID()].sortObjects()
                    
                    if self.detectedSlaveList[data[0][1].getGlobalID()].readEndedCallback != None:
                        reactor.callLater(HBUS_SLAVE_QUERY_INTERVAL,self.detectedSlaveList[data[0][1].getGlobalID()].readEndedCallback.callback,self.detectedSlaveList[data[0][1].getGlobalID()].readEndedParams) #@UndefinedVariable
        
        elif data[0][0] == "E":
            
            #ENDPOINTS
            
            currentEndpoint = len(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints)+1
            
            self.logger.debug("Analysing endpoint "+str(currentEndpoint)+", device with ID "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint] = hbusSlaveEndpointInfo()
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint].endpointDirection = ord(data[1][0])
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint].endpointBlockSize = ord(data[1][1])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint].endpointDescription = ''.join(data[1][3::])
            
            if currentEndpoint+1 < self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpointCount:
                
                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY_EP,data[0][1],params=[currentEndpoint+1],callBack=self.receiveSlaveInformation,callBackParams=("E",data[0][1])
                                 ,timeoutCallBack=self.readSlaveObjectInformationFailed)
                
            else:
                
                #INTERRUPT INFO
                if self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount > 0:
                    
                    self.logger.debug("Recuperando informações das interrupções do escravo "+str(data[0][1].getGlobalID()))
                    
                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1])
                                     ,timeoutCallBack=self.readSlaveObjectInformationFailed)
                
                else:
                    #self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug("análise escravo "+str(data[0][1].getGlobalID())+" completa")
                    self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
                    
                    self.detectedSlaveList[data[0][1].getGlobalID()].sortObjects()
                    
                    if self.detectedSlaveList[data[0][1].getGlobalID()].readEndedCallback != None:
                        reactor.callLater(HBUS_SLAVE_QUERY_INTERVAL,self.detectedSlaveList[data[0][1].getGlobalID()].readEndedCallback.callback,self.detectedSlaveList[data[0][1].getGlobalID()].readEndedParams) #@UndefinedVariable
                    
        elif data[0][0] == "I":
            
            #INTERRUPTS
            
            currentInterrupt = len(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts)+1
            
            self.logger.debug("Analisando interrupção "+str(currentInterrupt)+", escravo ID "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts[currentInterrupt] = hbusSlaveInterruptInfo()
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts[currentInterrupt].interruptFlags = ord(data[1][0])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts[currentInterrupt].interruptDescription = ''.join(data[1][2::])
            
            if currentInterrupt+1 < self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount:
                
                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[currentInterrupt+1],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1])
                                 ,timeoutCallBack=self.readSlaveObjectInformationFailed)
                
            else:
                #self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                self.logger.debug("análise escravo "+str(data[0][1].getGlobalID())+" completa")
                #self.processHiddenObjects(self.detectedSlaveList[data[0][1].getGlobalID()])
                self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
                
                self.detectedSlaveList[data[0][1].getGlobalID()].sortObjects()
                
                if self.detectedSlaveList[data[0][1].getGlobalID()].readEndedCallback != None:
                    reactor.callLater(HBUS_SLAVE_QUERY_INTERVAL,self.detectedSlaveList[data[0][1].getGlobalID()].readEndedCallback.callback,self.detectedSlaveList[data[0][1].getGlobalID()].readEndedParams) #@UndefinedVariable
        
        elif data[0][0] == "D":
            
            #info dump
            pass
        
    def readSlaveObject(self,address,number,callBack=None,timeoutCallback=None):
        
        d = None
        
        #see if this is a virtual device first
        if address.busNumber == VIRTUAL_BUS:
            #read and update
            result = self.pluginManager.readVirtualDeviceObject(address.devNumber,number)
            self.virtualDeviceList[address.getGlobalID()].hbusSlaveObjects[number].objectLastValue = result
            
            if callBack != None:
                callBack(result)
            return

        if self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectPermissions != hbusSlaveObjectPermissions.hbusSlaveObjectWrite:
        
            #self.expectResponse(HBUSCOMMAND_RESPONSE,address,self.receiveSlaveObjectData,actionParameters=(address,number,callBack),timeoutAction=timeoutCallback)
            #self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack))
            d = self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack),
                                 timeoutCallBack=timeoutCallback)
            
        else:
            
            self.logger.warning("Write-only object read attempted")
            self.logger.debug("Tried reading object %d of slave with address %s",number,address)
            
            if callBack != None:
                
                callBack(None)
                
        return d
    
    def readSlaveHiddenObject(self,*params):
        
        if isinstance(params[0],hbusDeviceAddress):
            address = params[0]
            number = params[1]
        elif isinstance(params[1],hbusDeviceAddress):
            address = params[1]
            number = params[2]
        else:
            raise ValueError('')
        
        d = None
        
        if self.detectedSlaveList[address.getGlobalID()].hbusSlaveHiddenObjects[number].objectPermissions != hbusSlaveObjectPermissions.hbusSlaveObjectWrite:
        
            #self.expectResponse(HBUSCOMMAND_RESPONSE,address,self.receiveSlaveObjectData,actionParameters=(address,number,callBack),timeoutAction=timeoutCallback)
            #self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack))
            d = self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveHiddenObjectData,callBackParams=(address,number,None),
                                 timeoutCallBack=None)
            
        else:
            
            self.logger.warning("Tentativa de leitura de objeto somente para escrita")
            self.logger.debug("Tentativa de leitura do objeto %d, escravo com endereço %s",number,address)
            
            #if callBack != None:
            #    
            #    callBack(None)
                
        return d
            
    def receiveSlaveObjectData(self, data):
        
        self.detectedSlaveList[data[0][0].getGlobalID()].hbusSlaveObjects[data[0][1]].objectLastValue = [ord(d) for d in data[1]]
        
        if data[0][2] != None:
            
            data[0][2](data[1])
            
    def receiveSlaveHiddenObjectData(self, data):
        
        self.detectedSlaveList[data[0][0].getGlobalID()].hbusSlaveHiddenObjects[data[0][1]].objectLastValue = [ord(d) for d in data[1]]
        
        if data[0][2] != None:
            
            data[0][2](data[1])
            
    def writeSlaveObject(self,address,number,value):

        #check if is virtual bus
        if address.busNumber == VIRTUAL_BUS:
            self.virtualDeviceList[address.getGlobalID()].hbusSlaveObjects[number].objectLastValue = value
            self.pluginManager.writeVirtualDeviceObject(address.devNumber, number, value)
            return
        
        if self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectPermissions != hbusSlaveObjectPermissions.hbusSlaveObjectRead:
            
            self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectLastValue = value
            size = self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectSize
            
            myParamList = [number,size]
            myParamList.extend(value)
            
            if (self.detectedSlaveList[address.getGlobalID()].hbusSlaveCapabilities & hbusSlaveCapabilities.hbusSlaveAuthSupport):
                
                myParamList[1] += HBUS_SIGNATURE_SIZE+1
                
                msg = struct.pack('ccccccc',chr(self.hbusMasterAddr.hbusAddressBusNumber),chr(self.hbusMasterAddr.hbusAddressDevNumber),chr(address.hbusAddressBusNumber),
                                  chr(address.hbusAddressDevNumber),chr(HBUSCOMMAND_SETCH.commandByte),chr(number),chr(myParamList[1]))
                
                i = 0
                while (size > 0):
                    struct.pack_into('c',msg,7+i,value[i])
                    
                    size -= 1
                    i += 1
                    
                sig = hbus_crypto.hbusCrypto_RabinWilliamsSign(msg, HBUS_ASYMMETRIC_KEYS.privatep, HBUS_ASYMMETRIC_KEYS.privateq)
                
                myParamList.extend(sig.getByteString())
            
            self.pushCommand(HBUSCOMMAND_SETCH,address,params=myParamList)
            
        else:
            
            self.logger.warning("tentativa de escrita em objeto somente leitura")
            
    def writeFormattedSlaveObject(self,address,number,value):
        
        #decodifica formatação e realiza escrita no objeto
        
        obj = self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number]
        
        data = hbusSlaveObjectDataType.dataTypeOptions[obj.objectDataType][obj.objectDataTypeInfo](hbusSlaveObjectDataType(),data=value,extInfo=obj.objectExtendedInfo,decode=True,size=obj.objectSize)
        
        self.writeSlaveObject(address, number, data)
    
    def pingSlave(self,callback, address, successCallback=None, failureCallback=None):
        
        if successCallback == None:
            successCallback = self.slavePongOK
        
        if failureCallback == None:
            failureCallback = self.slavePongFailed
        
        d = self.pushCommand(HBUSCOMMAND_SEARCH,address,callBack=successCallback,callBackParams=address,timeout=3000,
                             timeoutCallBack=failureCallback,timeoutCallBackParams=address)
        
        return d
    
    def deferredDelay(self,time):
        
        d = defer.Deferred()
        d.addCallback(self.dummyCallback)
        
        reactor.callLater(time,d.callback,None) #@UndefinedVariable
        
        return d
    
    def dummyCallback(self,*params):
        
        #delay
        
        pass
    
    def slavePongOK(self,*params):
        
        address = params[0][0]
        
        if address.getGlobalID() not in self.detectedSlaveList.keys():
            if address in self.staticSlaveList:
                self.logger.info("Device with static address present")
                self.registerNewSlave(address)

        if self.detectedSlaveList[address.getGlobalID()].pingRetryCount > 0:
            self.detectedSlaveList[address.getGlobalID()].pingRetryCount = 0
            self.detectedSlaveList[address.getGlobalID()].pingFailures += 1
        
        return self.deferredDelay(0.1)
    
    def slavePongFailed(self,*params):
        
        address = params[0].value.args[0]
        
        if address.getGlobalID() in self.detectedSlaveList.keys():
        
            if self.detectedSlaveList[address.getGlobalID()].pingRetryCount < 3:
                self.detectedSlaveList[address.getGlobalID()].pingRetryCount += 1
            else:
                self.logger.warning("Removing device from bus for unresponsiveness")
                self.unRegisterSlave(address)
        else:
            #é um escravo estático
            pass
        
        return self.deferredDelay(0.1)

    def detectSlaves(self, callBack=None, allBusses=False):
        
        self.pushCommand(HBUSCOMMAND_SEARCH, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,255))
        
        if self.masterState == hbusMasterState.hbusMasterOperational:
            self.masterState = hbusMasterState.hbusMasterChecking
        else:
            self.masterState = hbusMasterState.hbusMasterSearching
            self.logger.info("Starting device search")
        
        reactor.callLater(5,self.handleAlarm) #@UndefinedVariable
        
        self.detectSlavesEnded = callBack
        
    def checkSlaves(self):
        
        d = defer.Deferred()
        
        #escravos endereçados
        for slave in self.detectedSlaveList.values():
            
            if slave.hbusSlaveAddress in self.staticSlaveList:
                continue
            
            d.addCallback(self.pingSlave,slave.hbusSlaveAddress)
        
        #escravos estáticos
        for address in self.staticSlaveList:
            d.addCallback(self.pingSlave,address)
            
        d.addCallback(self.getSlavesMissingInformation)
        
        #novos escravos
        d.addCallback(self.detectSlaves)
        
        #inicia cadeia de callbacks
        d.callback(None)
             
    def getSlavesMissingInformation(self,callbackResult):
        
        d = defer.Deferred()
        
        for slave in self.detectedSlaveList.values():
            if slave.basicInformationRetrieved == False:
                d.addCallback(self.readBasicSlaveInformation, slave.hbusSlaveAddress)
                
        self.slaveReadDeferred = d
        reactor.callLater(0.1,self.slaveReadStart) #@UndefinedVariable
        
        return d
    
    def handleAlarm(self):
        
        if self.masterState in [hbusMasterState.hbusMasterSearching,hbusMasterState.hbusMasterChecking] :
            
            if self.masterState == hbusMasterState.hbusMasterSearching:
                self.logger.info("Device search ended, "+str(self.registeredSlaveCount)+" found")
            
            if self.detectSlavesEnded != None:
                
                self.detectSlavesEnded()
            
            self.logger.debug("Retrieving devices information...")
            
            if self.masterState == hbusMasterState.hbusMasterSearching:
                self.processStaticSlaves()
            
            self.masterState = hbusMasterState.hbusMasterScanning
            
            d = defer.Deferred()
            
            i = 0
            for slave in self.detectedSlaveList:
                
                if self.detectedSlaveList[slave].basicInformationRetrieved == True:
                    continue
                
                d.addCallback(self.readBasicSlaveInformation,self.detectedSlaveList[slave].hbusSlaveAddress)
                i += 1
                
            if i > 0:
                self.slaveReadDeferred = d
                
                reactor.callLater(0.1,self.slaveReadStart) #@UndefinedVariable
            
            else:
                
                self.masterState = hbusMasterState.hbusMasterOperational
            
        elif self.masterState == hbusMasterState.hbusMasterStarting:
            
            self.masterState = hbusMasterState.hbusMasterIdle
            
            self.detectSlaves()
            
    def findDeviceByUID(self, uid):
        
        for dev in self.detectedSlaveList:
            
            if self.detectedSlaveList[dev].hbusSlaveUniqueDeviceInfo == int(uid):
                
                return self.detectedSlaveList[dev].hbusSlaveAddress
            
        self.logger.debug("dispositivo com UID <"+str(int(uid))+"> não encontrado")
        return None
    
    def responseTimeoutCallback(self,response):
        
        
        self.logger.warning('Timeout de resposta')
        self.logger.debug("Timeout de resposta: %s",response)
        
        if self.hbusBusState == hbusBusStatus.hbusBusLockedThis:
            self.pushCommand(HBUSCOMMAND_BUSUNLOCK, self.hbusBusLockedWith)

        if self.masterState == hbusMasterState.hbusMasterScanning:
            self.hbusDeviceScanningTimeout = True
            
        response.dCallback.errback(HBUSTimeoutException(response.timeoutActionParameters))
        
        self.expectedResponseQueue.remove(response)
        
        #if response.timeoutAction != None:
        #    response.timeoutAction(response.source)
        
        #response.tCallback.callback(response.source)
    
    def periodicCall(self):
        
        #expectedResponseQueue cleanup
        
        for r in self.removeQueue:
            
            if r in self.expectedResponseQueue:
                
                self.expectedResponseQueue.remove(r)
                
        del self.removeQueue[:]
        
        #if allBusses:
        #    
        #    for b in range(0,32):
        #        
        #        for d in range(0,32):
        #            
        #            self.sendCommand(HBUSCOMMAND_SEARCH, hbusDeviceAddress(b,d))
        #            self.expectResponse(HBUSCOMMAND_ACK, hbusDeviceAddress(b,d))
        #            
        #else:
        #    
        #    for d in range(1,32):
        #        
        #        self.sendCommand(HBUSCOMMAND_SEARCH,hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,d))
        #        self.expectResponse(HBUSCOMMAND_ACK,hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,d),action=self.registerNewSlave,actionParameters=hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,d),timeout=10000000)
    def processStaticSlaves(self):
        
        for addr in self.staticSlaveList:
            
            if addr.getGlobalID() in self.detectedSlaveList:
                continue
            
            self.logger.info("Device with static address in %s",str(addr))
            
            self.registerNewSlave(addr)
            
            pass
        
    def onBusLocked(self):
        
        pass
        
    def onBusFree(self):
        
        while len(self.awaitingFreeBus):
            
            d = self.awaitingFreeBus.pop()
            d.callback(None)
        
