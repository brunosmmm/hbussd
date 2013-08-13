#coding=utf-8

from hbusmaster import *
import string
from bottle import route, run, template, static_file, request

class HBUSWEB:

    wait = False

    def __init__(self,port,hbusMaster):
        
        self.port = port
        self.hbusMaster = hbusMaster

    def index(self):
        
        return template('hbus_index',slaves=self.hbusMaster.detectedSlaveList.values())
    
    def favicon(self):
        
        return static_file('favicon.ico',root='web_static') 
        
    def slaveInfo(self,addr=None,uid=None,obj=None):
        
        objectLevel = 0
        
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
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType(),objectLevel=objectLevel)
    
    def slaveInfoSet(self,uid=None,obj=None):
        
        objectLevel = 0
        
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
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=hbusSlaveObjectDataType,objectLevel=objectLevel)
        
    
    def staticFiles(self,filename):
        
        return static_file(filename,root='web_static')
    
    #roda
    def run(self):
        
        #cria rotas
        route("/")(self.index)
        route("/index.html")(self.index)
        
        route("/slave-addr/<addr>")(self.slaveInfo)
        route("/slave-uid/<uid>")(self.slaveInfo)
        route("/slave-uid/<uid>/<obj>")(self.slaveInfo)
        route("/slave-uid/<uid>/<obj>",method="POST")(self.slaveInfoSet)
        
        route ("/static/<filename>")(self.staticFiles)
        route ("/favicon.ico")(self.favicon)
        
        run(host='192.168.1.122',port=self.port)

#test_server = HBUSWEB(8000,None)
#test_server.run()

