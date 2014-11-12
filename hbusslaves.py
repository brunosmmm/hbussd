#coding=utf-8
##@package hbusslaves
#Estruturas de dados e funções pertinentes ao enumeramento e interpretação de dados de dispositivos
#@author Bruno Morais <brunosmmm@gmail.com>
#@since 18/02/2014

from hbus_datahandlers import *
import struct
from array import array
from math import log

##Classe para a identificação de nível de um objeto de dispositivo
class hbusSlaveObjectLevel:
    
    ##Objeto tem nível 0
    level0  = 0x00
    ##Objeto tem nível 1
    level1  = 0x40
    ##Objeto tem nível 2
    level2  = 0x80
    ##Objeto tem nível 3
    level3  = 0xC0

##Classe para a identificação do tipo de dados de um objeto de dispositivo
class hbusSlaveObjectDataType:
    ##Objeto é do tipo Byte
    dataTypeByte        = 0x30
    ##Objeto é do tipo Inteiro
    dataTypeInt         = 0x00
    ##Objeto é do tiṕo Inteiro sem sinal
    dataTypeUnsignedInt = 0x10
    ##Objeto é do tipo Ponto Fixo
    dataTypeFixedPoint  = 0x20
    
    ##Interpreta tipo Byte como hexadecimal
    dataTypeByteHex     = 0x01
    ##Interpreta tipo Byte como decimal
    dataTypeByteDec     = 0x02
    ##Interpreta tipo Byte como octal
    dataTypeByteOct     = 0x03
    ##Interpreta tipo Byte como binário
    dataTypeByteBin     = 0x07
    ##Interpreta tipo Byte como booleano
    dataTypeByteBool    = 0x08
    
    ##Interpreta tipo Inteiro sem sinal como percentual
    dataTypeUintPercent     = 0x04
    ##Interpreta tipo Inteiro sem sinal como escala linear
    dataTypeUintLinPercent  = 0x05
    ##Interpreta tipo Inteiro sem sinal como escala logarítmica 
    dataTypeUintLogPercent  = 0x06
    ##Interpreta tipo Inteiro sem sinal como hora
    dataTypeUintTime        = 0x09
    ##Interpreta tipo Inteiro sem sinal como data
    dataTypeUintDate        = 0x0A
    
    ##Não interpreta inteiro sem sinal
    dataTypeUintNone        = 0x00
    
    ##Desempacota string de bytes recebida
    #@param data String de bytes recebida do dispositivo
    #@return valor interpretado como Inteiro sem sinal
    def unpackUINT(self,data):

        x = [0]
        while (len(data) < 4):
            x.extend(data)
            data = x
            x = [0]
        
        byteList = array('B',data)
        
        return struct.unpack('>I',byteList)[0]
    
    ##Interpreta dados como sendo booleano
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size parâmetro para compatibilidade
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatBoolBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            if data == "ON":
                return [1];
            
            return [0];
        
        if (data[0] > 0):
            return 'ON'
        else:
            return 'OFF'
    
    ##Interpreta dados como sendo hexadecimal
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size tamanho dos dados em bytes
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatHexBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%X' % x for x in data])
   
    ##Interpreta dados como sendo decimal
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size tamanho dos dados em bytes
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatDecBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%d' % x for x in data])
   
    ##Interpreta dados como sendo octal
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size tamanho dos dados em bytes
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatOctBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['%o' % x for x in data])
    
    ##Interpreta dados como sendo binário
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size tamanho dos dados em bytes
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatBinBytes(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return ', '.join(['0b{0:b}'.format(x) for x in data])
    
    ##Interpreta dados como sendo Inteiro sem sinal comum. Permite o uso de unidades
    #@param data dados recebidos
    #@param extInfo lista de propriedades extendidas do objeto de dispositivo relativo ao dado processado
    #@param size tamanho dos dados em bytes
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatUint(self,data,extInfo,size,decode=False):
        
        if decode:
            return [ord(x) for x in struct.pack('>I',data)[size:]]
        
        value = str(self.unpackUINT(data))
        
        try:
            unit = extInfo['UNIT']
            value = str(value)+" "+HBUS_UNITS[chr(unit[0])]
        except:
            pass
        
        return value

    ##Interpreta dados como sendo percentual (0-100)
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size parâmetro para compatibilidade
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatPercent(self,data,extInfo,size,decode=False):
        
        if len(data) > 0:
            try:
                data = int(data[::-1])
            except:
                data = 0
            
        if data > 100:
            data = 100
            
        if decode:
            return [ord(x) for x in struct.pack('>I',data)[size:]]
            
        return "%d%%" % data

    ##Interpreta dados como sendo escala linear
    #@param data dados recebidos
    #@param extInfo lista de propriedades extendidas do objeto de dispositivo relativo ao dado processado
    #@param size parâmetro para compatibilidade
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
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

    ##Interpreta dados como sendo escala logarítmica
    #@param data dados recebidos
    #@param extInfo lista de propriedades extendidas do objeto de dispositivo relativo ao dado processado
    #@param size parâmetro para compatibilidade
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
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
    
    ##Interpreta dados como sendo tempo (hora)
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size parâmetro para compatibilidade
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
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
    
    ##Interpreta dados como sendo data
    #@param data dados recebidos
    #@param extInfo parâmetro para compatibilidade
    #@param size parâmetro para compatibilidade
    #@param decode informa a direção da operação: decodificação ou codificação
    #@return string formatada para visualização ou dados
    def formatDate(self,data,extInfo,size,decode=False):
        
        if decode:
            return [0*x for x in range(0,size)]
        
        return "?"
    
    ##Dicionário associando tipos de dados possíveis para os objetos de dispositivos e suas strings para exibição
    dataTypeNames = {dataTypeByte : 'Byte', dataTypeInt : 'Int', dataTypeUnsignedInt : 'Unsigned Int', dataTypeFixedPoint : 'Ponto fixo'}
    ##Dicionário de tipos extendidos de dados possiveis e métodos de decodificação
    dataTypeOptions = {dataTypeByte : {dataTypeByteHex : formatHexBytes  ,dataTypeByteDec : formatDecBytes  ,dataTypeByteOct : formatOctBytes ,dataTypeByteBin : formatBinBytes,
                                       dataTypeByteBool : formatBoolBytes},
                       dataTypeUnsignedInt : {dataTypeUintNone : formatUint, dataTypeUintPercent : formatPercent, dataTypeUintLinPercent : formatRelLinPercent, dataTypeUintLogPercent : formatRelLogPercent, 
                                              dataTypeUintTime : formatTime, dataTypeUintDate : formatDate},
                       dataTypeFixedPoint : hbusFixedPointHandler(),
                       dataTypeInt : hbusIntHandler()}

##Informações extendidas para um objeto de dispositivo
class hbusSlaveObjectExtendedInfo:
    
    ##Valor máximo
    objectMaximumValue = None
    ##Valor mínimo
    objectMinimumValue = None
    
    ##String extendida do objeto
    objectExtendedString = None

##Classe principal do objeto de dispositivo
class hbusSlaveObjectInfo:
    
    ##Permissões do objeto
    objectPermissions = 0
    ##Indica se é criptografado
    objectCrypto = False
    ##Indica se é invisível
    #@todo isto não faz sentido uma vez que os objetos invisíveis e visíveis já são segregados em diferentes listas
    objectHidden = False
    ##String de descrição do objeto
    objectDescription = None
    ##Tamanho do objeto em bytes
    objectSize = 0
    ##Último valor conhecido do objeto
    objectLastValue = None
    
    ##Tipo de dados do objeto
    objectDataType = 0
    ##Informação extendida sobre o tipo de dados
    objectDataTypeInfo = None
    ##Nível do objeto
    objectLevel = 0
    ##Informação extendida sobre o objeto
    objectExtendedInfo = None
    
    ##Formata valor do objeto para exibição
    #@return valor formatado para exibição
    def getFormattedValue(self):
        
        if self.objectLastValue == None:
            return None
        
        if self.objectDataType not in hbusSlaveObjectDataType.dataTypeOptions.keys():
            
            return str(self.objectLastValue) #sem formato
        
        #analisa informação extra
        if type(hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType]) == dict: 
        
            if self.objectDataTypeInfo not in hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType].keys():
            
                return str(self.objectLastValue) #sem formato
                
        return hbusSlaveObjectDataType.dataTypeOptions[self.objectDataType][self.objectDataTypeInfo](hbusSlaveObjectDataType(),data=self.objectLastValue,size=self.objectSize,extInfo=self.objectExtendedInfo)
        
    ##Representação do objeto
    #@return string descritiva do objeto para log, etc
    def __repr__(self):
        
        return self.objectDescription

##Classe principal do endpoint de dispositivo
class hbusSlaveEndpointInfo:
    
    ##Direção do endpoint: escrita ou leitura ou ambos
    endpointDirection = 0
    ##String descritiva do endpoint
    endpointDescription = None
    ##Tamanho do bloco de dados em bytes
    endpointBlockSize = 0
    
    ##Representação
    #@return string descritiva do endpoint para log, etc
    def __repr__(self):
        
        return self.endpointDescription

##Classe principal das interrupções de dispositivo
class hbusSlaveInterruptInfo:
    
    ##Flags de interrupção
    interruptFlags = 0
    ##String descritiva da interrupção
    interruptDescription = None
    
    ##Representação
    #@return string descritiva da interrupção para log, etc
    def __repr__(self):
        
        return self.interruptDescription

##Classe principal para armazenamento de informações sobre um dispositivo
class hbusSlaveInfo:
    
    ##Endereço do dispositivo no barramento
    hbusSlaveAddress = None
    
    ##String descritiva do dispositivo
    hbusSlaveDescription = None
    ##UID do dispositivo
    hbusSlaveUniqueDeviceInfo = None
    ##Número de objetos no dispositivo
    #@todo verificar se esse número inclui objetos invisíveis ou não
    hbusSlaveObjectCount = 0
    ##Número de endpoints no dispositivo
    hbusSlaveEndpointCount = 0
    ##Número de interrupções no dispositivo
    hbusSlaveInterruptCount = 0
    ##Capabilidades do dispositivo
    hbusSlaveCapabilities = 0
    
    ##Indica se as informações básicas deste dispositivo já foram recebidas
    basicInformationRetrieved = False
    ##Indica se as informações extendidas deste dispositivo já foram recebidas
    extendedInformationRetrieved = False
    
    ##Dicionário de objetos do dispositivo
    hbusSlaveObjects = {}
    ##Dicionário de Endpoints do dispositivo
    hbusSlaveEndpoints = {}
    ##Dicionário de Interrupções do dispositivo
    hbusSlaveInterrupts = {}
    ##Dicionário de objetos invisíveis do dispositivo
    hbusSlaveHiddenObjects = {}
    
    ##@todo verificar a funcionalidade, não estou lembrando
    waitFlag = False
    
    #Flags de falhas
    ##Número de tentativas de leitura inicial realizadas sem sucesso
    scanRetryCount = 0
    ##Número de tentativas consecutivas de ping sem sucesso
    pingRetryCount = 0
    ##Número total de falhas de ping sem sucesso (resultado na remoção temporária do dispositivo do barramento)
    pingFailures = 0
    
    ##Representação para serialização
    #@return dicionário de strings dos objetos internos da classe
    def __repr__(self):
        return str(self.__dict__)
    
    ##Construtor
    #@param explicitSlaveAddress endereço que o dispositivo assumirá no barramento
    def __init__(self,explicitSlaveAddress):
        self.hbusSlaveAddress = explicitSlaveAddress
    
    ##Separa objetos visíveis e invisíveis
    #
    #Os objetos visíveis e invisíveis são todos colocados no dicionário hbusSlaveObjects no ato da leitura inicial. Após a leitura inicial, a função é chamada
    #e separa os objetos em dois dicionários diferentes
    def sortObjects(self):
        
        self.hbusSlaveHiddenObjects = {}
        
        for key,val in self.hbusSlaveObjects.viewitems():
            
            if val.objectHidden == False:
                continue
            
            self.hbusSlaveHiddenObjects[key] = val
            
        for key in self.hbusSlaveHiddenObjects.keys():
            
            if key in self.hbusSlaveObjects:
                self.hbusSlaveObjects.pop(key)
                