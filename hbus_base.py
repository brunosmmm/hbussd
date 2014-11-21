#coding=utf-8

##@package hbus_base
#hbussd general purpose data structures
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2013

import struct
import hbus_constants as hbusconst
import re

##HBUS commands
class hbusCommand:
    
    ##Constructor
    #@param value command identifier byte value
    #@param minimumSize maximum command length in bytes
    #@param maximumSize minimum command length in bytes
    #@param descStr descriptive string
    def __init__(self,value,minimumSize,maximumSize, descStr):
        
        ##byte value (ID)
        self.commandByte = value
        ##minimum length
        self.minimumLength = minimumSize
        ##maximum length
        self.maximumLength = maximumSize
        ##descriptive string
        self.descString = descStr
    
    ##Command representation
    #@return streing representation of command 
    def __repr__(self):
        
        return self.descString+"("+str(hex(self.commandByte))+")"
    
    ##Equal operator
    #@return returns equal or not
    def __eq__(self, other):
        if isinstance(other, hbusCommand):
            return self.commandByte == other.commandByte
        return NotImplemented
   
    ##@todo check if this is being used
    def __hash__(self):
        
        return hash(self.commandByte)

##HBUS bus instructions
class hbusInstruction:
    
    ##Constructor
    #@param command instruction command
    #@param paramSize parameter size in bytes
    #@param params parameters to be sent
    def __init__(self, command, paramSize=0, params=()):
        
        ##Parameter list
        self.params = []
        ##Parameter list size
        self.paramSize = 0
        
        ##HBUS command
        self.command = command
        
        if command not in hbusconst.HBUS_COMMANDLIST:
            if command == None:
                raise ValueError("Undefined error")
            else:
                raise ValueError("Invalid command: %d" % ord(command.commandByte))
        
        self.paramSize = paramSize
        self.params = params
        
        if (len(params)) > command.maximumLength:
            
            raise ValueError("Malformed command, "+str(len(params))+" > "+str(command.maximumLength))
        
        if (len(params)+1) < command.minimumLength:
            
            raise ValueError("Malformed command, "+str(len(params))+" < "+str(command.minimumLength))
    
    ##Instruction representation
    #@return string representation of instruction
    def __repr__(self):
        
        if (self.paramSize > 0):
            
            try:
                return str(self.command)+str([hex(ord(x)) for x in self.params])
            except TypeError:
                return str(self.command)+str(self.params)
        else:
            return str(self.command)

##HBUS device addresses
class hbusDeviceAddress:
    
    ##Constructor
    #@param busID bus number
    #@param devID device number
    def __init__(self, busID, devID):
        
        if (devID > 32) and (devID != 255):
            raise ValueError("Invalid address")
        
        ##Bus number
        self.hbusAddressBusNumber = busID
        ##Device number in this bus
        self.hbusAddressDevNumber = devID
    
    ##Address representation
    #@return string representation of address
    def __repr__(self):
        
        return "("+str(self.hbusAddressBusNumber)+":"+str(self.hbusAddressDevNumber)+")"
    
    ##Equal operator for addresses
    #@return equal or not
    def __eq__(self, other):
        if isinstance(other, hbusDeviceAddress):
            return self.hbusAddressBusNumber == other.hbusAddressBusNumber and self.hbusAddressDevNumber == other.hbusAddressDevNumber
        return NotImplemented
    
    ##Calculates a global ID for an address
    #Global IDs are calculated by doing ID = busNumber*32 + deviceNumber
    #@return address global ID
    def getGlobalID(self):
        
        return self.hbusAddressBusNumber*32 + self.hbusAddressDevNumber

##Parse a string and create an address from it
#
#String format is (X:Y) where X is the bus number and Y the device number
#@return HBUS address object
def hbusDeviceAddressFromString(addr):
    
    p = re.compile(r'\(([0-9]+):([0-9]+)\)')
    
    m = p.match(addr)
    
    if m:
        
        try:
            
            return hbusDeviceAddress(int(m.group(1)),int(m.group(2)))
        
        except:
            raise ValueError
        
    else:
        raise ValueError

##HBUS bus operation
#
#Bus operations are composed of an instruction, and message source and destination
class hbusOperation:
    
    ##Constructor
    #@param instruction a hbusInstruction object
    #@param destination destination device address
    #@param source source device address
    def __init__(self, instruction, destination, source):
        
        ##HBUS instruction
        self.instruction = instruction
        
        ##Destination address
        self.hbusOperationDestination = destination
        ##Source address
        self.hbusOperationSource = source
    
    ##Operation representation
    #@return string representation of operation
    def __repr__(self):
        
        return "HBUSOP: "+str(self.hbusOperationSource)+"->"+str(self.hbusOperationDestination)+" "+str(self.instruction)
    
    ##Generates data string to be sent by master
    #@return data string to be sent to bus
    def getString(self):
        
        header = struct.pack('4c',chr(self.hbusOperationSource.hbusAddressBusNumber),chr(self.hbusOperationSource.hbusAddressDevNumber),
                                  chr(self.hbusOperationDestination.hbusAddressBusNumber),chr(self.hbusOperationDestination.hbusAddressDevNumber))
        
        instruction = struct.pack('c',chr(self.instruction.command.commandByte))
        
        #if self.instruction.paramSize:
            
        #    instruction = instruction + struct.pack('c',chr(self.instruction.paramSize))
        
        for p in self.instruction.params:
            
            if (type(p) is str):
                if len(p) == 1:
                    instruction = instruction + struct.pack('c',p)
                else:
                    instruction = instruction + p
            else:
                instruction = instruction + struct.pack('c',chr(p))
        
        terminator = '\xFF'
                          
        return header+instruction+terminator
    
