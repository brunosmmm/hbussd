#coding=utf-8

##@package hbus_constants
#hbussd general purpuse constants
#@author Bruno Morais <brunosmmm@gmail.com>
#@date 2013

from hbus_base import hbusCommand

##HBUS security key size in bytes
#@todo Make this useful
HBUS_PUBKEY_SIZE = 192

##HBUS authentication key size in bytes
#
#This size is 192 but it is followed by another byte, e/f/r (193 bytes)
HBUS_SIGNATURE_SIZE = 192 

##@defgroup hbusCommands HBUS commands
#HBUS command list, values and properties
#
#@htmlonly
#<table border>
#<tr>
#<td> <b> Command ID </b> </td>
#<td> <b> Minimum length </b> </td>
#<td> <b> Maximum lenght </b> </td>
#<td> <b> Command name </b> </td>
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

##Write a value in a device's object (SETCH)
HBUSCOMMAND_SETCH = hbusCommand(0x01,3,32,"SETCH")
##Read a value from a device's object (GETCH)
HBUSCOMMAND_GETCH = hbusCommand(0x04,1,1,"GETCH")
##Search for devices in the bus (SEARCH)
HBUSCOMMAND_SEARCH = hbusCommand(0x03,0,0,"SEARCH")
##Acknowledge command (ACK)
HBUSCOMMAND_ACK = hbusCommand(0x06,0,0,"ACK")
##Queries a device's object descriptor for information (QUERY) 
HBUSCOMMAND_QUERY = hbusCommand(0x07,1,1,"QUERY")
##Returns information about a device's object following a QUERY command (QUERY_RESP)
HBUSCOMMAND_QUERY_RESP = hbusCommand(0x08,3,32,"QUERY_RESP")
##Returns the value from a device object following a GETCH command (RESP)
HBUSCOMMAND_RESPONSE = hbusCommand(0x10,1,32,"RESP")
##Error indicator (ERROR)
HBUSCOMMAND_ERROR = hbusCommand(0x20,2,2,"ERROR")
##Buslock command, locks bus traffic between two devices (BUSLOCK)
HBUSCOMMAND_BUSLOCK = hbusCommand(0xF0,0,0,"BUSLOCK")
##Busunlock command, frees bus from a buslock (BUSUNLOCK)
HBUSCOMMAND_BUSUNLOCK = hbusCommand(0xF1,0,0,"BUSUNLOCK")
##Causes devices to do a soft-reset (RESET)
HBUSCOMMAND_SOFTRESET = hbusCommand(0xF2,0,HBUS_SIGNATURE_SIZE+2,"SOFTRESET") #max length is HBUS_SIGNATURE_SIZE + 2 -> (PSZ;e/f/r;key)
##Queries a device's endpoint descriptor for information (QUERY_EP)
HBUSCOMMAND_QUERY_EP = hbusCommand(0x11,1,1,"QUERY_EP")
##Queries a device's interrupt descriptor for information (QUERY_INT)
HBUSCOMMAND_QUERY_INT = hbusCommand(0x12,1,1,"QUERY_INT")
##Block write to a device endpoint (STREAMW)
HBUSCOMMAND_STREAMW = hbusCommand(0x40,2,2,"STREAMW")
##Block read from a device endpoint (STREAMR)
HBUSCOMMAND_STREAMR = hbusCommand(0x41,2,2,"STREAMR")
##Bus interrupt (INT)
HBUSCOMMAND_INT = hbusCommand(0x80,1,1,"INT")
##Transfers security key to a device. Not to be used on a public bus (KEYSET)
HBUSCOMMAND_KEYSET = hbusCommand(0xA0,HBUS_PUBKEY_SIZE+1,HBUS_PUBKEY_SIZE+1,"KEYSET")
##Resets security key currently stored in device (KEYRESET)
HBUSCOMMAND_KEYRESET = hbusCommand(0xA1,1,1,"KEYRESET")

##@}

##HBUS command response pairs --- expected response commands
HBUS_RESPONSEPAIRS = {HBUSCOMMAND_GETCH : HBUSCOMMAND_RESPONSE, HBUSCOMMAND_QUERY : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_QUERY_EP : HBUSCOMMAND_QUERY_RESP, 
                      HBUSCOMMAND_QUERY_INT : HBUSCOMMAND_QUERY_RESP, HBUSCOMMAND_SEARCH : HBUSCOMMAND_ACK}

##List of all HBUS commands
HBUS_COMMANDLIST = (HBUSCOMMAND_SETCH,HBUSCOMMAND_SEARCH,HBUSCOMMAND_GETCH,HBUSCOMMAND_ACK,HBUSCOMMAND_QUERY,HBUSCOMMAND_QUERY_RESP,HBUSCOMMAND_RESPONSE,
                    HBUSCOMMAND_ERROR,HBUSCOMMAND_BUSLOCK,HBUSCOMMAND_BUSUNLOCK,HBUSCOMMAND_SOFTRESET, HBUSCOMMAND_QUERY_EP, HBUSCOMMAND_QUERY_INT, HBUSCOMMAND_STREAMW, 
                    HBUSCOMMAND_STREAMR, HBUSCOMMAND_INT, HBUSCOMMAND_KEYSET, HBUSCOMMAND_KEYRESET)
##List of all commands IDs
HBUS_COMMANDBYTELIST = [x.commandByte for x in HBUS_COMMANDLIST]

##Commands that do not use address or params
HBUS_SCMDBYTELIST = [x.commandByte for x in HBUS_COMMANDLIST if x.maximumLength == 0]

##Commands that use addresses but not params
HBUS_SACMDBYTELIST = [x.commandByte for x in HBUS_COMMANDLIST if x.maximumLength == 1]

##Broadcast address
HBUS_BROADCAST_ADDRESS = 255

##Available units and associated strings for printing
HBUS_UNITS = {'A' : 'A', 'V' : 'V', 'P' : 'Pa', 'C':'C', 'd' : 'dBm', 'D' : 'dB'}

##Delay between QUERY command executions
HBUS_SLAVE_QUERY_INTERVAL = 0.1

##@defgroup stateMachines HBUS state machines
#Used in bus control processes
#@{

##Packet receiving on master
class hbusMasterRxState:
    
    ##SBID received
    hbusRXSBID = 0
    ##SDID received
    hbusRXSDID = 1
    ##TBID received
    hbusRXTBID = 2
    ##TDID received
    hbusRXTDID = 3
    ##CMD received
    hbusRXCMD  = 4
    ##ADDR received
    hbusRXADDR = 5
    ##PSZ received
    hbusRXPSZ  = 6
    ##PRM received
    hbusRXPRM  = 7
    ##STP received
    hbusRXSTP  = 8

##@}

##@defgroup statusIndicators Status and properties indicators
#System status indicators, devices and objects properties descriptors
#@{

##Bus state
class hbusBusStatus:
    
    ##Bus is free 
    hbusBusFree = 0
    ##Bus is locked for master and a device
    hbusBusLockedThis = 1
    ##Bus is locked for two other devices
    hbusBusLockedOther = 2

##Object and device permissions
class hbusSlaveObjectPermissions:
    
    ##Object has read permission
    hbusSlaveObjectRead = 1
    ##Object has write permission
    hbusSlaveObjectWrite = 2
    ##Object has read/write permission
    hbusSlaveObjectReadWrite = 3
    
##Device capabilities
class hbusSlaveCapabilities:
    
    ##Device has master authentication support
    hbusSlaveAuthSupport = 8
    ##Device has endpoint support
    hbusSlaveEndpointSupport = 2
    ##Device has HBUS microcode support
    hbusSlaveUCODESupport = 16
    ##Device has interrupt support
    hbusSlaveIntSupport = 4
    ##Device has crypto support
    hbusSlaveCryptoSupport = 1
    ##Device has device (reverse) authentication support
    hbusSlaveRevAuthSupport = 0x20
    
##@}
