#coding=utf-8

##@package hbus_base
#Estruturas base para uso geral do hbussd
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2013

import struct
import hbus_constants as hbusconst
import re

##Comandos HBUS
class hbusCommand:
    
    ##Construtor
    #@param value valor do byte idenficador de comando
    #@param minimumSize tamanho mínimo do comando em bytes
    #@param maximumSize tamanho máximo do comando em bytes
    #@param descStr string descritiva
    def __init__(self,value,minimumSize,maximumSize, descStr):
        
        ##Valor do byte (ID)
        self.commandByte = value
        ##Tamanho mínimo
        self.minimumLength = minimumSize
        ##Tamanho máximo
        self.maximumLength = maximumSize
        ##String descritiva
        self.descString = descStr
    
    ##Representação do comando
    #@return representação do comando em string 
    def __repr__(self):
        
        return self.descString+"("+str(hex(self.commandByte))+")"
    
    ##Verifica igualdade
    #@return retorna se são iguais ou não
    def __eq__(self, other):
        if isinstance(other, hbusCommand):
            return self.commandByte == other.commandByte
        return NotImplemented
    
    def __hash__(self):
        
        return hash(self.commandByte)

##Instrução de barramento HBUS
class hbusInstruction:
    
    ##Construtor
    #@param command comando da instrução
    #@param paramSize tamanho dos parâmetros em bytes
    #@param params parâmetros a serem enviados
    def __init__(self, command, paramSize=0, params=()):
        
        ##Lista de parâmetros
        self.params = []
        ##Tamanho da lista de parâmetros
        self.paramSize = 0
        
        ##Comando HBUS
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
    
    ##Representação da instrução
    #@return retorna representação da instrução em string
    def __repr__(self):
        
        if (self.paramSize > 0):
            
            try:
                return str(self.command)+str([hex(ord(x)) for x in self.params])
            except TypeError:
                return str(self.command)+str(self.params)
        else:
            return str(self.command)

##Endereço de dispositivos no barramento HBUS
class hbusDeviceAddress:
    
    ##Construtor
    #@param busID número do barramento
    #@param devID número do dispositivo no barramento
    def __init__(self, busID, devID):
        
        if (devID > 32) and (devID != 255):
            raise ValueError("Endereço inválido")
        
        ##Número do barramento
        self.hbusAddressBusNumber = busID
        ##Número do dispositivo no barramento
        self.hbusAddressDevNumber = devID
    
    ##Representação do endereço
    #@return retorna representação do endereço em string
    def __repr__(self):
        
        return "("+str(self.hbusAddressBusNumber)+":"+str(self.hbusAddressDevNumber)+")"
    
    ##Verifica se dois endereços são iguais
    #@return retorna se são iguais ou não
    def __eq__(self, other):
        if isinstance(other, hbusDeviceAddress):
            return self.hbusAddressBusNumber == other.hbusAddressBusNumber and self.hbusAddressDevNumber == other.hbusAddressDevNumber
        return NotImplemented
    
    ##Retorna um ID global para um endereço qualquer.
    #O ID global é calculado fazendo-se ID = busNumber*32 + deviceNumber
    #@return ID global do endereço
    def getGlobalID(self):
        
        return self.hbusAddressBusNumber*32 + self.hbusAddressDevNumber

##Função para criação de objeto de endereço a partir de uma string.
#
#A string deve estar no formato (X:Y) onde X é o numero do barramento e Y é o número do dispositivo no barramento
#@return objeto de endereço do tipo hbusDeviceAddress
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

##Operação de barramento HBUS.
#
#A operação é composta de uma instrução e indicadores de fonte e destino da mensagem
class hbusOperation:
    
    ##Construtor
    #@param instruction uma instrução do tipo hbusInstruction
    #@param destination endereço do dispositivo que é o destinatário
    #@param source endereço do dispositivo que é a fonte da operação
    def __init__(self, instruction, destination, source):
        
        ##Instrução HBUS
        self.instruction = instruction
        
        ##Endereço de destino
        self.hbusOperationDestination = destination
        ##Endereço de fonte
        self.hbusOperationSource = source
    
    ##Representação da operação
    #@return representação da operação em string
    def __repr__(self):
        
        return "HBUSOP: "+str(self.hbusOperationSource)+"->"+str(self.hbusOperationDestination)+" "+str(self.instruction)
    
    ##Gera a string que é correspondente a operação e que será enviada pelo mestre
    #@return string com os dados a serem enviados ao barramento
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
    