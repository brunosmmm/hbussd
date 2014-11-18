#coding=utf-8

##@package hbus_fb
# fake bus for debugging without actual hardware connected
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 11/17/2014
# @todo implement fake bus device structure
# @todo load device configuration from files


from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
import struct
import logging

##Fake bus main class
class FakeBusSerialPort(Protocol):

    def __init__(self):
        self.logger = logging.getLogger('hbussd.fakebus')
        self.logger.debug("fakebus active")
    
    def connectionMade(self):
        self.logger.debug("hbus master connected to fakebus")

    def dataReceived(self,data):
        pass
