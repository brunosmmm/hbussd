##@package hbus_serializers
#Classes e funções para pré-serialização de objetos para uso com JSON
#@author Bruno Morais
#@contact brunosmmm@gmail.com
#@since 13/02/2014

##Pré-serializador de objetos do tipo hbusSlaveInformation
class hbusSlaveSerializer:

    ##Construtor
    #@param slave objeto do dispositivo para extração de informações
    def __init__(self,slave):
        
        self.description = slave.hbusSlaveDescription
        self.uid = slave.hbusSlaveUniqueDeviceInfo
        self.objectcount = slave.hbusSlaveObjectCount
        self.endpointcount = slave.hbusSlaveEndpointCount
        self.interruptcount = slave.hbusSlaveInterruptCount
        
        self.currentaddress = str(slave.hbusSlaveAddress)
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
        
        self.permissions = obj.objectPermissions
        self.description = obj.objectDescription
        self.size = obj.objectSize
        
        self.lastvalue = obj.objectLastValue
        
        self.datatype = obj.objectDataType
        self.datatypeinfo = obj.objectDataTypeInfo
        
        self.extendedinfo = obj.objectExtendedInfo
    
    ##Gera dicionário das informações do objeto do dispositivo
    #@return dicionário para posterior serialização
    def getDict(self):
        return self.__dict__