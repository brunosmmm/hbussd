# coding=utf-8

##@package hbusmaster
# main HBUS master module
# @author Bruno Morais <brunosmmm@gmail.com>
# @date 2012-2015
# @todo decouple and sanitize device scanning logic
# @todo merge virtual and normal devices into one dictionary

import struct
from datetime import datetime
import logging
from collections import deque
import hbus_crypto
import json

from twisted.internet import reactor, defer
from twisted.internet.protocol import Factory

from hbus_constants import *
from hbus_base import *
from hbus_except import *
from hbusslaves import *
from hbus_datahandlers import *
from hbusmasterobjects import *
from fakebus import hbus_fb
from hbussd_plugin import HbusPluginManager
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

##HBUS security key set
##@todo this is not useful at all currently
#key is a number tuple (p,q)
class hbusKeySet:

    ##Key p
    privateq = None
    ##Key q
    privatep = None


    def __init__(self,p,q):

        self.privatep = p
        self.privateq = q

    def pubKeyInt(self):

        return self.privatep*self.privateq

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

class HbusMaster:

    pluginManager = None

    hbusSerialRxTimeout = 100

    hbusBusState = HbusBusState.FREE
    hbusBusLockedWith = None
    hbusRxState = HbusRXState.SBID

    communicationBuffer = []
    SearchTimer = None

    receivedMessages = []
    expectedResponseQueue = deque()

    awaitingFreeBus = deque()

    outgoingCommands = deque()

    removeQueue = []

    detectedSlaveList = {}
    virtualDeviceList = {}

    staticSlaveList = []

    registeredSlaveCount = 0
    virtualSlaveCount = 0

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

    def __init__(self, port, baudrate=100000, busno=0, conf_file=None):

        self.serialPort = port
        self.serialBaud = baudrate
        self.hbusMasterAddr = HbusDeviceAddress(busno, 0)

        self.logger = logging.getLogger('hbussd.hbusmaster')
        self.pluginManager = HbusPluginManager('./plugins', self)
        self.searchAndLoadPlugins()

        if port == None:
            #create fakebus system
            f = Factory()
            f.protocol = hbus_fb.FakeBusSerialPort
            reactor.listenTCP(9090, f)

            self.serialCreate(fake=True)
        else:
            self.serialCreate(fake=False)

        #configuration parameters
        self.conf_param = {}
        self._load_configuration(conf_file)

        #system started event
        event = hbusMasterEvent(hbusMasterEventType.eventStarted)
        self.pluginManager.m_evt_broadcast(event)

    def _load_configuration(self, conf_file):

        if conf_file is None:
            return

        try:
            with open(conf_file, 'r') as f:
                self.conf_param = json.load(f)
        except IOError:
            return # for now

        #process some configuration params
        if 'staticSlaveList' in self.conf_param:
            for addr in self.conf_param['staticSlaveList']:
                if 'busNum' not in addr:
                    continue
                if 'devNum' not in addr:
                    continue

                self.staticSlaveList.append(HbusDeviceAddress(int(addr['busNum']), int(addr['devNum'])))


    ##Search and load plugins using plugin manager
    def searchAndLoadPlugins(self):

        self.logger.debug("scanning plugins")

        self.pluginManager.scan_plugins()

        for plugin in self.pluginManager.get_available_plugins():
            #try:
            #    self.logger.debug('loading plugin '+plugin)
            self.pluginManager.m_load_plugin(plugin)
            #except:
            #    self.logger.debug('error loading plugin '+plugin)

    ##Master entering operational phase
    def enterOperational(self):

        #broadcast event to plugin system
        event = hbusMasterEvent(hbusMasterEventType.eventOperational)
        self.pluginManager.m_evt_broadcast(event)


    def getInformationData(self):

        busses = list(set([slave.hbusSlaveAddress.bus_number for slave in self.detectedSlaveList.values() if slave.basicInformationRetrieved == True]))

        if len(self.virtualDeviceList) > 0:
            busses.append(VIRTUAL_BUS)

        return hbusMasterInformationData(len(self.detectedSlaveList), busses)


    def serialCreate(self):

        pass #overload!!

    def serialConnected(self):

        #reset all devices
        self.logger.debug("Connected. Resetting all devices now")

        address = HbusDeviceAddress(self.hbusMasterAddr.bus_number,HBUS_BROADCAST_ADDRESS)

        size = HBUS_SIGNATURE_SIZE+1

        myParamList = [chr(size)]

        msg = struct.pack('cccccc',chr(self.hbusMasterAddr.bus_number),chr(self.hbusMasterAddr.dev_number),chr(address.bus_number),
                                chr(address.dev_number),chr(HBUSCOMMAND_SOFTRESET.cmd_byte),myParamList[0])

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

        self.hbusRxState = HbusRXState.SBID

        if len(self.outgoingCommands) > 0:
            d = self.outgoingCommands.pop()
            d.callback(None)


    def serialNewData(self,data):

        for d in data:

            self.rxBytes += 1

            if self.hbusRxState == HbusRXState.SBID:

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.SDID

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.SDID:

                self.RXTimeout.cancel()

                #check address
                if (ord(d) > 32) and (ord(d) != 255):
                    self.serialRXMachineEnterIdle()

                    self.logger.debug("Invalid address in received packet")
                    return

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.TBID

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.TBID:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.TDID

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.TDID:

                self.RXTimeout.cancel()

                #check address
                if (ord(d) > 32) and (ord(d) != 255):
                    self.serialRXMachineEnterIdle()

                    self.logger.debug("Invalid address in received packet")
                    return

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.CMD

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.CMD:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                if ord(d) == HBUSCOMMAND_ACK.cmd_byte or ord(d) == HBUSCOMMAND_SEARCH.cmd_byte or ord(d) == HBUSCOMMAND_BUSLOCK.cmd_byte or ord(d) == HBUSCOMMAND_BUSUNLOCK.cmd_byte or ord(d) == HBUSCOMMAND_SOFTRESET.cmd_byte:
                    self.hbusRxState = HbusRXState.STP
                else:
                    self.hbusRxState = HbusRXState.ADDR

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.ADDR:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                if ord(self.communicationBuffer[4]) == HBUSCOMMAND_GETCH.cmd_byte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY.cmd_byte or\
                ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY_EP.cmd_byte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY_INT.cmd_byte:
                    self.hbusRxState = HbusRXState.STP
                else:
                    self.hbusRxState = HbusRXState.PSZ

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.PSZ:

                self.RXTimeout.cancel()

                if ord(self.communicationBuffer[4]) != HBUSCOMMAND_STREAMW.cmd_byte and ord(self.communicationBuffer[4]) != HBUSCOMMAND_STREAMR.cmd_byte:
                    if ord(d) > 64:
                        d = chr(64)

                self.communicationBuffer.append(d)
                self.lastPacketParamSize = ord(d)

                if ord(self.communicationBuffer[4]) == HBUSCOMMAND_STREAMW.cmd_byte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_STREAMR.cmd_byte:
                    self.hbusRxState = HbusRXState.STP
                else:
                    if ord(d) > 0:
                        self.hbusRxState = HbusRXState.PRM
                    else:
                        self.hbusRxState = HbusRXState.STP

                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout) #@UndefinedVariable

            elif self.hbusRxState == HbusRXState.PRM:

                self.RXTimeout.cancel()

                if len(self.communicationBuffer) <= (6 + self.lastPacketParamSize):
                    self.communicationBuffer.append(d)
                else:

                #self.hbusRxState = HbusRXState.STP
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

            elif self.hbusRxState == HbusRXState.STP:

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

            if c.cmd_byte == cmdbyte:
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
            return AddressByUID[uid].dev_number
            self.logger.debug("Re-integrating device with UID %s", hex(uid))
        else:
            return self.registeredSlaveCount+1

    def getnewvirtualaddress(self, uid):
        uidList = [x.hbusSlaveUniqueDeviceInfo for x in self.virtualDeviceList.values()]
        addressList = [x.hbusSlaveAddress for x in self.virtualDeviceList.values()]
        addressByUid = dict(zip(uidList,addressList))

        if uid in addressByUid.keys():
            return addressByUid[uid].dev_number
        else:
            return self.virtualSlaveCount+1


    def setNextSlaveCapabilities(self,params):

        self.nextSlaveCapabilities = ord(params[3])
        self.nextSlaveUID, = struct.unpack('I',''.join(params[4:8]))

        #get new address
        nextAddress = self.getNewAddress(self.nextSlaveUID)

        if (self.nextSlaveCapabilities & HbusDeviceCapabilities.AUTHSUP):
            self.logger.debug("New device has AUTH support")


        myParamList = [chr(HBUS_PUBKEY_SIZE)]
        myParamList.extend(HBUS_ASYMMETRIC_KEYS.pubKeyStr())

        #registers slave address with next available address
        if (self.nextSlaveCapabilities & HbusDeviceCapabilities.AUTHSUP):
            self.pushCommand(HBUSCOMMAND_KEYSET, HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress),myParamList)
        else:
            self.pushCommand(HBUSCOMMAND_SEARCH, HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress))

        #update BUSLOCK state
        self.hbusBusLockedWith = HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress)

        #sends BUSUNLOCK immediately
        self.pushCommand(HBUSCOMMAND_BUSUNLOCK, HbusDeviceAddress(self.hbusMasterAddr.bus_number,nextAddress))

        self.registerNewSlave(HbusDeviceAddress(self.hbusMasterAddr.bus_number,nextAddress))

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
            busOp = HbusOperation(HbusInstruction(self.getCommand(ord(data[4])), pSize, params), HbusDeviceAddress(ord(data[2]), ord(data[3])), HbusDeviceAddress(ord(data[0]),ord(data[1])))
        except:

            self.logger.warning("Invalid packet was received")
            return

        if busOp.source.dev_number == 0:
            self.logger.debug("Illegal packet ignored: reserved addres")
            return

        self.logger.debug(busOp)
        #print busOp

        if busOp.destination == self.hbusMasterAddr:

            self.receivedMessages.append(busOp)

            if busOp.instruction.command == HBUSCOMMAND_BUSLOCK:
                self.hbusBusState = HbusBusState.LOCKED_THIS
                self.hbusBusLockedWith = busOp.source
                self.nextSlaveCapabilities = None
                self.nextSlaveUID = None

                #exception: buslock from (x,255)
                if busOp.source.dev_number == HBUS_BROADCAST_ADDRESS and self.masterState in [hbusMasterState.hbusMasterSearching,hbusMasterState.hbusMasterChecking]:

                    self.pushCommand(HBUSCOMMAND_GETCH, HbusDeviceAddress(self.hbusMasterAddr.bus_number,HBUS_BROADCAST_ADDRESS),params=[chr(0)],callBack=self.setNextSlaveCapabilities)

                    self.masterState = hbusMasterState.hbusMasterAddressing


            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:
                self.hbusBusState = HbusBusState.FREE
                self.hbusBusLockedWith = None

                self.onBusFree()

            #Interrupts
            elif busOp.instruction.command == HBUSCOMMAND_INT:

                self.masterState = hbusMasterState.hbusMasterInterrupted

                #Process
                ##@todo missing interrupt mechanisms for master special objects subsystem implementation

            if len(self.expectedResponseQueue) > 0:

                selectedR = None
                for r in self.expectedResponseQueue:

                    if r in self.removeQueue:
                        continue

                    if r.source == busOp.source and r.command == busOp.instruction.command:

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

                self.hbusBusState = HbusBusState.LOCKED_OTHER

            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:

                self.hbusBusState = HbusBusState.FREE
                self.hbusBusLockedWith = None

                self.onBusFree()

    def pushCommand(self,command,dest,params=(),callBack=None,callBackParams=None,timeout=1000,timeoutCallBack=None,timeoutCallBackParams=None,immediate=False,deferredReturn=None):

        d = None

        if self.hbusRxState != HbusRXState.SBID and immediate == False:
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

        #warning: blocking
        if block:
            while self.hbusRxState != 0:
                pass

        busOp = HbusOperation(HbusInstruction(command, len(params), params),dest,self.hbusMasterAddr)

        self.logger.debug(busOp)

        if command == HBUSCOMMAND_BUSLOCK:

            self.hbusBusState = HbusBusState.LOCKED_THIS
            self.hbusBusLockedWith = dest

        elif command == HBUSCOMMAND_BUSUNLOCK:

            if self.hbusBusState == HbusBusState.LOCKED_THIS and self.hbusBusLockedWith == dest:

                self.hbusBusState = HbusBusState.FREE
                self.hbusBusLockedWith = None
                self.onBusFree()

            else:

                self.logger.debug("BUSUNLOCK error: locked with %s, tried unlocking %s" % (self.hbusBusLockedWith,dest))

        self.txBytes += len(busOp.get_string())
        if self.masterState == hbusMasterState.hbusMasterScanning:
            reactor.callFromThread(self.serialWrite,busOp.get_string()) #@UndefinedVariable
        else:
            self.serialWrite(busOp.get_string())

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
            if slaveInfo.hbusSlaveIsVirtual == True:
                #virtual device
                #doesn't know virtual bus number
                addr = HbusDeviceAddress(VIRTUAL_BUS,address)
                slaveInfo.hbusSlaveAddress = addr
                self.virtualDeviceList[addr.global_id()] = slaveInfo
            else:
                #not supported
                raise UserWarning("adding pre-formed real device not supported")
                return
        else:
            addr = address
            self.detectedSlaveList[address.global_id()] = HbusDevice(address)

        self.logger.info("New device registered at "+str(addr))
        self.logger.debug("New device UID is "+str(addr.global_id()))

        #self.readBasicSlaveInformation(address)

    def unRegisterSlave(self, address, virtual=False):

        if virtual == True:
            del self.virtualDeviceList[hbusSlaveAddress(VIRTUAL_BUS,address).global_id()]
        else:
            del self.detectedSlaveList[address.global_id()]

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

        if params[0].global_id() == self.detectedSlaveList.keys()[-1]:
            self.slaveReadDeferred.addCallback(self.slaveReadEnded)

        reactor.callLater(0.1,d.callback,*params) #@UndefinedVariable

        return d

    def readSlaveObjectInformationFailed(self,params):

        self.logger.warning("Failure while analyzing device")

        self.slaveScanDeferred.errback(IOError("Failure while analyzing device"))

    def readBasicSlaveInformationFailed(self,*params):

        failure, address, = params

        #try again at enumeration end
        if self.detectedSlaveList[address.global_id()].scanRetryCount < 3:
            self.slaveReadDeferred.addCallback(self.readBasicSlaveInformation,address)
            self.detectedSlaveList[address.global_id()].scanRetryCount += 1
        else:
            if address.global_id() == self.detectedSlaveList.keys()[-1]:
                self.slaveReadDeferred.addCallback(self.slaveReadEnded)

    def readExtendedSlaveInformationEnded(self,*params):

        result,address = params

        self.detectedSlaveList[address.global_id()].hbusSlaveHiddenObjects = None

        pass

    def readExtendedSlaveInformationFailed(self,*params):

        failure, address, = params

        #if self.detectedSlaveList[address.global_id()].scanRetryCount < 3:
        #    self.slaveHiddenDeferred.addCallback(self.readExtendedSlaveInformation,address)
        #    self.detectedSlaveList[address.global_id()].scanRetryCount += 1

    def readExtendedSlaveInformation(self,*params):

        self.logger.debug("Invisible objects being processed now")

        address = params[0]

        if address == None:
            address = params[1]

        self.detectedSlaveList[address.global_id()].scanRetryCount = 0

        d = defer.Deferred()

        for obj in self.detectedSlaveList[address.global_id()].hbusSlaveHiddenObjects.keys():
            d.addCallback(self.readSlaveHiddenObject,address,obj)
            d.addCallback(self.processHiddenObject,address,obj)

        d.addCallback(self.readExtendedSlaveInformationEnded,address)
        d.addErrback(self.readExtendedSlaveInformationFailed,address)
        self.slaveHiddenDeferred = d

        #inicia
        reactor.callLater(0.1,d.callback,None) #@UndefinedVariable

        return d

    def processHiddenObject(self,deferredResult,address,objectNumber):

        ##@todo look for exceptions here

        obj = self.detectedSlaveList[address.global_id()].hbusSlaveHiddenObjects[objectNumber]
        slave = self.detectedSlaveList[address.global_id()]

        objFunction = obj.description.split(':')
        objList = objFunction[0].split(',')

        for objSel in objList:
            x= re.match(r"([0-9]+)-([0-9]+)",objSel)

            if x != None:

                for rangeObj in range(int(x.group(1)),int(x.group(2))+1):

                    if slave.hbusSlaveObjects[rangeObj].objectExtendedInfo == None:
                        slave.hbusSlaveObjects[rangeObj].objectExtendedInfo = {}

                        slave.hbusSlaveObjects[rangeObj].objectExtendedInfo[objFunction[1]] = obj.last_value

            else:
                if slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo == None:
                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo = {}

                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo[objFunction[1]] = obj.last_value

    ##@todo this method is horrible
    def readBasicSlaveInformation(self,deferResult, address):

        self.logger.debug("Initializing device analysis "+str(address.global_id()))

        d = defer.Deferred()
        d.addCallback(self.readBasicSlaveInformationEnded)
        d.addErrback(self.readBasicSlaveInformationFailed,address)
        self.slaveScanDeferred = d


        self.detectedSlaveList[address.global_id()].readEndedCallback = d
        self.detectedSlaveList[address.global_id()].readEndedParams = address

        #BUSLOCK
        #self.sendCommand(HBUSCOMMAND_BUSLOCK,address)

        #self.expectResponse(HBUSCOMMAND_QUERY_RESP,address,self.receiveSlaveInformation,actionParameters=("Q",address))
        self.pushCommand(HBUSCOMMAND_QUERY, address,params=[0],callBack=self.receiveSlaveInformation,callBackParams=("Q",address)
                         ,timeoutCallBack=self.readSlaveObjectInformationFailed)

        return d

    def receiveSlaveInformation(self, data):

        if data[0][0] == "Q":

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveDescription = ''.join(data[1][4::]) #descrição do escravo


            #read device's objects information
            #self.expectResponse(HBUSCOMMAND_RESPONSE,data[0][1],self.receiveSlaveInformation,actionParameters=("V",data[0][1]))
            self.pushCommand(HBUSCOMMAND_GETCH,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("V",data[0][1])
                             ,timeoutCallBack=self.readSlaveObjectInformationFailed)

        elif data[0][0] == "V":

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjectCount = ord(data[1][0])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpointCount = ord(data[1][1])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterruptCount = ord(data[1][2])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveCapabilities = ord(data[1][3])

            #capabilities
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveHasAUTH = True if ord(data[1][3]) & HbusDeviceCapabilities.AUTHSUP else False
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveHasCRYPTO = True if ord(data[1][3]) & HbusDeviceCapabilities.CRYPTOSUP else False
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveHasEP = True if ord(data[1][3]) & HbusDeviceCapabilities.EPSUP else False
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveHasINT = True if ord(data[1][3]) & HbusDeviceCapabilities.INTSUP else False
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveHasUCODE = True if ord(data[1][3]) & HbusDeviceCapabilities.UCODESUP else False
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveHasREVAUTH = True if ord(data[1][3]) & HbusDeviceCapabilities.REVAUTHSUP else False

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveUniqueDeviceInfo, = struct.unpack('I',''.join(data[1][4:8]))

            #self.detectedSlaveList[data[0][1].global_id()].basicInformationRetrieved = True

            self.logger.info("Device at "+str(data[0][1])+" identified as "+str(self.detectedSlaveList[data[0][1].global_id()].hbusSlaveDescription)+"("+str(ord(data[1][0]))+","+str(ord(data[1][1]))+","+str(ord(data[1][2]))+") <"+str(
                hex(self.detectedSlaveList[data[0][1].global_id()].hbusSlaveUniqueDeviceInfo))+">")

            self.logger.debug("Retrieving device's objects information "+str(data[0][1].global_id()))

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects = {}

            #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
            self.pushCommand(HBUSCOMMAND_QUERY,data[0][1],params=[1],callBack=self.receiveSlaveInformation,callBackParams=("O",data[0][1])
                             ,timeoutCallBack=self.readSlaveObjectInformationFailed)

        elif data[0][0] == "O":

            currentObject = len(self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects)+1

            self.logger.debug("Analysing object "+str(currentObject)+", in device with ID "+str(data[0][1].global_id()))

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject] = HbusDeviceObject()
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].permissions = ord(data[1][0]) & 0x03

            if ord(data[1][0]) & 0x04:
                self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].is_crypto = True

            if ord(data[1][0]) & 0x08:
                self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].hidden = True

            if (ord(data[1][0]) & 0x30) == 0:
                self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].objectDataType = HbusObjDataType.dataTypeInt
            else:
                self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].objectDataType = ord(data[1][0]) & 0x30

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].objectLevel = (ord(data[1][0]) & 0xC0)>>6;

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].size = ord(data[1][1])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].objectDataTypeInfo = ord(data[1][2])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjects[currentObject].description = ''.join(data[1][4::])

            if currentObject+1 < self.detectedSlaveList[data[0][1].global_id()].hbusSlaveObjectCount:

                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY,data[0][1],params=[currentObject+1],callBack=self.receiveSlaveInformation,callBackParams=("O",data[0][1])
                                 ,timeoutCallBack=self.readSlaveObjectInformationFailed)
            else:

                #RECEIVES ENDPOINT INFO
                if self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpointCount > 0:

                    self.logger.debug("Retrieving device's endpoints information "+str(data[0][1].global_id()))

                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_EP,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("E",data[0][1]))

                elif self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterruptCount > 0:

                    self.logger.debug("Retrieving device's interrupts information "+str(data[0][1].global_id()))

                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1])
                                     ,timeoutCallBack=self.readSlaveObjectInformationFailed)

                else:
                    #self.pushCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug("Analysis of device "+str(data[0][1].global_id())+" finished")
                    #self.processHiddenObjects(self.detectedSlaveList[data[0][1].global_id()])
                    self.detectedSlaveList[data[0][1].global_id()].basicInformationRetrieved = True

                    self.detectedSlaveList[data[0][1].global_id()].sortObjects()

                    if self.detectedSlaveList[data[0][1].global_id()].readEndedCallback != None:
                        reactor.callLater(HBUS_SLAVE_QUERY_INTERVAL,self.detectedSlaveList[data[0][1].global_id()].readEndedCallback.callback,self.detectedSlaveList[data[0][1].global_id()].readEndedParams) #@UndefinedVariable

        elif data[0][0] == "E":

            #ENDPOINTS

            currentEndpoint = len(self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpoints)+1

            self.logger.debug("Analysing endpoint "+str(currentEndpoint)+", device with ID "+str(data[0][1].global_id()))

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpoints[currentEndpoint] = HbusEndpoint()
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpoints[currentEndpoint].endpointDirection = ord(data[1][0])
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpoints[currentEndpoint].endpointBlockSize = ord(data[1][1])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpoints[currentEndpoint].endpointDescription = ''.join(data[1][3::])

            if currentEndpoint+1 < self.detectedSlaveList[data[0][1].global_id()].hbusSlaveEndpointCount:

                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY_EP,data[0][1],params=[currentEndpoint+1],callBack=self.receiveSlaveInformation,callBackParams=("E",data[0][1])
                                 ,timeoutCallBack=self.readSlaveObjectInformationFailed)

            else:

                #INTERRUPT INFO
                if self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterruptCount > 0:

                    self.logger.debug("Retrieving device's endpoints information "+str(data[0][1].global_id()))

                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1])
                                     ,timeoutCallBack=self.readSlaveObjectInformationFailed)

                else:
                    #self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug("Analysis of device "+str(data[0][1].global_id())+" finished")
                    self.detectedSlaveList[data[0][1].global_id()].basicInformationRetrieved = True

                    self.detectedSlaveList[data[0][1].global_id()].sortObjects()

                    if self.detectedSlaveList[data[0][1].global_id()].readEndedCallback != None:
                        reactor.callLater(HBUS_SLAVE_QUERY_INTERVAL,self.detectedSlaveList[data[0][1].global_id()].readEndedCallback.callback,self.detectedSlaveList[data[0][1].global_id()].readEndedParams) #@UndefinedVariable

        elif data[0][0] == "I":

            #INTERRUPTS

            currentInterrupt = len(self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterrupts)+1

            self.logger.debug("Analyzing interrupt "+str(currentInterrupt)+", device ID "+str(data[0][1].global_id()))

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterrupts[currentInterrupt] = HbusInterrupt()
            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterrupts[currentInterrupt].interruptFlags = ord(data[1][0])

            self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterrupts[currentInterrupt].interruptDescription = ''.join(data[1][2::])

            if currentInterrupt+1 < self.detectedSlaveList[data[0][1].global_id()].hbusSlaveInterruptCount:

                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[currentInterrupt+1],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1])
                                 ,timeoutCallBack=self.readSlaveObjectInformationFailed)

            else:
                #self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                self.logger.debug("device analysis "+str(data[0][1].global_id())+" finished")
                #self.processHiddenObjects(self.detectedSlaveList[data[0][1].global_id()])
                self.detectedSlaveList[data[0][1].global_id()].basicInformationRetrieved = True

                self.detectedSlaveList[data[0][1].global_id()].sortObjects()

                if self.detectedSlaveList[data[0][1].global_id()].readEndedCallback != None:
                    reactor.callLater(HBUS_SLAVE_QUERY_INTERVAL,self.detectedSlaveList[data[0][1].global_id()].readEndedCallback.callback,self.detectedSlaveList[data[0][1].global_id()].readEndedParams) #@UndefinedVariable

        elif data[0][0] == "D":

            #info dump
            pass

    def readSlaveObject(self,address,number,callBack=None,timeoutCallback=None):

        d = None

        #see if this is a virtual device first
        if address.bus_number == VIRTUAL_BUS:
            #read and update
            result = self.pluginManager.m_read_vdev_obj(address.dev_number,number)
            self.virtualDeviceList[address.global_id()].hbusSlaveObjects[number].last_value = result

            if callBack != None:
                callBack(result)
            return

        if self.detectedSlaveList[address.global_id()].hbusSlaveObjects[number].permissions != HbusObjectPermissions.WRITE:

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

        if isinstance(params[0],HbusDeviceAddress):
            address = params[0]
            number = params[1]
        elif isinstance(params[1],HbusDeviceAddress):
            address = params[1]
            number = params[2]
        else:
            raise ValueError('')

        d = None

        if self.detectedSlaveList[address.global_id()].hbusSlaveHiddenObjects[number].permissions != HbusObjectPermissions.WRITE:

            #self.expectResponse(HBUSCOMMAND_RESPONSE,address,self.receiveSlaveObjectData,actionParameters=(address,number,callBack),timeoutAction=timeoutCallback)
            #self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack))
            d = self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveHiddenObjectData,callBackParams=(address,number,None),
                                 timeoutCallBack=None)

        else:

            self.logger.warning("Write-only object read attempted")
            self.logger.debug("Tried reading object %d of slave with address %s",number,address)

            #if callBack != None:
            #
            #    callBack(None)

        return d

    def receiveSlaveObjectData(self, data):

        self.detectedSlaveList[data[0][0].global_id()].hbusSlaveObjects[data[0][1]].last_value = [ord(d) for d in data[1]]

        if data[0][2] != None:

            data[0][2](data[1])

    def receiveSlaveHiddenObjectData(self, data):

        self.detectedSlaveList[data[0][0].global_id()].hbusSlaveHiddenObjects[data[0][1]].last_value = [ord(d) for d in data[1]]

        if data[0][2] != None:

            data[0][2](data[1])

    def writeSlaveObject(self,address,number,value):

        #check if is virtual bus
        if address.bus_number == VIRTUAL_BUS:
            self.virtualDeviceList[address.global_id()].hbusSlaveObjects[number].last_value = value
            self.pluginManager.m_write_vdev_obj(address.dev_number, number, value)
            return True

        if self.detectedSlaveList[address.global_id()].hbusSlaveObjects[number].permissions != HbusObjectPermissions.READ:

            self.detectedSlaveList[address.global_id()].hbusSlaveObjects[number].last_value = value
            size = self.detectedSlaveList[address.global_id()].hbusSlaveObjects[number].size

            myParamList = [number,size]
            if isinstance(value, list):
                myParamList.extend(value)
            else:
                myParamList.append(value)

            if (self.detectedSlaveList[address.global_id()].hbusSlaveCapabilities & HbusDeviceCapabilities.AUTHSUP):

                myParamList[1] += HBUS_SIGNATURE_SIZE+1

                msg = struct.pack('ccccccc',chr(self.hbusMasterAddr.bus_number),chr(self.hbusMasterAddr.dev_number),chr(address.bus_number),
                                  chr(address.dev_number),chr(HBUSCOMMAND_SETCH.cmd_byte),chr(number),chr(myParamList[1]))

                i = 0
                while (size > 0):
                    struct.pack_into('c',msg,7+i,value[i])

                    size -= 1
                    i += 1

                sig = hbus_crypto.hbusCrypto_RabinWilliamsSign(msg, HBUS_ASYMMETRIC_KEYS.privatep, HBUS_ASYMMETRIC_KEYS.privateq)

                myParamList.extend(sig.getByteString())

            self.pushCommand(HBUSCOMMAND_SETCH,address,params=myParamList)

        else:
            return False
            self.logger.warning("attempted to write to a read-only object")

        return True

    def writeFormattedSlaveObject(self,address,number,value):

        #decode formatting and write data to object
        if address.bus_number == VIRTUAL_BUS:
            obj = self.virtualDeviceList[address.global_id()].hbusSlaveObjects[number]
        else:
            obj = self.detectedSlaveList[address.global_id()].hbusSlaveObjects[number]

        data = HBUS_DTYPE_OPTIONS[obj.objectDataType][obj.objectDataTypeInfo](data=value,extinfo=obj.objectExtendedInfo,decode=True,size=obj.size)

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

        if address.global_id() not in self.detectedSlaveList.keys():
            if address in self.staticSlaveList:
                self.logger.info("Device with static address present")
                self.registerNewSlave(address)

        if self.detectedSlaveList[address.global_id()].pingRetryCount > 0:
            self.detectedSlaveList[address.global_id()].pingRetryCount = 0
            self.detectedSlaveList[address.global_id()].pingFailures += 1

        return self.deferredDelay(0.1)

    def slavePongFailed(self,*params):

        address = params[0].value.args[0]

        if address.global_id() in self.detectedSlaveList.keys():

            if self.detectedSlaveList[address.global_id()].pingRetryCount < 3:
                self.detectedSlaveList[address.global_id()].pingRetryCount += 1
            else:
                self.logger.warning("Removing device from bus for unresponsiveness")
                self.unRegisterSlave(address)
        else:
            #this is a static device
            pass

        return self.deferredDelay(0.1)

    def detectSlaves(self, callBack=None, allBusses=False):

        self.pushCommand(HBUSCOMMAND_SEARCH, HbusDeviceAddress(self.hbusMasterAddr.bus_number,255))

        if self.masterState == hbusMasterState.hbusMasterOperational:
            self.masterState = hbusMasterState.hbusMasterChecking
        else:
            self.masterState = hbusMasterState.hbusMasterSearching
            self.logger.info("Starting device search")

        reactor.callLater(5,self.handleAlarm) #@UndefinedVariable

        self.detectSlavesEnded = callBack

    def checkSlaves(self):

        d = defer.Deferred()

        #enumerated devices
        for slave in self.detectedSlaveList.values():

            if slave.hbusSlaveAddress in self.staticSlaveList:
                continue

            d.addCallback(self.pingSlave,slave.hbusSlaveAddress)

        #static devices
        for address in self.staticSlaveList:
            d.addCallback(self.pingSlave,address)

        d.addCallback(self.getSlavesMissingInformation)

        #new devices
        d.addCallback(self.detectSlaves)

        #starts callback chain (deferred chain)
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

        for dev in self.virtualDeviceList:
            if self.virtualDeviceList[dev].hbusSlaveUniqueDeviceInfo == int(uid):
                return self.virtualDeviceList[dev].hbusSlaveAddress

        self.logger.debug("device with UID <"+str(int(uid))+"> not found")
        return None

    def responseTimeoutCallback(self,response):


        self.logger.warning('Response timed out')
        self.logger.debug("Response timed out: %s",response)

        if self.hbusBusState == HbusBusState.LOCKED_THIS:
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
        #            self.sendCommand(HBUSCOMMAND_SEARCH, HbusDeviceAddress(b,d))
        #            self.expectResponse(HBUSCOMMAND_ACK, HbusDeviceAddress(b,d))
        #
        #else:
        #
        #    for d in range(1,32):
        #
        #        self.sendCommand(HBUSCOMMAND_SEARCH,HbusDeviceAddress(self.hbusMasterAddr.bus_number,d))
        #        self.expectResponse(HBUSCOMMAND_ACK,HbusDeviceAddress(self.hbusMasterAddr.bus_number,d),action=self.registerNewSlave,actionParameters=HbusDeviceAddress(self.hbusMasterAddr.bus_number,d),timeout=10000000)
    def processStaticSlaves(self):

        for addr in self.staticSlaveList:

            if addr.global_id() in self.detectedSlaveList:
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
