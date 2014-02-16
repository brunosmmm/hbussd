#coding=utf-8

##@package hbus_serializers
#Classes e funções para pré-serialização de objetos para uso com JSON
#@author Bruno Morais <brunosmmm@gmail.com>
#@since 13/02/2014

##Pré-serializador de objetos do tipo hbusSlaveInformation
class hbusSlaveSerializer:

    ##Construtor
    #@param slave objeto do dispositivo para extração de informações
    def __init__(self,slave):
        
        ##Descrição (nome) do dispositivo
        self.description = slave.hbusSlaveDescription
        ##UID do dispositivo
        self.uid = slave.hbusSlaveUniqueDeviceInfo
        ##Número de objetos no dispositivo
        self.objectcount = slave.hbusSlaveObjectCount
        ##Número de endpoints no dispositivo
        self.endpointcount = slave.hbusSlaveEndpointCount
        ##Número de interrupções no dispositivo
        self.interruptcount = slave.hbusSlaveInterruptCount
        
        ##Endereço atual do dispositivo no barramento
        self.currentaddress = str(slave.hbusSlaveAddress)
        ##Capacidades do dispositivo
        self.capabilities = slave.hbusSlaveCapabilities
        
    ##Gera dicionário das informações do dispositivo
    #@return dicionário para posterior serialização
    def getDict(self):
        return self.__dict__

##Pré-serializador de objetos do tipo hbusObjectInformation
class hbusObjectSerializer:
    
    ##Construtor
    #@param obj objeto do objeto de dispositivo para extração de informações
    def __init__(self,obj):
        
        ##Permissões do objeto
        self.permissions = obj.objectPermissions
        ##Descrição (nome) do objeto
        self.description = obj.objectDescription
        ##Tamanho em bytes do objeto
        self.size = obj.objectSize
        ##Último valor conhecido do objeto
        self.lastvalue = obj.objectLastValue
        ##Tipo de dados do objeto
        self.datatype = obj.objectDataType
        ##Informações sobre o tipo de dados do objeto
        self.datatypeinfo = obj.objectDataTypeInfo
        ##Informações extendidas do objeto
        self.extendedinfo = obj.objectExtendedInfo
        ##Nível do objeto
        self.objectlevel = obj.objectLevel
    
    ##Gera dicionário das informações do objeto do dispositivo
    #@return dicionário para posterior serialização
    def getDict(self):
        return self.__dict__