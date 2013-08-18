#coding=utf-8
'''
Created on 17/08/2013

@author: bruno
'''

import struct
import hbus_constants as hbusconst

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

class hbusInstruction:
    
    params = []
    paramSize = 0
    
    def __init__(self, command, paramSize=0, params=()):
        
        self.command = command
        
        if command not in hbusconst.HBUS_COMMANDLIST:
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
        
        return "("+str(self.hbusAddressBusNumber)+":"+str(self.hbusAddressDevNumber)+")"
    
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
    