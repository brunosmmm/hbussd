#coding=utf-8

##@package hbus_web
# Integrated web server for control, using pyBottle
# @author Bruno Morais <brunosmmm@gmail.com>
# @date 2013-2014
# @todo better documentation

from hbusmaster import *
import string
from bottle import route, run, template, static_file, request
import re

##Web server class
class HBUSWEB:

    ##wait for asynchronous operations
    wait = False

    ##Constructor
    #@param port HTTP port
    #@param hbusMaster main master object reference for direct manipulation
    #@todo decouple master object
    def __init__(self,port,hbusMaster):
        
        ##Server port
        self.port = port
        ##main master object
        self.hbusMaster = hbusMaster
        ##Minimum object level visible on web interface
        self.objectLevel = 0

    ##Templates main page
    #@return template HTML
    def index(self):
        
        return template('hbus_index',slaves=self.hbusMaster.detectedSlaveList.values(),masterStatus=self.hbusMaster.getInformationData(),re=re)
    
    ##Favorite icon for web browser
    #@return icon file
    def favicon(self):
        
        return static_file('favicon.ico',root='web_static') 
    
    ##Reads an object's value and displays it
    #
    #returns a formatted value for AJAX use
    #@param uid device UID
    #@param obj object number
    #@return requested data
    def readSlaveObject(self,uid=None,obj=None):
        
        self.wait = False
        def waitForSlaveRead(dummy):
            
            self.wait = False
        
        m = re.match(r"0x([0-9A-Fa-f]+)L?",uid)
        devUID = m.group(1)
            
        addr = self.hbusMaster.findDeviceByUID(int(devUID,16))
        
        if addr == None:
            s = None
        else:
            if addr.bus_number == 254:
                s = self.hbusMaster.virtualDeviceList[addr.global_id()]
            else:
                s = self.hbusMaster.detectedSlaveList[addr.global_id()]
        
        if obj != None:
            
            try:
                self.wait = True
                self.hbusMaster.readSlaveObject(addr, int(obj), callBack=waitForSlaveRead,timeoutCallback=waitForSlaveRead)
                
                while (self.wait == True):
                    pass
            except:
                self.logger.debug('error reading device object!!')
            
        if s != None:
            data = s.hbusSlaveObjects[int(obj)].getFormattedValue()
        else:
            data = "?"
            
        if data == None:
            data = "?"
            
        return (data)
    
    ##Templates a page with device information
    #@param addr device address
    #@param uid device UID
    #@param obj object number
    #@return template HTML
    def slaveInfo(self,addr=None,uid=None,obj=None):
        
        getN = 0
        
        self.wait = False
        def waitForSlaveRead(dummy):
            
            self.wait = False
        
        if addr != None:
            
            devAddr = string.split(addr,":")
            device = HbusDeviceAddress(int(devAddr[0]),int(devAddr[1]))
            
            s = self.hbusMaster.detectedSlaveList[device.global_id()]
        elif uid != None:
            
            m = re.match(r"0x([0-9A-Fa-f]+)L?",uid)
            devUID = m.group(1)
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID,16))
            
            if addr == None:
                s = None
            else:
                if addr.bus_number == 254:
                    s = self.hbusMaster.virtualDeviceList[addr.global_id()]
                else:
                    s = self.hbusMaster.detectedSlaveList[addr.global_id()]
            
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
                
                ##@todo retur error template, device not available
                
                pass
                
            writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x02 and x.objectLevel >= self.objectLevel and x.objectHidden == False])
            readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x01 and x.objectLevel >= self.objectLevel and x.objectHidden == False])
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=HbusObjDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        readObjCount=readObjectCount,writeObjCount=writeObjectCount,re=re,getNumber=getN)
        
    ##@todo document this
    def busList(self):
        
        from bottle import response
        from json import dumps
        
        rv = []
        for bus in self.hbusMaster.getInformationData().activeBusses:
        
            rv.append([{"busNumber": bus}])
        
        response.content_type = 'application/json'
        return dumps(rv)
    
    ##Writes value to device object
    #@param uid device UID
    #@param obj object number
    #@return template HTML with updated data
    def slaveWriteObject(self,uid=None,obj=None):
        

        if uid != None:
            
            m = re.match(r"0x([0-9A-Fa-f]+)L?",uid)
            devUID = m.group(1)
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID,16))
            
            if addr == None:
                s = None
            else:
                if addr.bus_number == 254:
                    s = self.hbusMaster.virtualDeviceList[addr.global_id()]
                else:
                    s = self.hbusMaster.detectedSlaveList[addr.global_id()]
                
            if s == None:
                
                ##@todo return error template, device not available
                
                pass
        
        return template('hbus_slave_object_set',slave=s,hbusSlaveObjectDataType=HbusObjDataType,objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        objectNumber = int(obj),re=re,percentToRange=self.percentToRange)
    
    ##@todo document this
    def slaveInfoSet(self,uid=None,obj=None):
        
        newObjValue = request.forms.get('value')
        
        if uid != None:
            
            m = re.match(r"0x([0-9A-Fa-f]+)L?",uid)
            devUID = m.group(1)
            
            addr = self.hbusMaster.findDeviceByUID(int(devUID,16))
            
            if addr == None:
                s = None
            else:
                if addr.bus_number == 254:
                    s = self.hbusMaster.virtualDeviceList[addr.global_id()]
                else:
                    s = self.hbusMaster.detectedSlaveList[addr.global_id()]
            
            if obj != None:
                
                #try:
                self.hbusMaster.writeFormattedSlaveObject(addr,int(obj),newObjValue)

                #except:
                #    pass
        
            #writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x02 and x.objectLevel > self.objectLevel])
            #readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x01 and x.objectLevel > self.objectLevel])
        
        return template('hbus_slave_object_set',slave=s,hbusSlaveObjectDataType=HbusObjDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        objectNumber = int(obj),re=re,percentToRange=self.percentToRange)
                        #readObjCount=readObjectCount,writeObjCount=writeObjectCount)
    
    ##Generates page with devices in a bus
    #@param busNumber bus number
    #@return template HTML
    def slavesByBus(self,busNumber=None):
        
        if int(busNumber) == 255:
            slaveList = self.hbusMaster.detectedSlaveList.values()
            slaveList.extend(self.hbusMaster.virtualDeviceList.values())
        elif int(busNumber) == 254:
            #virtual device bus
            slaveList = self.hbusMaster.virtualDeviceList.values()
        else:
            slaveList = []
            for slave in self.hbusMaster.detectedSlaveList.values():
                if slave.hbusSlaveAddress.bus_number == int(busNumber):
                    slaveList.append(slave)
        
        return template('hbus_slave_by_bus',slaveList=slaveList,masterStatus=self.hbusMaster.getInformationData(),busNumber=busNumber,re=re)
    
    ##Sets minimum object level for showing on web interface
    #@param level minimum level
    def setLevel(self,level=None):
        
        if level == None:
            return
        
        try:
            self.objectLevel = int(level)
        finally:
            return
    
    ##Fetches static files
    #@param filename name of file to be fetched
    #@return file
    def staticFiles(self,filename):
        
        return static_file(filename,root='web_static')
    
    ##Converts percent values to scaled
    #@param percentStr percent string
    #@return value
    def percentToRange(self,percentStr):
        
        if percentStr == "?" or percentStr == None:
            return "0"
        
        s = re.sub(r'\.[0-9]+%$','',percentStr)
        
        return s
    
    ##pyBottle main loop
    def run(self):
        
        #creates routes
        route("/")(self.index)
        route("/index.html")(self.index)
        
        route("/slave-addr/<addr>")(self.slaveInfo)
        route("/slave-uid/<uid>")(self.slaveInfo)
        route("/slave-uid/<uid>/get-<obj>")(self.slaveInfo)
        route("/slave-uid/<uid>/set-<obj>")(self.slaveWriteObject)
        route("/slave-uid/<uid>/set-<obj>",method="POST")(self.slaveInfoSet)
        route("/slave-uid/<uid>/objdata-<obj>")(self.readSlaveObject)
        route("/busses")(self.busList)
        
        #list of devices by bus number
        route("/bus/<busNumber>")(self.slavesByBus)
        
        route ("/static/<filename>")(self.staticFiles)
        route ("/favicon.ico")(self.favicon)
        
        #hidden options
        route ("/set-level/<level>")(self.setLevel)
        
        run(host='127.0.0.1',port=self.port)
