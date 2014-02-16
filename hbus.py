# coding=utf-8

##@package hbus
#Módulo principal do hbussd
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2012-2014


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

from twisted.web import server

from hbusjsonserver import *

import signal
#import threading

BUSID = 0

##Subclasse de protocolo Twisted para acesso a porta serial
class TwistedSerialPort(Protocol):
    
    ##Protótipo de função para evento de realização de conexão
    def connectionMade(self):
        
        pass
    
    ##Protótipo de função para evento de recepção de dados
    #@param data dados recebidos
    def dataReceived(self, data):
        
        pass

##Subclasse do objeto principal do servidor HBUS
#
#Contém elementos de controle de conexões externas
#
#@todo stable: Verificar ação em caso de timeouts no endereçamento
#@todo stable: Para finalizar versão de testes, incluir modificador para valores do tipo byte através da página web
#@todo stable: incluir código para permitir edição de objetos tipo Byte, Int e Unsigned Int
#@todo default: Implementar servidor http integrado twisted, para troca de dados via JSON
#@todo default: Estudar a realização de dump automático de todos os valores de objetos no sistema ao completar enumeração
class TwistedhbusMaster(hbusMaster):
    
    hbusSerial = None
    
    ##Função para inicialização do sistema de porta serial
    def serialCreate(self):
        
        ##Objeto da porta serial
        self.hbusSerial = TwistedSerialPort()

        self.hbusSerial.dataReceived = self.serialNewData #overload forçado
        self.hbusSerial.connectionMade = self.serialConnected
        
        SerialPort(self.hbusSerial, self.serialPort, reactor, baudrate=self.serialBaud,timeout=0)
    
    ##Realiza a escrita de dados na porta serial
    #@param string string de dados a serem escritos na porta serial
    def serialWrite(self, string):
        
        self.hbusSerial.transport.write(string)
        
        pass
    
    def initWebServer(self):
        
        pass

##Função para gerenciamentos de sinais globais
#@param signum identificador do sinal
#@param frame quadro
def SignalHandler(signum, frame):
    
    if signal == signal.SIGTERM:
        exit(0)

##Função chamada no evento de término da leitura inicial dos dados de dispositivos HBUS
def hbusMasterOperational():
    
    reactor.callInThread(hbusWeb.run)

##Loop principal de execução
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
    ##@todo lançar página apenas após enumeração
    
    if args['w'] == True:
        #habilita servidor integrado
        logger.info('Servidor web integrado habilitado')
        hbusWeb = HBUSWEB(args['wp'],hbusMaster)
        reactor.callInThread(hbusWeb.run)
    
    if args['t'] == True:
        reactor.listenTCP(args['tp'], HBUSTCPFactory(hbusMaster))
        
    #JSON SERVER
    reactor.listenTCP(7080, server.Site(HBUSJSONServer(hbusMaster)))
    
    reactor.run()
    
##Função principal do programa
if __name__ == '__main__':
    main()