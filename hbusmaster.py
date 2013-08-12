# coding=utf-8

import struct
from datetime import datetime
import logging
#import signal
from collections import deque
#import threading
import re
import hbus_crypto

from twisted.internet import reactor, defer
from array import array
from math import log


from bitstring import BitArray 

def getMillis(td):
    
    return (td.days * 24 * 60 * 60 + td.seconds) * 1000 + td.microseconds / 1000.0

def nonBlockingDelay(td):
    
    now = datetime.now()
    
    while getMillis(datetime.now() - now) < td:
        pass
    
class hbusCommand:
    
    def __init__(self,value,minimumSize,maximumSize, descStr):
        
        self.commandByte = value
        self.minimumLength = minimumSize
        self.maximumLength = maximumSize
        self.descString = descStr
        
    def __repr__(self):
        
        return self.descString+"("+str(hex(self.commandByte))+")"
    
    def __eq__(self, other):
        if isinstance(other, hbusCommand):
            return self.commandByte == other.commandByte
        return NotImplemented
    
    def __hash__(self):
        
        return hash(self.commandByte)

HBUS_PUBKEY_SIZE = 192
HBUS_SIGNATURE_SIZE = 192 #assinatura é 192, mas é acompanhada de mais um byte que é e/f/r (193 bytes)

HBUSCOMMAND_SETCH = hbusCommand(0x01,3,32,"SETCH")
HBUSCOMMAND_GETCH = hbusCommand(0x04,1,1,"GETCH")
HBUSCOMMAND_SEARCH = hbusCommand(0x03,0,0,"SEARCH")
HBUSCOMMAND_ACK = hbusCommand(0x06,0,0,"ACK")
HBUSCOMMAND_QUERY = hbusCommand(0x07,1,1,"QUERY")
HBUSCOMMAND_QUERY_RESP = hbusCommand(0x08,3,32,"QUERY_RESP")
HBUSCOMMAND_RESPONSE = hbusCommand(0x10,1,32,"RESP")
HBUSCOMMAND_ERROR = hbusCommand(0x20,2,2,"ERROR")
HBUSCOMMAND_BUSLOCK = hbusCommand(0xF0,0,0,"BUSLOCK")
HBUSCOMMAND_BUSUNLOCK = hbusCommand(0xF1,0,0,"BUSUNLOCK")
HBUSCOMMAND_SOFTRESET = hbusCommand(0xF2,0,HBUS_SIGNATURE_SIZE+2,"SOFTRESET") #tamanho máximo é HBUS_SIGNATURE_SIZE + 2 -> (PSZ;e/f/r;assinatura)
HBUSCOMMAND_QUERY_EP = hbusCommand(0x11,1,1,"QUERY_EP")
HBUSCOMMAND_QUERY_INT = hbusCommand(0x12,1,1,"QUERY_INT")
HBUSCOMMAND_STREAMW = hbusCommand(0x40,2,2,"STREAMW")
HBUSCOMMAND_STREAMR = hbusCommand(0x41,2,2,"STREAMR")
HBUSCOMMAND_INT = hbusCommand(0x80,1,1,"INT")
HBUSCOMMAND_KEYSET = hbusCommand(0xA0,HBUS_PUBKEY_SIZE+1,HBUS_PUBKEY_SIZE+1,"KEYSET")
HBUSCOMMAND_KEYRESET = hbusCommand(0xA1,1,1,"KEYRESET")

HBUS_RESPONSEPAIRS = {HBUSCOMMAND_GETCH : HBUSCOMMAND_RESPONSE, HBUSCOMMAND_QUERY : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_QUERY_EP : HBUSCOMMAND_QUERY_RESP, 
                      HBUSCOMMAND_QUERY_INT : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_SEARCH : HBUSCOMMAND_ACK}

HBUS_COMMANDLIST = (HBUSCOMMAND_SETCH,HBUSCOMMAND_SEARCH,HBUSCOMMAND_GETCH,HBUSCOMMAND_ACK,HBUSCOMMAND_QUERY,HBUSCOMMAND_QUERY_RESP,HBUSCOMMAND_RESPONSE,
                    HBUSCOMMAND_ERROR,HBUSCOMMAND_BUSLOCK,HBUSCOMMAND_BUSUNLOCK,HBUSCOMMAND_SOFTRESET, HBUSCOMMAND_QUERY_EP, HBUSCOMMAND_QUERY_INT, HBUSCOMMAND_STREAMW, 
                    HBUSCOMMAND_STREAMR, HBUSCOMMAND_INT, HBUSCOMMAND_KEYSET, HBUSCOMMAND_KEYRESET)
HBUS_COMMANDBYTELIST = (x.commandByte for x in HBUS_COMMANDLIST)

HBUS_BROADCAST_ADDRESS = 255

HBUS_UNITS = {'A' : 'A', 'V' : 'V', 'P' : 'Pa', 'C':'C', 'd' : 'dBm', 'D' : 'dB'}



class hbusInstruction:
    
    params = []
    paramSize = 0
    
    def __init__(self, command, paramSize=0, params=()):
        
        self.command = command
        
        if command not in HBUS_COMMANDLIST:
            if command == None:
                raise ValueError("Erro desconhecido")
            else:
                raise ValueError("Comando inválido: %d" % ord(command.commandByte))
        
        self.paramSize = paramSize
        self.params = params
        
        if (len(params)) > command.maximumLength:
            
            raise ValueError("Comando mal-formado, "+str(len(params))+" > "+str(command.maximumLength))
        
        if (len(params)+1) < command.minimumLength:
            
            raise ValueError("Comando mal-formado, "+str(len(params))+" < "+str(command.minimumLength))
        
    def __repr__(self):
        
        if (self.paramSize > 0):
            
            try:
                return str(self.command)+str([hex(ord(x)) for x in self.params])
            except TypeError:
                return str(self.command)+str(self.params)
        else:
            return str(self.command)

class hbusDeviceAddress:
    
    def __init__(self, busID, devID):
        
        if (devID > 32) and (devID != 255):
            raise ValueError("Endereço inválido")
        
        self.hbusAddressBusNumber = busID
        self.hbusAddressDevNumber = devID
        
    def __repr__(self):
        
        return "(BUS ID = "+str(self.hbusAddressBusNumber)+", DEV ID = "+str(self.hbusAddressDevNumber)+")"
    
    def __eq__(self, other):
        if isinstance(other, hbusDeviceAddress):
            return self.hbusAddressBusNumber == other.hbusAddressBusNumber and self.hbusAddressDevNumber == other.hbusAddressDevNumber
        return NotImplemented
    
    def getGlobalID(self):
        
        return self.hbusAddressBusNumber*32 + self.hbusAddressDevNumber

class hbusOperation:
    
    def __init__(self, instruction, destination, source):
        
        self.instruction = instruction
        
        self.hbusOperationDestination = destination
        self.hbusOperationSource = source
        
    def __repr__(self):
        
        return "HBUSOP: "+str(self.hbusOperationSource)+"->"+str(self.hbusOperationDestination)+" "+str(self.instruction)
        
    def getString(self):
        
        header = struct.pack('4c',chr(self.hbusOperationSource.hbusAddressBusNumber),chr(self.hbusOperationSource.hbusAddressDevNumber),
                                  chr(self.hbusOperationDestination.hbusAddressBusNumber),chr(self.hbusOperationDestination.hbusAddressDevNumber))
        
        instruction = struct.pack('c',chr(self.instruction.command.commandByte))
        
        #if self.instruction.paramSize:
            
        #    instruction = instruction + struct.pack('c',chr(self.instruction.paramSize))
            
        for p in self.instruction.params:
            
            if (type(p) is str):
                instruction = instruction + struct.pack('c',p)
            else:
                instruction = instruction + struct.pack('c',chr(p))
        
        terminator = '\xFF'
                          
        return header+instruction+terminator

class hbusKeySet:
    
    privateq = None
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

class hbusSlaveCapabilities:
    
    hbusSlaveAuthSupport = 8
    hbusSlaveEndpointSupport = 2
    hbusSlaveUCODESupport = 16
    hbusSlaveIntSupport = 4
    hbusSlaveCryptoSupport = 1
    hbusSlaveRevAuthSupport = 0x20

class hbusBusStatus:
    
    hbusBusFree = 0
    hbusBusLockedThis = 1
    hbusBusLockedOther = 2
    
class hbusMasterRxState:
    
    hbusRXSBID = 0
    hbusRXSDID = 1
    hbusRXTBID = 2
    hbusRXTDID = 3
    hbusRXCMD  = 4
    hbusRXADDR = 5
    hbusRXPSZ  = 6
    hbusRXPRM  = 7
    hbusRXSTP  = 8
    
class hbusSlaveObjectPermissions:
    
    hbusSlaveObjectRead = 1
    hbusSlaveObjectWrite = 2
    hbusSlaveObjectReadWrite = 3

class hbusFixedPointHandler:
    
    pointLocation = None

    def formatFixedPoint(self,dummy,data,extInfo,size,decode=False):
        
        x = [0]
        while (len(data) < 4):
            x.extend(data)
            data = x
            x = [0]
        
        byteList = array('B',data)
        
        value = float(struct.unpack('>i',byteList)[0])/(10**float(self.pointLocation))
        
        try:
            unit = extInfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass
        
        return  value
    
    def __getitem__(self,key):
        
        #ultra gambiarra
        self.pointLocation = int(key)
        
        return self.formatFixedPoint
    
class hbusIntHandler:
    
    def formatInt(self,dummy,data,extInfo,size,decode=False):
        
        #x = [0]
        #while (len(data) < 4):
        #    x.extend(data)
        #    data = x
        #    x = [0]
        
        #byteList = array('B',data)
        
        #value = struct.unpack('>i',byteList)[0]
        
        value = BitArray(bytes=''.join([chr(x) for x in data])).int
        
        try:
            unit = extInfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass
        
        return value
    
    def __getitem__(self,key):
        
        return self.formatInt

class hbusSlaveObjectDataType:
    
    dataTypeByte = 0x80
    dataTypeInt = 0x10
    dataTypeUnsignedInt = 0x20
    dataTypeFixedPoint = 0x40
    
    dataTypeByteHex = 0x01
    dataTypeByteDec = 0x02
    dataTypeByteOct = 0x03
    dataTypeByteBin = 0x07
    dataTypeByteBool = 0x08
    
    dataTypeUintPercent     = 0x04
    dataTypeUintLinPercent  = 0x05
    dataTypeUintLogPercent  = 0x06
    dataTypeUintTime        = 0x09
    dataTypeUintDate        = 0x0A
    
    dataTypeUintNone        = 0x00
    
    
    def unpackUINT(self,data):

        x = [0]
        while (len(data) < 4):
            x.extend(data)
            data = x
            x = [0]
        
        byteList = array('B',data)
        
        return struct.unpack('>I',byteList)[0]
    
    def formatBoolBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            if data == "ON":
                return [1];
            
            return [0];
        
        if (data[0] > 0):
            return 'ON'
        else:
            return 'OFF'
    
    def formatHexBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%X' % x for x in data])
   
    def formatDecBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%d' % x for x in data])
   
    def formatOctBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%o' % x for x in data])
    
    def formatBinBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['0b{0:b}'.format(x) for x in data])

    def formatUint(self,data,extInfo,size,decode=False):
        
        if decode:
            return [ord(x) for x in struct.pack('>I',data)[size:]]
        
        return self.unpackUINT(data)

    def formatPercent(self,data,extInfo,size,decode=False):
        
        if len(data) > 0:
            
            data = int(data[::-1])
            
        if data > 100:
            data = 100
            
        if decode:
            return [ord(x) for x in struct.pack('>I',data)[size:]]
            
        return "%d%%" % data

    def formatRelLinPercent(self,data,extInfo,size,decode=False):
        
        try:
            minimumValue = self.unpackUINT(extInfo['MIN'])
        except:
            minimumValue = 0
        
        if decode:
            
            try:
                maximumValue = self.unpackUINT(extInfo['MAX'])
            except:
                maximumValue = 2**(8*size) - 1
                
            
            value = int((float(data)/100.0)*(maximumValue-minimumValue) + minimumValue)
            
            return [ord(x) for x in struct.pack('>I',value)[size:]]
        
        if data == None:
            return "?"
        
        try:
            maximumValue = self.unpackUINT(extInfo['MAX'])
        except:
            maximumValue = 2**(8*len(data)) - 1
        
        value = self.unpackUINT(data)
        
        return "%.2f%%" % ((float(value-minimumValue)/float(maximumValue-minimumValue))*100)

    def formatRelLogPercent(self,data,extInfo,size,decode=False):
        
        try:
            minimumValue = self.unpackUINT(extInfo['MIN'])
        except:
            minimumValue = 0
        
        if decode:
            
            try:
                maximumValue = self.unpackUINT(extInfo['MAX'])
            except:
                maximumValue = 2**(8*size) - 1
                
            
            value = int(10**((float(data)/100.0)*log(maximumValue-minimumValue)) + minimumValue)
            
            return [ord(x) for x in struct.pack('>I',value)[size:]]
        
        if data == None:
            return "?"
        
        try:
            maximumValue = self.unpackUINT(extInfo['MAX'])
        except:
            maximumValue = 2**(8*len(data)) - 1
            
        
        value = self.unpackUINT(data)
        
        try:
            percent = (log(float(value-minimumValue))/log(float(maximumValue-minimumValue)))*100
        except:
            percent = 0
            
        
        return "%.2f%%" % percent
    
    def formatTime(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        tenthSeconds = (data[3] & 0xF0)>>4
        milliSeconds = data[3] & 0x0F
        
        segundos = data[2] & 0x0F
        dezenaSegundos = data[2] & 0xF0
        
        minutes = data[1] & 0x0F
        dezena = (data[1] & 0xF0) >> 4
        
        horas24 = data[0] & 0x0F
        
        return "%2d:%2d:%2d,%2d" % (horas24,minutes+dezena*10,segundos+dezenaSegundos*10,milliSeconds+tenthSeconds*10)
    

    def formatDate(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return "?"
    
    dataTypeNames = {dataTypeByte : 'Byte', dataTypeInt : 'Int', dataTypeUnsignedInt : 'Unsigned Int', dataTypeFixedPoint : 'Ponto fixo'}
    dataTypeOptions = {dataTypeByte : {dataTypeByteHex : formatHexBytes  ,dataTypeByteDec : formatDecBytes  ,dataTypeByteOct : formatOctBytes ,dataTypeByteBin : formatBinBytes,
                                       dataTypeByteBool : formatBoolBytes},
                       dataTypeUnsignedInt : {dataTypeUintNone : formatUint, dataTypeUintPercent : formatPercent, dataTypeUintLinPercent : formatRelLinPercent, dataTypeUintLogPercent : formatRelLogPercent, 
                                              dataTypeUintTime : formatTime, dataTypeUintDate : formatDate},
                       dataTypeFixedPoint : hbusFixedPointHandler(),
                       dataTypeInt : hbusIntHandler()}

class hbusSlaveObjectExtendedInfo:
    
    objectMaximumValue = None
    objectMinimumValue = None
    
    objectExtendedString = None

class hbusSlaveObjectInfo:
    
    objectPermissions = 0
    objectCrypto = False
    objectHidden = False
    objectDescription = None
    objectSize = 0
    objectLastValue = None
    
    objectDataType = 0
    objectDataTypeInfo = None
    
    objectExtendedInfo = None
    
    def getFormattedValue(self):
        
        if self.objectLastValue == None:
            return None
        
        if self.objectDataType == 0 or self.objectDataType not in hbusSlaveObjectDataType.dataTypeOptions.keys():
            
            #print self.objectDataType
            #print hbusSlaveObjectDataType.dataTypeOptions.keys()
            
            return self.objectLastValue #sem formato
        
        #analisa informação extra
        if type(hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType]) == dict: 
        
            if self.objectDataTypeInfo not in hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType].keys():
            
            #print self.objectDataTypeInfo
            #print hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType].keys()
            
                return self.objectLastValue #sem formato
                
        return hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType][self.objectDataTypeInfo](hbusSlaveObjectDataType(),data=self.objectLastValue,size=self.objectSize,extInfo=self.objectExtendedInfo)
        
    
    def __repr__(self):
        
        return self.objectDescription
    
class hbusSlaveEndpointInfo:
    
    endpointDirection = 0
    endpointDescription = None
    endpointBlockSize = 0
    
    def __repr__(self):
        
        return self.endpointDescription
    
class hbusSlaveInterruptInfo:
    
    interruptFlags = 0
    interruptDescription = None
    
    def __repr__(self):
        
        return self.interruptDescription
    
class hbusSlaveInfo:
    
    hbusSlaveAddress = None
    
    hbusSlaveDescription = None
    hbusSlaveUniqueDeviceInfo = None
    hbusSlaveObjectCount = 0
    hbusSlaveEndpointCount = 0
    hbusSlaveInterruptCount = 0
    hbusSlaveCapabilities = 0
    
    basicInformationRetrieved = False
    extendedInformationRetrieved = False
    
    hbusSlaveObjects = {}
    hbusSlaveEndpoints = {}
    hbusSlaveInterrupts = {}
    
    hbusSlaveHiddenObjects = {}
    
    waitFlag = False
    
    def __init__(self,explicitSlaveAddress):
        self.hbusSlaveAddress = explicitSlaveAddress

class hbusMasterState:
    
    hbusMasterStarting = 0
    hbusMasterIdle = 1
    hbusMasterSearching = 2
    hbusMasterAddressing = 3
    hbusMasterScanning = 4
    hbusMasterOperational = 5
    
class hbusPendingAnswer:
    
    def __init__(self,command,source,timeout,action=None,actionParameters=None,timeoutAction=None):
        
        self.command = command
        self.source = source
        self.timeout = timeout
        self.now = datetime.now()
        
        self.dCallback = defer.Deferred()
        
        if action != None:
            self.dCallback.addCallback(action)
        
        #self.action= action
        self.actionParameters = actionParameters
        
        self.tCallback = defer.Deferred()
        if timeoutAction != None:
            self.tCallback.addCallback(timeoutAction)
        
        #self.timeoutAction = timeoutAction
        
    def addTimeoutHandler(self,timeoutHandler):
        
        self.timeoutHandler = timeoutHandler

class hbusMaster:
    
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
    
    staticSlaveList = [hbusDeviceAddress(0, 31),hbusDeviceAddress(1,30)]
    
    registeredSlaveCount = 0
    
    masterState = hbusMasterState.hbusMasterStarting
    
    commandDelay = datetime.now()
    
    hbusDeviceSearchTimer = datetime.now()
    
    hbusDeviceSearchInterval = 60000
    
    autoSearch = True
    
    nextSlaveCapabilities = None
    nextSlaveUID = None
    
    hbusDeviceScanningTimeout = False
    
    def __init__(self, port, baudrate=100000, busno = 0):
        
        self.serialPort = port
        self.serialBaud = baudrate
        self.hbusMasterAddr = hbusDeviceAddress(busno, 0)
        
        self.logger = logging.getLogger('hbus_skeleton.hbusmaster')
        
        #signal.signal(signal.SIGALRM, self.handleAlarm)
        
        #self.hbusSerial = hbusSerialConnection(port,baudrate,self.hbusSerialRxTimeout)
    
        self.serialCreate()
        
    def processHiddenObjects(self):
        
        self.waitFlag = False
        def waitForResult(dummy):
            
            self.waitFlag = False
        
        for slave in self.detectedSlaveList.values():
        
            i = 1
            for obj in slave.hbusSlaveObjects.values():
                
                if obj.objectHidden == False:
                    i += 1
                    continue
                
                self.waitFlag = True
                self.readSlaveObject(slave.hbusSlaveAddress, i, callBack=waitForResult)
                
                while (self.waitFlag):
                    pass
                
                objFunction = obj.objectDescription.split(':')
                
                objList = objFunction[0].split(',')
                
                for objSel in objList:
                    
                    x = re.match(r"([0-9]+)-([0-9]+)",objSel)
                    
                    if x != None:
                        
                        for rangeObj in range(int(x.group(1)),int(x.group(2))+1):
                            
                            if slave.hbusSlaveObjects[int(rangeObj)].objectExtendedInfo == None:
                                slave.hbusSlaveObjects[int(rangeObj)].objectExtendedInfo = {}
                
                                slave.hbusSlaveObjects[int(rangeObj)].objectExtendedInfo[objFunction[1]] = obj.objectLastValue
                            
                    else:
                        if slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo == None:
                            slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo = {}
                
                            slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo[objFunction[1]] = obj.objectLastValue
                
                i += 1
            
    
    def serialCreate(self):
        
        pass #overload!!
    
    def serialConnected(self):
        
        #reseta todos dispositivos
        
        address = hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,HBUS_BROADCAST_ADDRESS)
        
        size = HBUS_SIGNATURE_SIZE+1
        
        myParamList = [chr(size)]
        
        msg = struct.pack('cccccc',chr(self.hbusMasterAddr.hbusAddressBusNumber),chr(self.hbusMasterAddr.hbusAddressDevNumber),chr(address.hbusAddressBusNumber),
                                chr(address.hbusAddressDevNumber),chr(HBUSCOMMAND_SOFTRESET.commandByte),myParamList[0])
                    
        sig = hbus_crypto.hbusCrypto_RabinWilliamsSign(msg, HBUS_ASYMMETRIC_KEYS.privatep, HBUS_ASYMMETRIC_KEYS.privateq,HBUS_SIGNATURE_SIZE)
        
        myParamList.extend(sig.getByteString())
        
        self.pushCommand(HBUSCOMMAND_SOFTRESET,address,params=myParamList)
        
        self.logger.debug("Aguardando RESET dos escravos...")
        
        #signal.alarm(1)
        reactor.callLater(1,self.handleAlarm)
        
        #self.detectSlaves()
        self.serialRXMachineEnterIdle()
        
    def serialWrite(self, string):
        
        pass #fazer overload
    
    def serialRead(self,size):
        
        pass #overload
    
    def serialRXMachineTimeout(self):
        
        self.logger.warning("Timeout na formação de pacote")
        self.logger.debug("dump pacote: %s", self.communicationBuffer)
        
        #self.communicationBuffer = []
        #self.hbusRxState = hbusMasterRxState.hbusRXSBID
        self.serialRXMachineEnterIdle()
        
    def serialRXMachineEnterIdle(self):
        
        self.communicationBuffer = []
        
        self.hbusRxState = hbusMasterRxState.hbusRXSBID
        
        if len(self.outgoingCommands) > 0:
            d = self.outgoingCommands.pop()
            d.callback(None)
        
    
    def serialNewData(self,data):
        
        #lasthbusState = self.hbusRxState
        
        #self.logger.debug("DADOS %s",[d for d in data])
        
        #if self.hbusSerialRxTimeout < getMillis(self.RxTimer - datetime.now()):
        #    self.hbusBusState = hbusMasterRxState.hbusRXSBID
        #    self.communicationBuffer = []
        #    
        #    self.logger.warning("HBUSOP Timeout")
        #    self.logger.debug("COM BUF = "+self.communicationBuffer)
        
        for d in data:
            
            if self.hbusRxState == hbusMasterRxState.hbusRXSBID:
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXSDID
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXSDID:
                
                self.RXTimeout.cancel()
                
                #endereço inválido
                if (ord(d) > 32) and (ord(d) != 255):
                    self.serialRXMachineEnterIdle()
                    
                    self.logger.debug("Pacote com endereço inválido recebido")
                    return
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXTBID
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXTBID:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXTDID
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXTDID:
                
                self.RXTimeout.cancel()
                
                #endereço inválido
                if (ord(d) > 32) and (ord(d) != 255):
                    self.serialRXMachineEnterIdle()
                    
                    self.logger.debug("Pacote com endereço inválido recebido")
                    return
                
                self.communicationBuffer.append(d)
                
                self.hbusRxState = hbusMasterRxState.hbusRXCMD
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXCMD:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
            
                if ord(d) == HBUSCOMMAND_ACK.commandByte or ord(d) == HBUSCOMMAND_SEARCH.commandByte or ord(d) == HBUSCOMMAND_BUSLOCK.commandByte or ord(d) == HBUSCOMMAND_BUSUNLOCK.commandByte or ord(d) == HBUSCOMMAND_SOFTRESET.commandByte:
                    self.hbusRxState = hbusMasterRxState.hbusRXSTP
                else:
                    self.hbusRxState = hbusMasterRxState.hbusRXADDR
                
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                    
            elif self.hbusRxState == hbusMasterRxState.hbusRXADDR:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
                
                if ord(self.communicationBuffer[4]) == HBUSCOMMAND_GETCH.commandByte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY.commandByte or\
                ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY_EP.commandByte or ord(self.communicationBuffer[4]) == HBUSCOMMAND_QUERY_INT.commandByte:
                    self.hbusRxState = hbusMasterRxState.hbusRXSTP
                else:
                    self.hbusRxState = hbusMasterRxState.hbusRXPSZ
                    
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                
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
                        self.hbusRxState = hbusMasterRxState.hbusRXSTP #faltava
                        
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
                
            elif self.hbusRxState == hbusMasterRxState.hbusRXPRM:
                
                self.RXTimeout.cancel()
                
                if len(self.communicationBuffer) <= (6 + self.lastPacketParamSize):
                    self.communicationBuffer.append(d)
                else:
                    
                #self.hbusRxState = hbusMasterRxState.hbusRXSTP
                    if ord(d) == 0xFF:
                        self.communicationBuffer.append(d)
                        
                        self.logger.debug("pacote recebido, processando...")
                        self.logger.debug("dump pacote: %s" % [hex(ord(x)) for x in self.communicationBuffer])
                        
                        #t = threading.Thread(target=self.parseReceivedData(self.communicationBuffer))
                        #t.start()
                        #reactor.callInThread(self.parseReceivedData,self.communicationBuffer)
                        dataToParse = self.communicationBuffer
                        
                        self.serialRXMachineEnterIdle()
                        
                        self.parseReceivedData(dataToParse)
                        
                        return
                        
                    else:
                        self.logger.debug("pacote mal-formado, erro no fechamento")
                        self.logger.debug("dump pacote: %s" % [hex(ord(x)) for x in self.communicationBuffer])
                        
                        self.serialRXMachineEnterIdle()
                        
                        return
                        #print self.communicationBuffer
                self.RXTimeout = reactor.callLater(0.2,self.serialRXMachineTimeout)
            
            elif self.hbusRxState == hbusMasterRxState.hbusRXSTP:
                
                self.RXTimeout.cancel()
                
                self.communicationBuffer.append(d)
                
                self.logger.debug("pacote recebido, processando...")
                self.logger.debug("dump pacote: %s" % [hex(ord(x)) for x in self.communicationBuffer])
                
                if ord(d) == 0xFF:
                    #t = threading.Thread(target=self.parseReceivedData(self.communicationBuffer))
                    #t.start()
                    #reactor.callInThread(self.parseReceivedData,self.communicationBuffer)
                    
                    dataToParse = self.communicationBuffer
                    
                    self.serialRXMachineEnterIdle()
                    
                    self.parseReceivedData(dataToParse)
                    
                    return
                
                else:
                    self.logger.debug("pacote mal-formado, erro no fechamento")
                    self.logger.debug("dump pacote: %s" % [hex(ord(x)) for x in self.communicationBuffer])
                                        
                    self.serialRXMachineEnterIdle()
                    return
                
            else:
                self.logger.error("HBUSOP erro fatal na recepção")
                raise IOError("erro fatal na recepção")
            
                self.serialRXMachineEnterIdle()
                
                return
    
    def getCommand(self,cmdbyte):
        
        for c in HBUS_COMMANDLIST:
            
            if c.commandByte == cmdbyte:
                return c
            
        return None
    
    def setNextSlaveCapabilities(self,params):
        
        self.nextSlaveCapabilities = ord(params[3])
        self.nextSlaveUID = params[4:7]
        
        if (self.nextSlaveCapabilities & hbusSlaveCapabilities.hbusSlaveAuthSupport):
            self.logger.debug("Novo escravo tem suporte AUTH")
        
        myParamList = [chr(HBUS_PUBKEY_SIZE)]
        myParamList.extend(HBUS_ASYMMETRIC_KEYS.pubKeyStr())
        
        #registra escravo no proximo endereço disponível
        if (self.nextSlaveCapabilities & hbusSlaveCapabilities.hbusSlaveAuthSupport):
            self.pushCommand(HBUSCOMMAND_KEYSET, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, self.registeredSlaveCount+1),myParamList)
        else:
            self.pushCommand(HBUSCOMMAND_SEARCH, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, self.registeredSlaveCount+1))
            
        #modifica estado interno do BUSLOCK
        self.hbusBusLockedWith = hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, self.registeredSlaveCount+1)
        
        #envia BUSUNLOCK imediatamente
        self.pushCommand(HBUSCOMMAND_BUSUNLOCK, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,self.registeredSlaveCount+1))
        
        self.registerNewSlave(hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,self.registeredSlaveCount+1))
        
        self.registeredSlaveCount = self.registeredSlaveCount + 1
        
        self.masterState = hbusMasterState.hbusMasterSearching
        
    def parseReceivedData(self,data):
        
        if len(data) < 7:
            pSize = 0
            params = ()
        else:
            pSize = ord(data[6])
            params = data[7:7+ord(data[6])]
            
        try:
            busOp = hbusOperation(hbusInstruction(self.getCommand(ord(data[4])), pSize, params), hbusDeviceAddress(ord(data[2]), ord(data[3])), hbusDeviceAddress(ord(data[0]),ord(data[1])))
        except:
            
            self.logger.warning("Pacote inválido recebido")
            return
        
        if busOp.hbusOperationSource.hbusAddressDevNumber == 0:
            self.logger.debug("Descartando pacote ilegal: endereço reservado utilizado")
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
                if busOp.hbusOperationSource.hbusAddressDevNumber == HBUS_BROADCAST_ADDRESS and self.masterState == hbusMasterState.hbusMasterSearching:
                    
                    #self.expectResponse(HBUSCOMMAND_RESPONSE, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber, HBUS_BROADCAST_ADDRESS),action=self.setNextSlaveCapabilities)
                    self.pushCommand(HBUSCOMMAND_GETCH, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,HBUS_BROADCAST_ADDRESS),params=[chr(0)],callBack=self.setNextSlaveCapabilities)
                    
                    self.masterState = hbusMasterState.hbusMasterAddressing
                
                
            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:
                self.hbusBusState = hbusBusStatus.hbusBusFree
                self.hbusBusLockedWith = None
                
                self.onBusFree()
            
            if len(self.expectedResponseQueue) > 0:
                
                #removeQueue = []
                
                selectedR = None
                for r in self.expectedResponseQueue:
                    
                    if r in self.removeQueue:
                        continue
                
                #r = self.expectedResponseQueue[0]
                    if r.source == busOp.hbusOperationSource and r.command == busOp.instruction.command:
                        #if r.timeout > getMillis((datetime.now() - r.now)):
                            #ok
                            #if r.action != None:
                            #    if r.actionParameters != None:
                            #        r.action((r.actionParameters,busOp.instruction.params)) #callback
                            #        
                            #        #self.logger.debug("HBUSOP RESPONSE OK")
                            #        self.removeQueue.append(r)
                            #        
                            #        r.timeoutHandler.cancel()
                            #        
                            #        break
                            #        
                            #    else:
                            #        r.action(busOp.instruction.params) #callback
                            #        self.removeQueue.append(r)
                            #        
                            #        r.timeoutHandler.cancel()
                            #        break
                            #        
                            #        #self.logger.debug("HBUSOP RESPONSE OK")
                        selectedR = r
                        r.timeoutHandler.cancel()
                        self.removeQueue.append(r)
                        break
                            
                            
                        #else:
                            #timeout
                            
                        #    self.logger.warning("HBUSOP RESPONSE Timeout")
                        #    if self.masterState == hbusMasterState.hbusMasterScanning:
                        #        self.hbusDeviceScanningTimeout = True
                            
                        #self.expectedResponseQueue.popleft()
                        #self.removeQueue.append(r)
                    
                    #elif r.timeout < getMillis((datetime.now() - r.now)):
                    #    
                    #    self.logger.warning("HBUSOP RESPONSE Timeout")
                    #    if self.masterState == hbusMasterState.hbusMasterScanning:
                    #        self.hbusDeviceScanningTimeout = True
                    #    
                    #    #self.expectedResponseQueue.popleft()
                    #    self.removeQueue.append(r)
                    #       
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
                
    def pushCommand(self,command,dest,params=(),callBack=None,callBackParams=None,timeout=3000,timeoutCallBack=None,immediate=False):
        
        if self.hbusRxState != hbusMasterRxState.hbusRXSBID and immediate == False:
            d = defer.Deferred()
            d.addCallback(self.pushCommand,command,dest,params,callBack,callBackParams,timeout,timeoutCallBack)
            self.outgoingCommands.appendleft(d)
        else:
            if callBack != None:
                
                try:
                    self.expectResponse(HBUS_RESPONSEPAIRS[command],dest,action=callBack,actionParameters=callBackParams,timeout=timeout,timeoutAction=timeoutCallBack)
                except:
                    pass
            
            elif timeoutCallBack != None:
                
                try:
                    self.expectResponse(HBUS_RESPONSEPAIRS[command], dest, None, None, timeout, timeoutCallBack)
                except:
                    pass
                
            self.sendCommand(command,dest,params)

    def sendCommand(self,command, dest, params=(),block=False):
        
        #blocante!!
        if block:
            while self.hbusRxState != 0:
                pass
        
        #self.commandDelay = datetime.now()
        
        #while getMillis(datetime.now() - self.commandDelay) < 60:
        #    pass
        
        busOp = hbusOperation(hbusInstruction(command, len(params), params),dest,self.hbusMasterAddr)
        
        self.logger.debug(busOp)
        
        #s = busOp.getString()
        #for c in s:
        #    
        #    print hex(ord(c))
        
        self.logger.debug('dump saida: %s' % [hex(ord(x)) for x in list(busOp.getString())])
        
        if command == HBUSCOMMAND_BUSLOCK:
            
            self.hbusBusState = hbusBusStatus.hbusBusLockedThis
            self.hbusBusLockedWith = dest
            
        elif command == HBUSCOMMAND_BUSUNLOCK:
            
            if self.hbusBusState == hbusBusStatus.hbusBusLockedThis and self.hbusBusLockedWith == dest:
                
                self.hbusBusState = hbusBusStatus.hbusBusFree
                self.hbusBusLockedWith = None
                self.onBusFree()
                
            else:
                
                self.logger.debug("erro de BUSUNLOCK: travado com %s, tentativa de destravamento com %s" % (self.hbusBusLockedWith,dest))
        if self.masterState == hbusMasterState.hbusMasterScanning:
            reactor.callFromThread(self.serialWrite,busOp.getString())
        else:
            self.serialWrite(busOp.getString())
        
    def expectResponse(self, command, source, action=None, actionParameters=None, timeout=3000, timeoutAction=None):
        
        pending = hbusPendingAnswer(command,source,timeout,action,actionParameters,timeoutAction)
        
        #timeout handler
        timeoutHandler = reactor.callLater(timeout/1000,self.responseTimeoutCallback,pending)
        pending.addTimeoutHandler(timeoutHandler)
        
        self.expectedResponseQueue.append(pending)
        
        self.logger.debug("Registrando resposta esperada")
        
    def registerNewSlave(self, address):
        
        self.detectedSlaveList[address.getGlobalID()] = hbusSlaveInfo(address)
        
        self.logger.info("Novo escravo registrado em "+str(address))
        self.logger.debug("Novo escravo tem ID interno "+str(address.getGlobalID()))
        
        #self.readBasicSlaveInformation(address)
        
    def unRegisterSlave(self, address):
        
        del self.detectedSlaveList[address.getGlobalID()]
        
        self.logger.info("Escravo em "+str(address)+" removido")
        
    def readBasicSlaveInformation(self, address):
        
        self.logger.debug("Iniciando análise do escravo "+str(address.getGlobalID()))
        
        #executa BUSLOCK
        #self.sendCommand(HBUSCOMMAND_BUSLOCK,address)
        
        #self.expectResponse(HBUSCOMMAND_QUERY_RESP,address,self.receiveSlaveInformation,actionParameters=("Q",address))
        self.pushCommand(HBUSCOMMAND_QUERY, address,params=[0],callBack=self.receiveSlaveInformation,callBackParams=("Q",address))
    
    def receiveSlaveInformation(self, data):
        
        if data[0][0] == "Q":
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveDescription = ''.join(data[1][4::]) #descrição do escravo
            
            
            #lê informação sobre objetos do escravo
            #self.expectResponse(HBUSCOMMAND_RESPONSE,data[0][1],self.receiveSlaveInformation,actionParameters=("V",data[0][1]))
            self.pushCommand(HBUSCOMMAND_GETCH,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("V",data[0][1]))
            
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
            
            self.logger.info("Escravo em "+str(data[0][1])+" identificado como "+str(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveDescription)+"("+str(ord(data[1][0]))+","+str(ord(data[1][1]))+","+str(ord(data[1][2]))+") <"+str(
                hex(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveUniqueDeviceInfo))+">")
            
            self.logger.debug("Recuperando informações dos objetos do escravo "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects = {}
            
            #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
            self.pushCommand(HBUSCOMMAND_QUERY,data[0][1],params=[1],callBack=self.receiveSlaveInformation,callBackParams=("O",data[0][1]))
            
        elif data[0][0] == "O":
            
            currentObject = len(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects)+1
            
            self.logger.debug("Analisando objeto "+str(currentObject)+", escravo ID "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject] = hbusSlaveObjectInfo()
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectPermissions = ord(data[1][0]) & 0x03
            
            if ord(data[1][0]) & 0x04:
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectCrypto = True
                
            if ord(data[1][0]) & 0x08:
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectHidden = True
                
            if (ord(data[1][0]) & 0xF0) == 0: 
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDataType = hbusSlaveObjectDataType.dataTypeByte
            else:
                self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDataType = ord(data[1][0]) & 0xF0
                            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectSize = ord(data[1][1])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDataTypeInfo = ord(data[1][2])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject].objectDescription = ''.join(data[1][4::])
            
            #print currentObject
            #print str(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjects[currentObject])
            
            if currentObject+1 < self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveObjectCount:
                
                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY,data[0][1],params=[currentObject+1],callBack=self.receiveSlaveInformation,callBackParams=("O",data[0][1]))
            else:
                
                #RECEBE ENDPOINT INFO
                if self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpointCount > 0:
                    
                    self.logger.debug("Recuperando informações dos endpoints do escravo "+str(data[0][1].getGlobalID()))
                    
                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_EP,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("E",data[0][1]))
                    
                elif self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount > 0:
                    
                    self.logger.debug("Recuperando informações das interrupções do escravo "+str(data[0][1].getGlobalID()))
                    
                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1]))
                
                else:
                    #self.pushCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug("análise escravo "+str(data[0][1].getGlobalID())+" completa")
                    #self.processHiddenObjects(self.detectedSlaveList[data[0][1].getGlobalID()])
                    self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
        
        elif data[0][0] == "E":
            
            #ENDPOINTS
            
            currentEndpoint = len(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints)+1
            
            self.logger.debug("Analisando endpoint "+str(currentEndpoint)+", escravo ID "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint] = hbusSlaveEndpointInfo()
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint].endpointDirection = ord(data[1][0])
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint].endpointBlockSize = ord(data[1][1])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpoints[currentEndpoint].endpointDescription = ''.join(data[1][3::])
            
            if currentEndpoint+1 < self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveEndpointCount:
                
                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY_EP,data[0][1],params=[currentEndpoint+1],callBack=self.receiveSlaveInformation,callBackParams=("E",data[0][1]))
                
            else:
                
                #INTERRUPT INFO
                if self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount > 0:
                    
                    self.logger.debug("Recuperando informações das interrupções do escravo "+str(data[0][1].getGlobalID()))
                    
                    #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[0],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1]))
                
                else:
                    #self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug("análise escravo "+str(data[0][1].getGlobalID())+" completa")
                    #self.processHiddenObjects(self.detectedSlaveList[data[0][1].getGlobalID()])
                    self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
                    
        elif data[0][0] == "I":
            
            #INTERRUPTS
            
            currentInterrupt = len(self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts)+1
            
            self.logger.debug("Analisando interrupção "+str(currentInterrupt)+", escravo ID "+str(data[0][1].getGlobalID()))
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts[currentInterrupt] = hbusSlaveInterruptInfo()
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts[currentInterrupt].interruptFlags = ord(data[1][0])
            
            self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterrupts[currentInterrupt].interruptDescription = ''.join(data[1][2::])
            
            if currentInterrupt+1 < self.detectedSlaveList[data[0][1].getGlobalID()].hbusSlaveInterruptCount:
                
                #self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                self.pushCommand(HBUSCOMMAND_QUERY_INT,data[0][1],params=[currentInterrupt+1],callBack=self.receiveSlaveInformation,callBackParams=("I",data[0][1]))
                
            else:
                #self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                self.logger.debug("análise escravo "+str(data[0][1].getGlobalID())+" completa")
                #self.processHiddenObjects(self.detectedSlaveList[data[0][1].getGlobalID()])
                self.detectedSlaveList[data[0][1].getGlobalID()].basicInformationRetrieved = True
    
    def readSlaveObject(self,address,number,callBack=None,timeoutCallback=None):
        
        if self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectPermissions != hbusSlaveObjectPermissions.hbusSlaveObjectWrite:
        
            #self.expectResponse(HBUSCOMMAND_RESPONSE,address,self.receiveSlaveObjectData,actionParameters=(address,number,callBack),timeoutAction=timeoutCallback)
            #self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack))
            self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack),
                             timeoutCallBack=timeoutCallback)
            
        else:
            
            self.logger.warning("Tentativa de leitura de objeto somente para escrita")
            self.logger.debug("Tentativa de leitura do objeto %d, escravo com endereço %s",number,address)
            
            if callBack != None:
                
                callBack(None)
            
    def receiveSlaveObjectData(self, data):
        
        self.detectedSlaveList[data[0][0].getGlobalID()].hbusSlaveObjects[data[0][1]].objectLastValue = [ord(d) for d in data[1]]
        
        #print data[1]
        
        if data[0][2] != None:
            
            data[0][2](data[1])
            
    def writeSlaveObject(self,address,number,value):
        
        if self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectPermissions != hbusSlaveObjectPermissions.hbusSlaveObjectRead:
            
            self.detectedSlaveList[address.getGlobalID()].hbusSlaveObjects[number].objectValue = value
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
    
        
    def detectSlaves(self, callBack = None, allBusses = False):
        
        if len(self.detectedSlaveList) > 0:
            
            #verifica presença de escravos já detectados anteriormente
            
            for s in self.detectedSlaveList.values():
                
                #self.expectResponse(HBUSCOMMAND_ACK, s.hbusSlaveAddress, None, None, 3000, self.unRegisterSlave)
                self.pushCommand(HBUSCOMMAND_SEARCH, s.hbusSlaveAddress,None,None,3000,self.unRegisterSlave)
            
        
        self.pushCommand(HBUSCOMMAND_SEARCH, hbusDeviceAddress(self.hbusMasterAddr.hbusAddressBusNumber,255))
        
        self.masterState = hbusMasterState.hbusMasterSearching
        
        self.logger.info("Iniciando busca por escravos")
        
        #signal.alarm(10)
        
        reactor.callLater(10,self.handleAlarm)
        
        self.detectSlavesEnded = callBack
             
        
    def handleAlarm(self):
        
        if self.masterState == hbusMasterState.hbusMasterSearching:
            
            self.masterState = hbusMasterState.hbusMasterIdle
            
            self.logger.info("Fim da busca por escravos, "+str(self.registeredSlaveCount)+" encontrado(s)")
            
            if self.detectSlavesEnded != None:
                
                self.detectSlavesEnded()
            
            self.logger.debug("Recuperando informações dos escravos...")
            
            #tarefa de leitura dos escravos em threading separada para poder aguardar recepção individual de dados sem congelar as outras rotinas
            
            def startReadingSlaves():
            
                for slave in self.detectedSlaveList:
                
                #aguarda barramento livre
                    while (self.hbusBusState != hbusBusStatus.hbusBusFree):
                        pass
                
                    if self.detectedSlaveList[slave].basicInformationRetrieved == False:
                        self.hbusDeviceScanningTimeout = False #reinicia flags
                        self.readBasicSlaveInformation(self.detectedSlaveList[slave].hbusSlaveAddress)
                        timeoutcounter = datetime.now()
                        retry = 0
                    
                    #se a recepção falhar, causa travamento da thread
                    while (self.detectedSlaveList[slave].basicInformationRetrieved == False):
                        #pass
                        if (getMillis(datetime.now() - timeoutcounter) > 30000) or (self.hbusDeviceScanningTimeout == True):
                            if retry < 5:
                                retry += 1
                                
                                #espera alguns segundos
                                delay = datetime.now()
                                
                                while (getMillis(datetime.now() - delay)) < 2000:
                                    pass
                                
                                self.hbusDeviceScanningTimeout = False
                                self.readBasicSlaveInformation(self.detectedSlaveList[slave].hbusSlaveAddress)
                                self.logger.debug("Falha na leitura. Realizando Nova tentativa")
                                timeoutcounter = datetime.now()
                            else:
                                self.logger.warning("Erro na obtenção de informações do escravo")
                                break
                
                self.masterState = hbusMasterState.hbusMasterOperational
                reactor.callInThread(self.processHiddenObjects)
                self.logger.info("Fim da leitura de informações dos escravos")

            self.processStaticSlaves()
            
            self.logger.debug("Nova thread iniciada, 'startReadingSlaves'")
            self.masterState = hbusMasterState.hbusMasterScanning
            reactor.callInThread(startReadingSlaves)
            
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
        
        self.expectedResponseQueue.remove(response)
        
        #if response.timeoutAction != None:
        #    response.timeoutAction(response.source)
        response.tCallback.callback(response.source)
    
    def periodicCall(self):
        
        #expectedResponseQueue cleanup
        
        #remove elementos desnecessários
        for r in self.removeQueue:
            
            if r in self.expectedResponseQueue:
                
                self.expectedResponseQueue.remove(r)
                
                self.logger.debug("Limpeza da fila de respostas...")
                
        del self.removeQueue[:]
        
        #procura por novos dispositivos
        
        if self.autoSearch:
            
            if getMillis(self.hbusDeviceSearchTimer - datetime.now()) > self.hbusDeviceSearchInterval:
                
                self.detectSlaves()
                
                self.hbusDeviceSearchTimer = datetime.now()
        
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
            
            self.logger.info("Escravo com endereço estático em %s",str(addr))
            
            self.registerNewSlave(addr)
            
            pass
        
    def onBusLocked(self):
        
        pass
        
    def onBusFree(self):
        
        while len(self.awaitingFreeBus):
            
            d = self.awaitingFreeBus.pop()
            d.callback();
        