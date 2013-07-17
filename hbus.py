# coding=utf-8
import logging
from hbusmaster import *
from hbustcpserver import *
from hbus_web import *

from twisted.internet import reactor
from twisted.internet.serialport import SerialPort
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import LoopingCall

import signal
#import threading

BUSID = 0

class TwistedSerialPort(Protocol):
    
    def connectionMade(self):
        
        pass
        
    def dataReceived(self, data):
        
        pass

class TwistedhbusMaster(hbusMaster):
    
    hbusSerial = None
    
    def serialCreate(self):
        
        self.hbusSerial = TwistedSerialPort()

        self.hbusSerial.dataReceived = self.serialNewData #overload forçado
        self.hbusSerial.connectionMade = self.serialConnected
        
        SerialPort(self.hbusSerial, self.serialPort, reactor, baudrate=self.serialBaud,timeout=0)
        
        pass
    
    def serialWrite(self, string):
        
        self.hbusSerial.transport.write(string)
        
        #self.hbusSerial.transport.flushInput()
        
        pass
    
    def initWebServer(self):
        
        pass

def SignalHandler(signum, frame):
    
    if signal == signal.SIGTERM:
        exit(0)

def main():
    
    logging.basicConfig(level=logging.DEBUG,filename='hbus_skeleton.log',filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
    logger = logging.getLogger('hbus_skeleton')
    
    logger.info("hbus_skeleton start")
    
    signal.signal(signal.SIGTERM, SignalHandler)
    
    hbusMaster = TwistedhbusMaster('/dev/ttyUSB0',baudrate=100000)
    
    hbusMasterPeriodicTask = LoopingCall(hbusMaster.periodicCall)
    hbusMasterPeriodicTask.start(1)
    
    #lança pagina web
    hbusWeb = HBUSWEB(8000,hbusMaster)
    reactor.callInThread(hbusWeb.run)
    
    reactor.listenTCP(8123, HBUSTCPFactory(hbusMaster))
    
    reactor.run()
    

if __name__ == '__main__':
    main()