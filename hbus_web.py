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

class HBUSWEB(object):
    """HBUS Web server class"""

    ##wait for asynchronous operations
    wait = False

    #@todo decouple master object
    def __init__(self,port,hbusMaster):
        """Class constructor
           @param port HTTP port
           @param hbusMaster main master object reference for manipulation
           """
        
        ##Server port
        self.port = port
        ##main master object
        self.hbusMaster = hbusMaster
        ##Minimum object level visible on web interface
        self.objectLevel = 0
        
    def index(self):
        """Generates main page template
           @return template HTML"""
        
        return template('hbus_index',slaves=self.hbusMaster.detectedSlaveList.values(),masterStatus=self.hbusMaster.getInformationData(),re=re)
    
    def favicon(self):
        """Favorite icon for web browser
           @return icon file"""
        
        return static_file('favicon.ico',root='web_static') 
    
    def readSlaveObject(self,uid=None,obj=None):
        """Reads an object value and displays it
           @param uid device UID
           @param obj object number
           @return requested data"""
        
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
    

    def slaveInfo(self,addr=None,uid=None,obj=None):
        """Templates a page with device information
           @param addr device address
           @param uid device UID
           @param obj object number
           @return template HTML"""
        
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
                
            writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x02 and x.objectLevel >= self.objectLevel and x.hidden == False])
            readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x01 and x.objectLevel >= self.objectLevel and x.hidden == False])
        
        return template('hbus_slave_info',slave=s,hbusSlaveObjectDataType=HbusObjDataType(),objectLevel=self.objectLevel,masterStatus=self.hbusMaster.getInformationData(),
                        readObjCount=readObjectCount,writeObjCount=writeObjectCount,re=re,getNumber=getN)
        
    ##@todo document this properly
    def busList(self):
        """Generates a bus list"""
        
        from bottle import response
        from json import dumps
        
        rv = []
        for bus in self.hbusMaster.getInformationData().activeBusses:
        
            rv.append([{"busNumber": bus}])
        
        response.content_type = 'application/json'
        return dumps(rv)
     
    def slaveWriteObject(self,uid=None,obj=None):
        """Writes value to device object
           @param uid device UID
           @param obj object number
           @return template HTML with updated data"""

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
    
    def slavesByBus(self,busNumber=None):
        """Generates page with devices from a bus
           @param busNumber bus number
           @return template HTML"""
        
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
    
    def setLevel(self,level=None):
        """Sets level filter for visible objects on web interface
           @param level minimum level"""
        
        if level == None:
            return
        
        try:
            self.objectLevel = int(level)
        finally:
            return
    
    def staticFiles(self,filename):
        """Fetches static files
           @param filename name of file to be fetched
           @return file"""
        
        return static_file(filename,root='web_static')
    
    def percentToRange(self,percentStr):
        """Converts percent values to scaled
           @param percentStr percent string
           @return value"""
        
        if percentStr == "?" or percentStr == None:
            return "0"
        
        s = re.sub(r'\.[0-9]+%$','',percentStr)
        
        return s
    
    def run(self):
        """pyBottle main loop"""
        
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
