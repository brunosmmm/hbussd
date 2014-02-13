#coding=utf-8
'''
Created on 17/08/2013

@author: bruno
'''

from hbus_base import hbusCommand

HBUS_PUBKEY_SIZE = 192
HBUS_SIGNATURE_SIZE = 192 #assinatura é 192, mas é acompanhada de mais um byte que é e/f/r (193 bytes)

HBUSCOMMAND_SETCH = hbusCommand(0x01,3,32,"SETCH")
HBUSCOMMAND_GETCH = hbusCommand(0x04,1,1,"GETCH")
HBUSCOMMAND_SEARCH = hbusCommand(0x03,0,0,"SEARCH")
HBUSCOMMAND_ACK = hbusCommand(0x06,0,0,"ACK")
HBUSCOMMAND_QUERY = hbusCommand(0x07,1,1,"QUERY")
HBUSCOMMAND_QUERY_RESP = hbusCommand(0x08,3,32,"QUERY_RESP")
HBUSCOMMAND_RESPONSE = hbusCommand(0x10,1,32,"RESP")
HBUSCOMMAND_ERROR = hbusCommand(0x20,2,2,"ERROR")
HBUSCOMMAND_BUSLOCK = hbusCommand(0xF0,0,0,"BUSLOCK")
HBUSCOMMAND_BUSUNLOCK = hbusCommand(0xF1,0,0,"BUSUNLOCK")
HBUSCOMMAND_SOFTRESET = hbusCommand(0xF2,0,HBUS_SIGNATURE_SIZE+2,"SOFTRESET") #tamanho máximo é HBUS_SIGNATURE_SIZE + 2 -> (PSZ;e/f/r;assinatura)
HBUSCOMMAND_QUERY_EP = hbusCommand(0x11,1,1,"QUERY_EP")
HBUSCOMMAND_QUERY_INT = hbusCommand(0x12,1,1,"QUERY_INT")
HBUSCOMMAND_STREAMW = hbusCommand(0x40,2,2,"STREAMW")
HBUSCOMMAND_STREAMR = hbusCommand(0x41,2,2,"STREAMR")
HBUSCOMMAND_INT = hbusCommand(0x80,1,1,"INT")
HBUSCOMMAND_KEYSET = hbusCommand(0xA0,HBUS_PUBKEY_SIZE+1,HBUS_PUBKEY_SIZE+1,"KEYSET")
HBUSCOMMAND_KEYRESET = hbusCommand(0xA1,1,1,"KEYRESET")

HBUS_RESPONSEPAIRS = {HBUSCOMMAND_GETCH : HBUSCOMMAND_RESPONSE, HBUSCOMMAND_QUERY : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_QUERY_EP : HBUSCOMMAND_QUERY_RESP, 
                      HBUSCOMMAND_QUERY_INT : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_SEARCH : HBUSCOMMAND_ACK}

HBUS_COMMANDLIST = (HBUSCOMMAND_SETCH,HBUSCOMMAND_SEARCH,HBUSCOMMAND_GETCH,HBUSCOMMAND_ACK,HBUSCOMMAND_QUERY,HBUSCOMMAND_QUERY_RESP,HBUSCOMMAND_RESPONSE,
                    HBUSCOMMAND_ERROR,HBUSCOMMAND_BUSLOCK,HBUSCOMMAND_BUSUNLOCK,HBUSCOMMAND_SOFTRESET, HBUSCOMMAND_QUERY_EP, HBUSCOMMAND_QUERY_INT, HBUSCOMMAND_STREAMW, 
                    HBUSCOMMAND_STREAMR, HBUSCOMMAND_INT, HBUSCOMMAND_KEYSET, HBUSCOMMAND_KEYRESET)
HBUS_COMMANDBYTELIST = (x.commandByte for x in HBUS_COMMANDLIST)

HBUS_BROADCAST_ADDRESS = 255

HBUS_UNITS = {'A' : 'A', 'V' : 'V', 'P' : 'Pa', 'C':'C', 'd' : 'dBm', 'D' : 'dB'}

HBUS_SLAVE_QUERY_INTERVAL = 0.1

class hbusBusStatus:
    
    hbusBusFree = 0
    hbusBusLockedThis = 1
    hbusBusLockedOther = 2
    
class hbusMasterRxState:
    
    hbusRXSBID = 0
    hbusRXSDID = 1
    hbusRXTBID = 2
    hbusRXTDID = 3
    hbusRXCMD  = 4
    hbusRXADDR = 5
    hbusRXPSZ  = 6
    hbusRXPRM  = 7
    hbusRXSTP  = 8
    
class hbusSlaveObjectPermissions:
    
    hbusSlaveObjectRead = 1
    hbusSlaveObjectWrite = 2
    hbusSlaveObjectReadWrite = 3
    
class hbusSlaveCapabilities:
    
    hbusSlaveAuthSupport = 8
    hbusSlaveEndpointSupport = 2
    hbusSlaveUCODESupport = 16
    hbusSlaveIntSupport = 4
    hbusSlaveCryptoSupport = 1
    hbusSlaveRevAuthSupport = 0x20