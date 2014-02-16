#coding=utf-8

##@package hbus_constants
#Constantes de uso geral no hbussd
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2013

from hbus_base import hbusCommand

##Tamanho da chave de segurança HBUS em bytes
HBUS_PUBKEY_SIZE = 192

##Tamanho da assinatura de segurança HBUS em bytes
#
#Assinatura tem tamanho 192, mas é acompanhada de mais um byte que é e/f/r (193 bytes)
HBUS_SIGNATURE_SIZE = 192 

##@defgroup hbusCommands Comandos HBUS
#Lista de comandos do barramento HBUS e seus valores e propriedades
#
#@htmlonly
#<table border>
#<tr>
#<td> <b> ID do comando </b> </td>
#<td> <b> Tamanho mínimo </b> </td>
#<td> <b> Tamanho máximo </b> </td>
#<td> <b> Nome do comando </b> </td>
#</tr>
#<tr>
#<td> 0x01 </td>
#<td> 3    </td>
#<td> 32   </td>
#<td> SETCH </td>
#</tr>
#<tr>
#<td> 0x03 </td>
#<td> 0    </td>
#<td> 0   </td>
#<td> SEARCH </td>
#</tr>
#<tr>
#<td> 0x04 </td>
#<td> 1    </td>
#<td> 1   </td>
#<td> GETCH </td>
#</tr>
#<tr>
#<td> 0x06 </td>
#<td> 0    </td>
#<td> 0   </td>
#<td> ACK </td>
#</tr>
#<tr>
#<td> 0x07 </td>
#<td> 1    </td>
#<td> 1   </td>
#<td> QUERY </td>
#</tr>
#<tr>
#<td> 0x08 </td>
#<td> 3    </td>
#<td> 32   </td>
#<td> QUERY_RESP </td>
#</tr>
#<tr>
#<td> 0x10 </td>
#<td> 1    </td>
#<td> 32   </td>
#<td> RESP </td>
#</tr>
#<tr>
#<td> 0x11 </td>
#<td> 1    </td>
#<td> 1   </td>
#<td> QUERY_EP </td>
#</tr>
#<tr>
#<td> 0x12 </td>
#<td> 1    </td>
#<td> 1   </td>
#<td> QUERY_INT </td>
#</tr>
#<tr>
#<td> 0x40 </td>
#<td> 2    </td>
#<td> 2   </td>
#<td> STREAMW </td>
#</tr>
#<tr>
#<td> 0x41 </td>
#<td> 2    </td>
#<td> 2   </td>
#<td> STREAMR </td>
#</tr>
#<tr>
#<td> 0x80 </td>
#<td> 1    </td>
#<td> 1   </td>
#<td> INT </td>
#</tr>
#<tr>
#<td> 0xA0 </td>
#<td> HBUS_PUBKEY_SIZE+1    </td>
#<td> HBUS_PUBKEY_SIZE+1   </td>
#<td> KEYSET </td>
#</tr>
#<tr>
#<td> 0xA1 </td>
#<td> 1    </td>
#<td> 1   </td>
#<td> KEYRESET </td>
#</tr>
#<tr>
#<td> 0xF0 </td>
#<td> 0    </td>
#<td> 0   </td>
#<td> BUSLOCK </td>
#</tr>
#<tr>
#<td> 0xF1 </td>
#<td> 0    </td>
#<td> 0   </td>
#<td> BUSUNLOCK </td>
#</tr>
#<tr>
#<td> 0xF2 </td>
#<td> 0    </td>
#<td> HBUS_SIGNATURE_SIZE+2   </td>
#<td> SOFTRESET </td>
#</tr>
#</table>
#@endhtmlonly
#@{

##Comando de escrita de valor em objeto de dispositivo (SETCH)
HBUSCOMMAND_SETCH = hbusCommand(0x01,3,32,"SETCH")
##Comando de leitura de valor em objeto de dispositivo (GETCH)
HBUSCOMMAND_GETCH = hbusCommand(0x04,1,1,"GETCH")
##Comando para busca de dispositivos no barramento (SEARCH)
HBUSCOMMAND_SEARCH = hbusCommand(0x03,0,0,"SEARCH")
##Comando para confirmação de operações no barramento (ACK)
HBUSCOMMAND_ACK = hbusCommand(0x06,0,0,"ACK")
##Comando para busca de informações sobre objeto de dispositivo (QUERY) 
HBUSCOMMAND_QUERY = hbusCommand(0x07,1,1,"QUERY")
##Comando de retorno de informações sobre objeto de dispositivo (QUERY_RESP)
HBUSCOMMAND_QUERY_RESP = hbusCommand(0x08,3,32,"QUERY_RESP")
##Comando de retorno de resposta com valor de objeto de dispositivo (RESP)
HBUSCOMMAND_RESPONSE = hbusCommand(0x10,1,32,"RESP")
##Comando indicador de erros (ERROR)
HBUSCOMMAND_ERROR = hbusCommand(0x20,2,2,"ERROR")
##Comando de travamento do barramento (BUSLOCK)
HBUSCOMMAND_BUSLOCK = hbusCommand(0xF0,0,0,"BUSLOCK")
##Comando de destravamento do barramento (BUSUNLOCK)
HBUSCOMMAND_BUSUNLOCK = hbusCommand(0xF1,0,0,"BUSUNLOCK")
##Comando de RESET dos dispositivos no barramento (RESET)
HBUSCOMMAND_SOFTRESET = hbusCommand(0xF2,0,HBUS_SIGNATURE_SIZE+2,"SOFTRESET") #tamanho máximo é HBUS_SIGNATURE_SIZE + 2 -> (PSZ;e/f/r;assinatura)
##Comando para busca de informações sobre endpoints de dispositivo (QUERY_EP)
HBUSCOMMAND_QUERY_EP = hbusCommand(0x11,1,1,"QUERY_EP")
##Comando para busca de informações sobre interrupções de dispositivo (QUERY_INT)
HBUSCOMMAND_QUERY_INT = hbusCommand(0x12,1,1,"QUERY_INT")
##Comando para realizar operação de escrita em bloco em endpoint de dispositivo (STREAMW)
HBUSCOMMAND_STREAMW = hbusCommand(0x40,2,2,"STREAMW")
##Comando para realizar operação de leitura em bloco em endpoint de dispositivo (STREAMR)
HBUSCOMMAND_STREAMR = hbusCommand(0x41,2,2,"STREAMR")
##Comando para indicar interrupção (INT)
HBUSCOMMAND_INT = hbusCommand(0x80,1,1,"INT")
##Comando para realizar gravação da chave de segurança em dispositivo (KEYSET)
HBUSCOMMAND_KEYSET = hbusCommand(0xA0,HBUS_PUBKEY_SIZE+1,HBUS_PUBKEY_SIZE+1,"KEYSET")
##Comando para realizar RESET da chave de segurança em dispositivo (KEYRESET)
HBUSCOMMAND_KEYRESET = hbusCommand(0xA1,1,1,"KEYRESET")

##@}

##Pares de resposta para comandos HBUS --- comandos esperados como resposta para comandos enviados
HBUS_RESPONSEPAIRS = {HBUSCOMMAND_GETCH : HBUSCOMMAND_RESPONSE, HBUSCOMMAND_QUERY : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_QUERY_EP : HBUSCOMMAND_QUERY_RESP, 
                      HBUSCOMMAND_QUERY_INT : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_SEARCH : HBUSCOMMAND_ACK}

##Lista de todos os comandos HBUS
HBUS_COMMANDLIST = (HBUSCOMMAND_SETCH,HBUSCOMMAND_SEARCH,HBUSCOMMAND_GETCH,HBUSCOMMAND_ACK,HBUSCOMMAND_QUERY,HBUSCOMMAND_QUERY_RESP,HBUSCOMMAND_RESPONSE,
                    HBUSCOMMAND_ERROR,HBUSCOMMAND_BUSLOCK,HBUSCOMMAND_BUSUNLOCK,HBUSCOMMAND_SOFTRESET, HBUSCOMMAND_QUERY_EP, HBUSCOMMAND_QUERY_INT, HBUSCOMMAND_STREAMW, 
                    HBUSCOMMAND_STREAMR, HBUSCOMMAND_INT, HBUSCOMMAND_KEYSET, HBUSCOMMAND_KEYRESET)
##Lista de IDs de todos os comandos HBUS
HBUS_COMMANDBYTELIST = (x.commandByte for x in HBUS_COMMANDLIST)

##Endereço de broadcast
HBUS_BROADCAST_ADDRESS = 255

##Unidades aceitas e strings respectivas
HBUS_UNITS = {'A' : 'A', 'V' : 'V', 'P' : 'Pa', 'C':'C', 'd' : 'dBm', 'D' : 'dB'}

##Intervalo entre execução de comandos do tipo QUERY
HBUS_SLAVE_QUERY_INTERVAL = 0.1

##@defgroup stateMachines Máquinas de estado
#Máquinas de estado utilizadas nos processos de controle do barramento
#@{

##Status de recepção de pacote no mestre HBUS
class hbusMasterRxState:
    
    ##SBID recebido
    hbusRXSBID = 0
    ##SDID recebido
    hbusRXSDID = 1
    ##TBID recebido
    hbusRXTBID = 2
    ##TDID recebido
    hbusRXTDID = 3
    ##CMD recebido
    hbusRXCMD  = 4
    ##ADDR recebido
    hbusRXADDR = 5
    ##PSZ recebido
    hbusRXPSZ  = 6
    ##PRM recebido
    hbusRXPRM  = 7
    ##STP recebido
    hbusRXSTP  = 8

##@}

##@defgroup statusIndicators Indicadores de status e propriedades
#Indicadores de estado do sistema e descritores de propriedades dos dispositivos e objetos
#@{

##Status do barramento HBUS
class hbusBusStatus:
    
    ##Barramento livre 
    hbusBusFree = 0
    ##Barramento travado entre o mestre e um dispositivo
    hbusBusLockedThis = 1
    ##Barramento travado entre outros dois dispositivos
    hbusBusLockedOther = 2

##Permissões de objeto de dispositivo
class hbusSlaveObjectPermissions:
    
    ##O objeto tem permissão de leitura
    hbusSlaveObjectRead = 1
    ##O objeto tem permissão de escrita
    hbusSlaveObjectWrite = 2
    ##O objeto tem permissão de leitura e escrita
    hbusSlaveObjectReadWrite = 3
    
##Capacidades de um dispositivo
class hbusSlaveCapabilities:
    
    ##O dispositivo tem suporte a autenticação
    hbusSlaveAuthSupport = 8
    ##O dispositivo tem suporte a endpoints
    hbusSlaveEndpointSupport = 2
    ##O dispositivo tem suporte a microcodigo HBUS
    hbusSlaveUCODESupport = 16
    ##O dispositivo tem suporte a interrupções
    hbusSlaveIntSupport = 4
    ##O dispositivo tem suporte a criptografia
    hbusSlaveCryptoSupport = 1
    ##O dispositivo tem suporte a autenticação reversa
    hbusSlaveRevAuthSupport = 0x20
    
##@}