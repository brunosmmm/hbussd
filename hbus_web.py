#coding=utf-8

from hbusmaster import *
import string
from bottle import route, run, template

class HBUSWEB:

    def __init__(self,port,hbusMaster):
        
        self.port = port
        self.hbusMaster = hbusMaster

    def index(self):
    
        return template('hbus_index',list=None)
    
    def slaveInfo(self,addr=None,uid=None):
        
        if addr != None:
            
            devAddr = string.split(addr,":")
            device = hbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
            
            s = self.hbusMaster.detectedSlaveList[device.getGlobalID()]
        elif uid != None:
            
            devUID = string.split(uid,"0x")
            
            s = self.hbusMaster.findDeviceByUID(int(devUID[1],16))
        
        return template('hbus_slave_info',slave=s)
    
    #roda
    def run(self):
        
        #cria rotas
        route("/")(self.index)
        route("/index.html")(self.index)
        
        route("/slave-addr/<addr>")(self.slaveInfo)
        route("/slave-uid/<uid>")(self.slaveInfo)
        
        run(host='localhost',port=self.port)

#test_server = HBUSWEB(8000,None)
#test_server.run()

