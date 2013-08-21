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

##TODO: Estudar a realização de dump automático de todos os valores de objetos no sistema ao completar enumeração

##TODO: Estudar arquitetura do template engine (django) para interface de controle web  mais robusta; observar possibilidades de "renomeação" dos dispositivos, barramentos e objetos; persistência;
##        possibilidade de plug-ins específicos ao objeto; etc 

##TODO: Verificar ação em caso de timeouts no endereçamento
##TODO: Verificar ação em caso de timeouts no processamento de objetos invisíveis

##TODO: Realizar análise de objetos invisíveis por escravo após a enumeração de cada um e não como um todo

##TODO: Para finalizar versão de testes, incluir modificador para valores do tipo byte através da página web

##TODO: Implementar servidor http integrado twisted, para troca de dados via JSON

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

def hbusMasterOperational():
    
    reactor.callInThread(hbusWeb.run)

def main():
    
    logging.basicConfig(level=logging.DEBUG,filename='hbus_skeleton.log',filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
    logger = logging.getLogger('hbus_skeleton')
    
    logger.info("hbus_skeleton start")
    
    signal.signal(signal.SIGTERM, SignalHandler)
    
    hbusMaster = TwistedhbusMaster('/dev/ttyUSB0',baudrate=100000)
    #hbusMaster.enterOperational = hbusMasterOperational
    
    hbusMasterPeriodicTask = LoopingCall(hbusMaster.periodicCall)
    hbusMasterPeriodicTask.start(1)
    
    hbusSlaveChecker = LoopingCall(hbusMaster.checkSlaves)
    hbusSlaveChecker.start(300, False)
    
    #lança pagina web
    ##TODO:lançar página apenas após enumeração
    hbusWeb = HBUSWEB(8000,hbusMaster)
    reactor.callInThread(hbusWeb.run)
    
    reactor.listenTCP(8123, HBUSTCPFactory(hbusMaster))
    
    reactor.run()
    

if __name__ == '__main__':
    main()