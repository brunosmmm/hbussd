#coding=utf-8

##@package hbusjsonserver
#Módulo para gerenciamento de entrada e saída de informações através de requisições HTTP usando JSON
#@author Bruno Morais <brunosmmm@gmail.com>
#@since 13/02/2014

from txjsonrpc.web import jsonrpc
import simplejson
from hbus_serializers import *
from hbus_base import hbusDeviceAddressFromString

##Servidor HTTP de JSON para conexão com hbuswte
class HBUSJSONServer(jsonrpc.JSONRPC):

    ##Construtor
    #@param master referencia ao objeto principal do mestre hbus para manipulação de dados
    #@todo realizar separação entre corpo principal do mestre hbus e modulos exteriores
    def __init__(self,master):
        
        ##Referência ao objeto principal do mestre
        self.master = master
    
    ##Retorna lista de barramentos atualmente ativos
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_activebusses(self):
        return self.master.getInformationData().activeBusses
    
    ##Retorna o número de dispositivos atualmente ativos
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_activeslavecount(self):
        
        return self.master.getInformationData().activeSlaveCount
    

    ##Retorna lista de uids contendo todos os dispositivos ativos no momento
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_activeslavelist(self):

        #slaveList = [hbusSlaveSerializer(x).getDict() for x in self.master.detectedSlaveList.values()]
        slaveList = [x.hbusSlaveUniqueDeviceInfo for x in self.master.detectedSlaveList.values()]
        
        return slaveList
    

    ##Retorna informações detalhadas de um dispositivo
    #@param uid UID do dispositivo
    #@return informações a serem esrtuturadas em JSON   
    def jsonrpc_slaveinformation(self,uid):

        address = self.master.findDeviceByUID(uid)
        
        if address == None:
            return None
        
        slave = self.master.detectedSlaveList[address.getGlobalID()]
        
        return hbusSlaveSerializer(slave).getDict()
    
    ##Retorna lista de objetos de um dispositivo
    #@param slaveuid UID do dispositivo
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_slaveobjectlist(self,slaveuid):
        
        address = self.master.findDeviceByUID(slaveuid)
        
        if address == None:
            return None
        
        slave = self.master.detectedSlaveList[address.getGlobalID()]
        
        objectList = [hbusObjectSerializer(x).getDict() for x in slave.hbusSlaveObjects.values()]
        
        return objectList
    
    ##Retorna lista de UIDs de dispositivos ativos em um barramento
    #@param bus número do barramento
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_activeslavesbybus(self,bus):
        
        if int(bus) == 255:
            slaveList = self.hbusMaster.detectedSlaveList.values()
        else:
            slaveList = []
            for slave in self.hbusMaster.detectedSlaveList.values():
                if slave.hbusSlaveAddress.hbusAddressBusNumber == int(bus):
                    slaveList.append(slave)
                    
        returnList = [x.hbusSlaveUniqueDeviceInfo for x in slaveList]
        
        return returnList
    
    ##Executa leitura do valor de um objeto
    #@param address endereço do dispositivo
    #@param number número do objeto
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_readobject(self,address,number):

        addr = hbusDeviceAddressFromString(address)
        
        if not addr.getGlobalID() in self.master.detectedSlaveList.keys():
            
            #escravo não existe
            return
        
        if not int(number) in self.master.detectedSlaveList[addr.getGlobalID()].hbusSlaveObjects.keys():
            
            #objeto não existe
            return
        
        #deferred?
        
        ##@todo verificar como fazer o retorno dos dados -- utilizar deferreds
        
    ##Executa escrita do valor de um objeto
    #@param address endereço do dispositivo
    #@param number número do objeto
    #@param value novo valor a ser escrito no objeto
    #@return informações a serem esrtuturadas em JSON
    def jsonrpc_writeobject(self,address,number,value):
        
        addr = hbusDeviceAddressFromString(address)
        
        if not addr.getGlobalID() in self.master.detectedSlaveList.keys():
            
            #escravo não existe
            return
        
        if not int(number) in self.master.detectedSlaveList[addr.getGlobalID()].hbusSlaveObjects.keys():
            
            #objeto não existe
            return
        
        #interpretar valor
        self.master.writeSlaveObject(addr,int(number),int(value))
        
        return 'OK'