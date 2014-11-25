# coding=utf-8

##@package hbus
#hbussd main module
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2012-2014


import logging
from hbusmaster import *
from hbustcpserver import *
from hbus_web import *
import argparse

from twisted.internet import reactor
from twisted.internet.serialport import SerialPort
from twisted.internet.protocol import Factory, Protocol, ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import LoopingCall
#from twisted.internet.defer import setDebugging
#setDebugging(True)

from twisted.web import server

from hbusjsonserver import *

import signal

##Main bus where master is located
BUSID = 0

##Twisted protocol subclass for serial port access
class TwistedSerialPort(Protocol):

    def __init__(self,master):
        self.master = master
    
    ##Function prototype for connection made event
    def connectionMade(self):
        
        self.master.serialConnected()
    
    ##Function prototype for data received event
    #@param data received data
    def dataReceived(self, data):
        
        self.master.serialNewData(data)

##Fakebus client interface
class HBUSFakeBus(ClientFactory):

    def __init__(self,master):
        self.master = master
        self.serial = TwistedSerialPort(self.master)
    
    def startedConnecting(self,connector):
        pass

    def buildProtocol(self, addr):
        return self.serial
    
    def clientConnectionLost(self, connector, reason):
        pass

    def clientConnectionFailed(self, connector, reason):
        pass


##Main HBUS server object class
#
#Cpntains control elements for external connections
#
#@todo stable: Verify behavior in case addressing timeouts occur
#@todo stable: Finishing up test version, include byte type value modifier for web page
#@todo stable: incluir código para permitir edição de objetos tipo Byte, Int e Unsigned Int
#@todo default: Implement integrated twisted http server for JSON data exchange
#@todo default: Explore feasibility of doing an automatic data dump of all system objects when enumeration is done
class TwistedhbusMaster(HbusMaster):
    
    hbusSerial = None
    
    ##Serial port system initialization
    def serialCreate(self,fake=False):
        
        if fake == False:
            self.hbusSerial = TwistedSerialPort(self)
            SerialPort(self.hbusSerial, self.serialPort, reactor, baudrate=self.serialBaud,timeout=0)
        else:
            #fake bus
            f = HBUSFakeBus(self)
            self.hbusSerial = f.serial
            reactor.connectTCP('localhost',9090,f) #connect to ourselves!
    
    ##Writes data to serial port
    #@param string data string to be written
    def serialWrite(self, string):
        
        self.hbusSerial.transport.write(string)
        
        pass
    
    def initWebServer(self):
        
        pass

##Signal handler
#@param signum signal number
#@param frame signal frame
def SignalHandler(signum, frame):

    reactor.stop()
    #exit(0)

##Master entering Operational state after initial scan of HBUS devices event
def hbusMasterOperational():
    
    reactor.callInThread(hbusWeb.run) #@UndefinedVariable

##Main execution loop
def main():
    
    #argparse
    parser = argparse.ArgumentParser(description='HBUS Services Daemon')
    mutexArgs = parser.add_mutually_exclusive_group()
    mutexArgs.add_argument('-s',help='Serial port path')
    mutexArgs.add_argument('-f',help='Enable fake bus for debugging without actual hardware',action='store_true')
    parser.add_argument('-w',help='Enables integrated web server',action='store_true')
    parser.add_argument('-wp',help='Integrated web server port',default=8000,type=int)
    
    parser.add_argument('-t',help='Enables TCP server',action='store_true')
    parser.add_argument('-tp',help='TCP server port',default=8123,type=int)
    
    parser.add_argument('-c',help='Slave polling interval in seconds',default=300,type=int)

    args = vars(parser.parse_args())
    
    if args['s'] == None and args['f'] == False:
        print "error: bus connection not setup! use -f or -s"
        #parser.print_help()
        exit(1)

    logging.basicConfig(level=logging.DEBUG,filename='hbussd.log',filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
    logger = logging.getLogger('hbussd')
    
    logger.info("hbussd start")
    
    signal.signal(signal.SIGTERM, SignalHandler)
    signal.signal(signal.SIGINT, SignalHandler)
    
    hbusMaster = TwistedhbusMaster(args['s'],baudrate=100000,reactor=reactor)

    hbusMasterPeriodicTask = LoopingCall(hbusMaster.periodicCall)
    hbusMasterPeriodicTask.start(1)
    
    hbusSlaveChecker = LoopingCall(hbusMaster.checkSlaves)
    hbusSlaveChecker.start(args['c'], False)
    
    #web server start
    ##@todo start server only after enumeration
    
    if args['w'] == True:
        #integrated web server
        logger.info('Integrated web server enabled')
        hbusWeb = HBUSWEB(args['wp'],hbusMaster)
        reactor.callInThread(hbusWeb.run) #@UndefinedVariable
    
    if args['t'] == True:
        reactor.listenTCP(args['tp'], HBUSTCPFactory(hbusMaster)) #@UndefinedVariable
        
    #JSON SERVER
    reactor.listenTCP(7080, server.Site(HBUSJSONServer(hbusMaster))) #@UndefinedVariable
    
    reactor.run() #@UndefinedVariable
    
##Main function
if __name__ == '__main__':
    main()
