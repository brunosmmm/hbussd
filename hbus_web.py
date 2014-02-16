#coding=utf-8

##@package hbus_web
#Servidor integrado web para controle e visualização dos dados de dispositivos
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2013-2014

from hbusmaster import *
import string
from bottle import route, run, template, static_file, request
import re

##Servidor web integrado HBUS para controle e visualização dos dados de dispositivos
class HBUSWEB:

    ##Indica o modo de espera do servidor (operações assíncronas)
    wait = False

    ##Construtor
    #@param port número da porta HTTP
    #@param hbusMaster referência ao objeto principal do mestre para extração de informações
    #@todo realizar separação e abstração entre objeto principal do mestre e outros
    def __init__(self,port,hbusMaster):
        
        ##Porta do servidor
        self.port = port
        ##Referência ao objeto principal do mestre
        self.hbusMaster = hbusMaster
        #Nível dos objetos mostrados na interface
        self.objectLevel = 0

    ##Gera a página principal do servidor web
    #@return template HTML
    def index(self):
        
        return template('hbus_index',slaves=self.hbusMaster.detectedSlaveList.values(),masterStatus=self.hbusMaster.getInformationData(),re=re)
    
    ##Usado para fornecer ícone de favorito ao browser
    #@return ícone de favorito
    def favicon(self):
        
        return static_file('favicon.ico',root='web_static') 
    
    ##Realiza a leitura de um objeto de dispositivo e mostra ao usuário.
    #
    #Retorna um valor formatado do objeto para utilização com AJAX.
    #@param uid UID do dispositivo
    #@param obj número do objeto
    #@return dados requisitados
    def readSlaveObject(self,uid=None,obj=None):
        
        self.wait = False
        def waitForSlaveRead(dummy):
            
            self.wait = False
        
        devUID = string.split(uid,"0x")
            
        addr = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
        
        if addr == None:
            s = None
        else:
            s = self.hbusMaster.detectedSlaveList[addr.getGlobalID()]
        
        if obj != None:
            
            try:
                self.wait = True
                self.hbusMaster.readSlaveObject(addr, int(obj), callBack=waitForSlaveRead,timeoutCallback=waitForSlaveRead)
                
                while (self.wait == True):
                    pass
            except:
                pass
            
        if s != None:
            data = s.hbusSlaveObjects[int(obj)].getFormattedValue()
        else:
            data = "?"
            
        if data == None:
            data = "?"
            
        return (data)
    
    ##Gera uma página de informações sobre o dispositivo para mostrar ao usuário
    #@param addr endereço do dispositivo
    #@param uid UID do dispositivo
    #@param obj número do objeto
    #@return template HTML
    def slaveInfo(self,addr=None,uid=None,obj=None):
        
        getN = 0
        
        self.wait = False
        def waitForSlaveRead(dummy):
            
            self.wait = False
        
        if addr != None:
            
            devAddr = string.split(addr,":")
            device = hbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
            
            s = self.hbusMaster.detectedSlaveList[device.getGlobalID()]
        elif uid != None:
            
            devUID = string.split(uid,"0x")
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
            
            if addr == None:
                s = None
            else:
                s = self.hbusMaster.detectedSlaveList[addr.getGlobalID()]
            
            if obj != None:
                
                try:
                    self.wait = True
                    self.hbusMaster.readSlaveObject(addr, int(obj), callBack=waitForSlaveRead,timeoutCallback=waitForSlaveRead)
                    
                    getN = int(obj)
                    
                    while (self.wait == True):
                        pass
                except:
                    pass
                
            if s == None:
                
                ##@todo retornar template de erro, escravo indisponível
                
                pass
                
            writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x02 and x.objectLevel >= self.objectLevel and x.objectHidden == False])
            readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x01 and x.objectLevel >= self.objectLevel and x.objectHidden == False])
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        readObjCount=readObjectCount,writeObjCount=writeObjectCount,re=re,getNumber=getN)
        
    def busList(self):
        
        from bottle import response
        from json import dumps
        
        rv = []
        for bus in self.hbusMaster.getInformationData().activeBusses:
        
            rv.append([{"busNumber": bus}])
        
        response.content_type = 'application/json'
        return dumps(rv)
    
    ##Escreve valor no objeto de dispositivo
    #@param uid UID do dispositivo
    #@param obj número do objeto
    #@return template HTML com valores atualizados
    def slaveWriteObject(self,uid=None,obj=None):
        

        if uid != None:
            
            devUID = string.split(uid,"0x")
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
            
            if addr == None:
                s = None
            else:
                s = self.hbusMaster.detectedSlaveList[addr.getGlobalID()]
                
            if s == None:
                
                ##@todo retornar template de erro, escravo indisponível
                
                pass
        
        return template('hbus_slave_object_set',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType,objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        objectNumber = int(obj),re=re,percentToRange=self.percentToRange)
    
    def slaveInfoSet(self,uid=None,obj=None):
        
        newObjValue = request.forms.get('value')
        
        if uid != None:
            
            devUID = string.split(uid,"0x")
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
            
            if addr == None:
                s = None
            else:
                s = self.hbusMaster.detectedSlaveList[addr.getGlobalID()]
            
            if obj != None:
                
                #try:
                self.hbusMaster.writeFormattedSlaveObject(addr,int(obj),newObjValue)

                #except:
                #    pass
        
            #writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x02 and x.objectLevel > self.objectLevel])
            #readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x01 and x.objectLevel > self.objectLevel])
        
        return template('hbus_slave_object_set',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        objectNumber = int(obj),re=re,percentToRange=self.percentToRange)
                        #readObjCount=readObjectCount,writeObjCount=writeObjectCount)
    
    ##Gera uma página listando os dispositivos em um barramento
    #@param busNumber número do barramento
    #@return template HTML
    def slavesByBus(self,busNumber=None):
        
        if int(busNumber) == 255:
            slaveList = self.hbusMaster.detectedSlaveList.values()
        else:
            slaveList = []
            for slave in self.hbusMaster.detectedSlaveList.values():
                if slave.hbusSlaveAddress.hbusAddressBusNumber == int(busNumber):
                    slaveList.append(slave)
        
        return template('hbus_slave_by_bus',slaveList=slaveList,masterStatus=self.hbusMaster.getInformationData(),busNumber=busNumber,re=re)
    
    ##Define o nível mínimo dos objetos mostrados na interface
    #@param level nível mínimo dos objetos
    def setLevel(self,level=None):
        
        if level == None:
            return
        
        try:
            self.objectLevel = int(level)
        finally:
            return
    
    ##Obtém arquivos estáticos
    #@param filename nome do arquivo a ser obtido
    #@return arquivo
    def staticFiles(self,filename):
        
        return static_file(filename,root='web_static')
    
    ##Converte percentuais para valores escalonados
    #@param percentStr valor percentual em string
    #@return valor
    def percentToRange(self,percentStr):
        
        if percentStr == "?" or percentStr == None:
            return "0"
        
        s = re.sub(r'\.[0-9]+%$','',percentStr)
        
        return s
    
    ##Loop principal de execução do servidor web pyBottle
    def run(self):
        
        #cria rotas
        route("/")(self.index)
        route("/index.html")(self.index)
        
        route("/slave-addr/<addr>")(self.slaveInfo)
        route("/slave-uid/<uid>")(self.slaveInfo)
        route("/slave-uid/<uid>/get-<obj>")(self.slaveInfo)
        route("/slave-uid/<uid>/set-<obj>")(self.slaveWriteObject)
        route("/slave-uid/<uid>/set-<obj>",method="POST")(self.slaveInfoSet)
        #route("/slave-uid/<uid>/setget-<obj>")(self.slaveWriteObjectRefresh)
        route("/slave-uid/<uid>/objdata-<obj>")(self.readSlaveObject)
        route("/busses")(self.busList)
        
        #escravos por barramento
        route("/bus/<busNumber>")(self.slavesByBus)
        
        route ("/static/<filename>")(self.staticFiles)
        route ("/favicon.ico")(self.favicon)
        
        #opções escondidas
        route ("/set-level/<level>")(self.setLevel)
        
        run(host='192.168.1.122',port=self.port)

#test_server = HBUSWEB(8000,None)
#test_server.run()

