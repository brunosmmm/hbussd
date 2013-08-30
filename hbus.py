# coding=utf-8
import logging
from hbusmaster import *
from hbustcpserver import *
from hbus_web import *
import argparse

from twisted.internet import reactor
from twisted.internet.serialport import SerialPort
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import LoopingCall
#from twisted.internet.defer import setDebugging
#setDebugging(True)

import signal
#import threading

BUSID = 0

##stable:
##TODO: Verificar ação em caso de timeouts no endereçamento
##TODO: Verificar ação em caso de timeouts no processamento de objetos invisíveis
##TODO: Realizar análise de objetos invisíveis por escravo após a enumeração de cada um e não como um todo
##TODO: Para finalizar versão de testes, incluir modificador para valores do tipo byte através da página web
##TODO: incluir código para permitir edição de objetos tipo Byte, Int e Unsigned Int

##default (desenvolvimento)
##TODO: Implementar servidor http integrado twisted, para troca de dados via JSON
##TODO: Estudar a realização de dump automático de todos os valores de objetos no sistema ao completar enumeração

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
    
    #argparse
    parser = argparse.ArgumentParser(description='HBUS Services Daemon')
    parser.add_argument('-s',help='Caminho da porta serial',required=True)
    parser.add_argument('-w',help='Habilita servidor web integrado',action='store_true')
    parser.add_argument('-wp',help='Porta do servidor web',default=8000,type=int)
    
    parser.add_argument('-t',help='Habilita servidor TCP',action='store_true')
    parser.add_argument('-tp',help='Porta do servidor TCP',default=8123,type=int)
    
    parser.add_argument('-c',help='Intervalo de verificação de escravos em segundos',default=300,type=int)
    
    args = vars(parser.parse_args())
    
    logging.basicConfig(level=logging.DEBUG,filename='hbus_skeleton.log',filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
    logger = logging.getLogger('hbus_skeleton')
    
    logger.info("hbus_skeleton start")
    
    signal.signal(signal.SIGTERM, SignalHandler)
    
    hbusMaster = TwistedhbusMaster(args['s'],baudrate=100000)
    #hbusMaster.enterOperational = hbusMasterOperational
    
    hbusMasterPeriodicTask = LoopingCall(hbusMaster.periodicCall)
    hbusMasterPeriodicTask.start(1)
    
    hbusSlaveChecker = LoopingCall(hbusMaster.checkSlaves)
    hbusSlaveChecker.start(args['c'], False)
    
    #lança pagina web
    ##TODO:lançar página apenas após enumeração
    
    if args['w'] == True:
        #habilita servidor integrado
        logger.info('Servidor web integrado habilitado')
        hbusWeb = HBUSWEB(args['wp'],hbusMaster)
        reactor.callInThread(hbusWeb.run)
    
    if args['t'] == True:
        reactor.listenTCP(args['tp'], HBUSTCPFactory(hbusMaster))
    
    reactor.run()
    

if __name__ == '__main__':
    main()