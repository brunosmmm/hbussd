#coding=utf-8

from hbusmaster import *
import string
from bottle import route, run, template, static_file, request

class HBUSWEB:

    wait = False

    def __init__(self,port,hbusMaster):
        
        self.port = port
        self.hbusMaster = hbusMaster
        self.objectLevel = 0

    def index(self):
        
        return template('hbus_index',slaves=self.hbusMaster.detectedSlaveList.values(),masterStatus=self.hbusMaster.getInformationData())
    
    def favicon(self):
        
        return static_file('favicon.ico',root='web_static') 
        
    def slaveInfo(self,addr=None,uid=None,obj=None):
        
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
                    
                    while (self.wait == True):
                        pass
                except:
                    pass
                
            if s == None:
                
                ##TODO: retornar template de erro, escravo indisponível
                
                pass
                
            writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x02])
            readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x01])
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        readObjCount=readObjectCount,writeObjCount=writeObjectCount)
    
    def slaveWriteObject(self,uid=None,obj=None):
        

        if uid != None:
            
            devUID = string.split(uid,"0x")
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
            
            if addr == None:
                s = None
            else:
                s = self.hbusMaster.detectedSlaveList[addr.getGlobalID()]
                
            if s == None:
                
                ##TODO: retornar template de erro, escravo indisponível
                
                pass
        
        return template('hbus_slave_object_set',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType,objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        objectNumber = int(obj))
    
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
        
            writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x02])
            readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.objectPermissions & 0x01])
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        readObjCount=readObjectCount,writeObjCount=writeObjectCount)
    
    def slavesByBus(self,busNumber=None):
        
        if int(busNumber) == 255:
            slaveList = self.hbusMaster.detectedSlaveList.values()
        else:
            slaveList = []
            for slave in self.hbusMaster.detectedSlaveList.values():
                if slave.hbusSlaveAddress.hbusAddressBusNumber == int(busNumber):
                    slaveList.append(slave)
        
        return template('hbus_slave_by_bus',slaveList=slaveList,masterStatus=self.hbusMaster.getInformationData(),busNumber=busNumber)
    
    def setLevel(self,level=None):
        
        if level == None:
            return
        
        try:
            self.objectLevel = int(level)
        finally:
            return
    
    def staticFiles(self,filename):
        
        return static_file(filename,root='web_static')
    
    #roda
    def run(self):
        
        #cria rotas
        route("/")(self.index)
        route("/index.html")(self.index)
        
        route("/slave-addr/<addr>")(self.slaveInfo)
        route("/slave-uid/<uid>")(self.slaveInfo)
        route("/slave-uid/<uid>/get-<obj>")(self.slaveInfo)
        route("/slave-uid/<uid>/set-<obj>")(self.slaveWriteObject)
        route("/slave-uid/<uid>/set-<obj>",method="POST")(self.slaveInfoSet)
        
        #escravos por barramento
        route("/bus/<busNumber>")(self.slavesByBus)
        
        route ("/static/<filename>")(self.staticFiles)
        route ("/favicon.ico")(self.favicon)
        
        #opções escondidas
        route ("/set-level/<level>")(self.setLevel)
        
        run(host='192.168.1.122',port=self.port)

#test_server = HBUSWEB(8000,None)
#test_server.run()

