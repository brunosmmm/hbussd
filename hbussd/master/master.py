"""HBUS Master."""
import logging
import re
import struct
import time
from collections import deque
from datetime import datetime

import hbussd.hbus.crypto
from hbussd.fakebus import hbus_fb
from hbussd.hbus.base import HbusDeviceAddress, HbusInstruction, HbusOperation
from hbussd.hbus.constants import *
from hbussd.hbus.evt import HbusMasterEvent, HbusMasterEventType
from hbussd.hbus.exceptions import HBUSTimeoutException
from hbussd.hbus.slaves import (
    HBUS_DTYPE_OPTIONS,
    HbusDevice,
    HbusDeviceObject,
    HbusEndpoint,
    HbusInterrupt,
    HbusObjDataType,
)
from hbussd.plugins import HbusPluginManager
from twisted.internet import defer, reactor
from twisted.internet.protocol import Factory

BROADCAST_BUS = 255
VIRTUAL_BUS = 254


def get_millis(td):
    """Get actual time in milliseconds."""
    return (
        td.days * 24 * 60 * 60 + td.seconds
    ) * 1000 + td.microseconds / 1000.0


class HbusKeySet:
    """Set of HBUS keys."""

    # Key p
    privateq = None
    # Key q
    privatep = None

    def __init__(self, p, q):
        """Initialize."""
        self.privatep = p
        self.privateq = q

    @property
    def intpubkey(self):
        """Get public key as integer."""
        return self.privatep * self.privateq

    @property
    def strpubkey(self):
        """Get public key as hexadecimal string."""
        h = hex(self.privatep * self.privateq)[2:].rstrip("L")
        if len(h) % 2:
            h = "0%s" % h

        while len(h) < HBUS_PUBKEY_SIZE * 2:
            h = "00%s" % h

        h = bytes.fromhex(h)

        # packStr = str(192)+'s'

        return list(h)  # struct.pack(packStr,h)


p = 342604160482313166816112334007089110910258720251016392985178072980194817098198724574409056226636958394678465934459619696622719424740669649868502396485869067283396294556282972464396510025180816154985285048268006216979372669280971
q = 609828164381195487560324418811535461583859042182887774624946398207269636262857827797730598026846661116173290667288561275278714668006770186716586859843775717295061922379022086436506552898287802124771661400922779346993469164594119
HBUS_ASYMMETRIC_KEYS = HbusKeySet(p, q)


class HbusMasterState:
    """HBUS master states."""

    hbusMasterStarting = 0
    hbusMasterIdle = 1
    hbusMasterSearching = 2
    hbusMasterAddressing = 3
    hbusMasterScanning = 4
    hbusMasterOperational = 5
    hbusMasterChecking = 6
    hbusMasterInterrupted = 7


class HbusPendingAnswer:
    """Pending answer system using deferreds."""

    def __init__(
        self,
        command,
        source,
        timeout,
        callBackDefer,
        actionParameters=None,
        timeoutAction=None,
        timeoutActionParameters=None,
    ):
        """Initialize."""
        self.command = command
        self.source = source
        self.timeout = timeout
        self.now = datetime.now()

        self.dCallback = callBackDefer
        # self.dCallback = defer.Deferred()

        # if action is not None:
        #    self.dCallback.addCallback(action)

        # self.action = action
        self.actionParameters = actionParameters
        self.timeoutActionParameters = timeoutActionParameters

        # self.tCallback = defer.Deferred()
        # if timeoutAction is not None:
        #    self.tCallback.addCallback(timeoutAction)

        # self.timeoutAction = timeoutAction
        self._timeout_handler = None

    @property
    def timeout_handler(self):
        """Get timeout handler."""
        return self._timeout_handler

    @timeout_handler.setter
    def timeout_handler(self, value):
        """Set timeout handler."""
        self._timeout_handler = value

    def cancel_timeout_handler(self):
        """Cancel timeout handler."""
        if self._timeout_handler is not None:
            self._timeout_handler.cancel()


class HbusMasterInformationData:
    """Master information."""

    def __init__(self, slaveCount, activeBusses):
        """Initialize."""
        self.activeSlaveCount = slaveCount
        self.activeBusses = activeBusses


class HbusMaster:
    """HBUS master."""

    pluginManager = None

    hbusSerialRxTimeout = 100

    hbusBusState = HbusBusState.FREE
    hbusBusLockedWith = None
    hbusRxState = HbusRXState.SBID

    communicationBuffer = []
    SearchTimer = None

    expectedResponseQueue = deque()

    awaitingFreeBus = deque()

    outgoingCommands = deque()

    removeQueue = []

    detectedSlaveList = {}
    virtualDeviceList = {}

    staticSlaveList = []

    registeredSlaveCount = 0
    virtualSlaveCount = 0

    masterState = HbusMasterState.hbusMasterStarting

    commandDelay = datetime.now()

    hbusDeviceSearchTimer = datetime.now()

    hbusDeviceSearchInterval = 60000

    autoSearch = True

    nextSlaveCapabilities = None
    nextSlaveUID = None

    hbusDeviceScanningTimeout = False

    rxBytes = 0
    txBytes = 0

    def __init__(self, port, baudrate=100000, busno=0, conf_file=None):
        """Initialize."""

        def fake_bus():
            f = Factory()
            f.protocol = hbus_fb.FakeBusSerialPort
            reactor.listenTCP(9090, f)

            self.serial_create(fake=True)

        def system_start():
            # system started event
            event = HbusMasterEvent(HbusMasterEventType.eventStarted)
            self.pluginManager.m_evt_broadcast(event)

        self.serialBaud = baudrate
        self.hbusMasterAddr = HbusDeviceAddress(busno, 0)

        self.logger = logging.getLogger("hbussd.hbusmaster")
        self.pluginManager = HbusPluginManager("./plugins", self)
        self.search_and_load_plugins()

        # configuration parameters
        self.conf_param = {}
        self._load_configuration(conf_file)

        if port is None and "serial_port" not in self.conf_param:
            # create fakebus system
            fake_bus()
        else:
            if (
                "fakebus" in self.conf_param
                and self.conf_param["fakebus"] is True
            ):
                self.logger.warning(
                    "conflicting options in configuration"
                    " file: fakebus/serial_port"
                )
                fake_bus()
                system_start()
                return
            if port is None:
                self.serialPort = self.conf_param["serial_port"]
            else:
                self.serialPort = port
            self.serial_create(fake=False)

        system_start()

    def _load_configuration(self, conf_file):

        if conf_file is None:
            return

        self.conf_param = conf_file

        # process some configuration params
        if "staticSlaveList" in self.conf_param:
            for addr in self.conf_param["staticSlaveList"]:
                if "busNum" not in addr:
                    continue
                if "devNum" not in addr:
                    continue

                self.staticSlaveList.append(
                    HbusDeviceAddress(int(addr["busNum"]), int(addr["devNum"]))
                )

    def search_and_load_plugins(self):
        """Search and load plugins using plugin manager."""
        self.logger.debug("scanning plugins")

        self.pluginManager.scan_plugins()

        for plugin in self.pluginManager.get_available_plugins():
            try:
                self.logger.debug("loading plugin " + plugin)
                self.pluginManager.m_load_plugin(plugin)
            except UserWarning as ex:
                self.logger.warning(f"error loading plugin {plugin}: '{ex}'")
                raise ex

    def enter_operational(self):
        """Enter operational stage."""
        # broadcast event to plugin system
        event = HbusMasterEvent(HbusMasterEventType.eventOperational)
        self.pluginManager.m_evt_broadcast(event)

    def get_information_data(self):
        """Get master information."""
        busses = list(
            set(
                [
                    slave.hbusSlaveAddress.bus_number
                    for slave in list(self.detectedSlaveList.values())
                    if slave.basicInformationRetrieved == True
                ]
            )
        )

        if len(self.virtualDeviceList) > 0:
            busses.append(VIRTUAL_BUS)

        return HbusMasterInformationData(len(self.detectedSlaveList), busses)

    def serial_create(self, fake=False):
        """Create serial port."""
        raise NotImplementedError

    def serial_connected(self):
        """Connect serial port callback."""
        # reset all devices
        self.logger.debug("Connected. Resetting all devices now")

        address = HbusDeviceAddress(
            self.hbusMasterAddr.bus_number, HBUS_BROADCAST_ADDRESS
        )

        size = HBUS_SIGNATURE_SIZE + 1

        myParamList = [bytes([size])]

        msg = struct.pack(
            "cccccc",
            bytes([self.hbusMasterAddr.bus_number]),
            bytes([self.hbusMasterAddr.dev_number]),
            bytes([address.bus_number]),
            bytes([address.dev_number]),
            bytes([HBUSCOMMAND_SOFTRESET.cmd_byte]),
            bytes([size]),
        )

        sig = hbussd.hbus.crypto.RabinWilliamsSign(
            msg,
            HBUS_ASYMMETRIC_KEYS.privatep,
            HBUS_ASYMMETRIC_KEYS.privateq,
            HBUS_SIGNATURE_SIZE,
        )

        myParamList.extend(sig.getByteString())

        self._push_command(HBUSCOMMAND_SOFTRESET, address, params=myParamList)

        self.logger.debug("Waiting for device RESET to complete...")

        # signal.alarm(1)
        reactor.callLater(1, self._alarm)  # @UndefinedVariable

        # self.detectSlaves()
        self._rx_enter_idle()

    def serial_write(self, string):
        """Write to serial port."""
        raise NotImplementedError

    def _serial_timeout(self):
        """Flag timeout in communication."""
        self.logger.warning("Packet receive timeout")
        self.logger.debug("packet dump: %s", self.communicationBuffer)

        self._rx_enter_idle()

    def _rx_enter_idle(self):
        """Enter idle state in RX state machine."""
        self.communicationBuffer = []

        self.hbusRxState = HbusRXState.SBID

        if len(self.outgoingCommands) > 0:
            d = self.outgoingCommands.pop()
            d.callback(None)

    def _rx_new_data(self, data):
        """Receive new data."""
        for d in data:

            self.rxBytes += 1

            if self.hbusRxState == HbusRXState.SBID:

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.SDID

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.SDID:

                self.RXTimeout.cancel()

                # check address
                if (d > 32) and (d != 255):
                    self._rx_enter_idle()

                    self.logger.debug("Invalid address in received packet")
                    return

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.TBID

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.TBID:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.TDID

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.TDID:

                self.RXTimeout.cancel()

                # check address
                if (d > 32) and (d != 255):
                    self._rx_enter_idle()

                    self.logger.debug("Invalid address in received packet")
                    return

                self.communicationBuffer.append(d)

                self.hbusRxState = HbusRXState.CMD

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.CMD:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                if (
                    d == HBUSCOMMAND_ACK.cmd_byte
                    or d == HBUSCOMMAND_SEARCH.cmd_byte
                    or d == HBUSCOMMAND_BUSLOCK.cmd_byte
                    or d == HBUSCOMMAND_BUSUNLOCK.cmd_byte
                    or d == HBUSCOMMAND_SOFTRESET.cmd_byte
                ):
                    self.hbusRxState = HbusRXState.STP
                else:
                    self.hbusRxState = HbusRXState.ADDR

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.ADDR:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                if (
                    self.communicationBuffer[4] == HBUSCOMMAND_GETCH.cmd_byte
                    or self.communicationBuffer[4]
                    == HBUSCOMMAND_QUERY.cmd_byte
                    or self.communicationBuffer[4]
                    == HBUSCOMMAND_QUERY_EP.cmd_byte
                    or self.communicationBuffer[4]
                    == HBUSCOMMAND_QUERY_INT.cmd_byte
                ):
                    self.hbusRxState = HbusRXState.STP
                else:
                    self.hbusRxState = HbusRXState.PSZ

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.PSZ:

                self.RXTimeout.cancel()

                if (
                    self.communicationBuffer[4] != HBUSCOMMAND_STREAMW.cmd_byte
                    and self.communicationBuffer[4]
                    != HBUSCOMMAND_STREAMR.cmd_byte
                ):
                    if d > 64:
                        d = chr(64)

                self.communicationBuffer.append(d)
                self.lastPacketParamSize = d

                if (
                    self.communicationBuffer[4] == HBUSCOMMAND_STREAMW.cmd_byte
                    or self.communicationBuffer[4]
                    == HBUSCOMMAND_STREAMR.cmd_byte
                ):
                    self.hbusRxState = HbusRXState.STP
                else:
                    if d > 0:
                        self.hbusRxState = HbusRXState.PRM
                    else:
                        self.hbusRxState = HbusRXState.STP

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.PRM:

                self.RXTimeout.cancel()

                if len(self.communicationBuffer) <= (
                    6 + self.lastPacketParamSize
                ):
                    self.communicationBuffer.append(d)
                else:

                    # self.hbusRxState = HbusRXState.STP
                    if d == 0xFF:
                        self.communicationBuffer.append(d)

                        dataToParse = self.communicationBuffer

                        self._rx_enter_idle()

                        self._parse_received_data(dataToParse)

                        return

                    else:
                        self.logger.debug(
                            "malformed packet, termination error"
                        )
                        self.logger.debug(
                            "packet dump: %s"
                            % [hex(ord(x)) for x in self.communicationBuffer]
                        )

                        self._rx_enter_idle()

                        return

                self.RXTimeout = reactor.callLater(
                    0.2, self._serial_timeout
                )  # @UndefinedVariable

            elif self.hbusRxState == HbusRXState.STP:

                self.RXTimeout.cancel()

                self.communicationBuffer.append(d)

                if d == 0xFF:

                    dataToParse = self.communicationBuffer

                    self._rx_enter_idle()

                    self._parse_received_data(dataToParse)

                    return

                else:
                    self.logger.debug("malformed packet, termination error")
                    self.logger.debug(
                        "packet dump: %s"
                        % [hex(ord(x)) for x in self.communicationBuffer]
                    )

                    self._rx_enter_idle()
                    return

            else:
                self.logger.error("Fatal error receiving HBUSOP")
                raise IOError("Fatal error receiving")

                self._rx_enter_idle()

                return

    @classmethod
    def find_command(cmdbyte):
        """Find HBUS command definition."""
        for c in HBUS_COMMANDLIST:
            if c.cmd_byte == cmdbyte:
                return c

        return None

    def get_new_address(self, uid):
        """Get address for new slave.

        @param uid slave's UID
        """
        UIDList = [
            x.hbusSlaveUniqueDeviceInfo
            for x in list(self.detectedSlaveList.values())
        ]
        addressList = [
            x.hbusSlaveAddress for x in list(self.detectedSlaveList.values())
        ]

        AddressByUID = dict(list(zip(UIDList, addressList)))

        # see if already registered at some point
        if uid in list(AddressByUID.keys()):
            return AddressByUID[uid].dev_number
            self.logger.debug("Re-integrating device with UID %s", hex(uid))
        else:
            return self.registeredSlaveCount + 1

    def get_new_virtual_address(self, uid):
        """Get address for new virtual slave."""
        uidList = [
            x.hbusSlaveUniqueDeviceInfo
            for x in list(self.virtualDeviceList.values())
        ]
        addressList = [
            x.hbusSlaveAddress for x in list(self.virtualDeviceList.values())
        ]
        addressByUid = dict(list(zip(uidList, addressList)))

        if uid in list(addressByUid.keys()):
            return addressByUid[uid].dev_number
        else:
            self.virtualSlaveCount += 1
            return HbusDeviceAddress(VIRTUAL_BUS, self.virtualSlaveCount)

    def _set_slave_capabilities(self, params):
        """Set slave capabilities."""
        self.logger.debug("enumerating new device")
        self.nextSlaveCapabilities = params[3]
        (self.nextSlaveUID,) = struct.unpack("I", bytes(params[4:8]))

        # get new address
        nextAddress = self.get_new_address(self.nextSlaveUID)

        if self.nextSlaveCapabilities & HbusDeviceCapabilities.AUTHSUP:
            self.logger.debug("New device has AUTH support")

        myParamList = [chr(HBUS_PUBKEY_SIZE)]
        myParamList.extend(HBUS_ASYMMETRIC_KEYS.pubKeyStr())

        # registers slave address with next available address
        if self.nextSlaveCapabilities & HbusDeviceCapabilities.AUTHSUP:
            self._push_command(
                HBUSCOMMAND_KEYSET,
                HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress),
                myParamList,
            )
        else:
            self._push_command(
                HBUSCOMMAND_SEARCH,
                HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress),
            )

        # update BUSLOCK state
        self.hbusBusLockedWith = HbusDeviceAddress(
            self.hbusMasterAddr.bus_number, nextAddress
        )

        # sends BUSUNLOCK immediately
        self._push_command(
            HBUSCOMMAND_BUSUNLOCK,
            HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress),
        )

        self.register_new_slave(
            HbusDeviceAddress(self.hbusMasterAddr.bus_number, nextAddress)
        )

        if nextAddress == (self.registeredSlaveCount + 1):
            self.registeredSlaveCount = self.registeredSlaveCount + 1

        self.masterState = HbusMasterState.hbusMasterSearching

    def _parse_received_data(self, data):
        """Parse received data and verify correctness."""
        selectedR = None

        if len(data) < 7:
            pSize = 0
            params = ()
        else:
            pSize = data[6]
            params = data[7 : 7 + data[6]]

        try:
            busOp = HbusOperation(
                HbusInstruction(self.find_command(data[4]), pSize, params),
                HbusDeviceAddress(data[2], data[3]),
                HbusDeviceAddress(data[0], data[1]),
            )
        except ValueError:

            self.logger.warning("Invalid packet was received")
            return

        if busOp.source.dev_number == 0:
            self.logger.debug("Illegal packet ignored: reserved addres")
            return

        # very slow!!!
        # self.logger.debug(busOp)
        # print busOp

        if busOp.destination == self.hbusMasterAddr:

            if busOp.instruction.command == HBUSCOMMAND_BUSLOCK:
                self.hbusBusState = HbusBusState.LOCKED_THIS
                self.hbusBusLockedWith = busOp.source
                self.nextSlaveCapabilities = None
                self.nextSlaveUID = None

                self.logger.debug(
                    "received BUSLOCK from {}".format(busOp.source)
                )
                # exception: buslock from (x,255)
                if (
                    busOp.source.dev_number == HBUS_BROADCAST_ADDRESS
                    and self.masterState
                    in [
                        HbusMasterState.hbusMasterSearching,
                        HbusMasterState.hbusMasterChecking,
                    ]
                ):

                    self._push_command(
                        HBUSCOMMAND_GETCH,
                        HbusDeviceAddress(
                            self.hbusMasterAddr.bus_number,
                            HBUS_BROADCAST_ADDRESS,
                        ),
                        params=[0],
                        callBack=self._set_slave_capabilities,
                    )

                    self.masterState = HbusMasterState.hbusMasterAddressing

            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:
                self.logger.debug(
                    "received BUSUNLOCK from {}".format(busOp.source)
                )
                self.hbusBusState = HbusBusState.FREE
                self.hbusBusLockedWith = None

                self._bus_free()

            # Interrupts
            elif busOp.instruction.command == HBUSCOMMAND_INT:
                self.logger.debug("received INT from {}".format(busOp.source))
                self.masterState = HbusMasterState.hbusMasterInterrupted

                # Process
                # TODO: missing interrupt mechanisms for master special objects subsystem implementation

            if len(self.expectedResponseQueue) > 0:

                selectedR = None
                for r in self.expectedResponseQueue:

                    if r in self.removeQueue:
                        continue

                    if (
                        r.source == busOp.source
                        and r.command == busOp.instruction.command
                    ):

                        selectedR = r
                        r.cancel_timeout_handler()
                        self.removeQueue.append(r)
                        break

            if selectedR is not None:
                if selectedR.actionParameters is not None:
                    selectedR.dCallback.callback(
                        (selectedR.actionParameters, busOp.instruction.params)
                    )
                else:
                    selectedR.dCallback.callback(busOp.instruction.params)
        else:

            if busOp.instruction.command == HBUSCOMMAND_BUSLOCK:

                self.hbusBusState = HbusBusState.LOCKED_OTHER

            elif busOp.instruction.command == HBUSCOMMAND_BUSUNLOCK:

                self.hbusBusState = HbusBusState.FREE
                self.hbusBusLockedWith = None

                self._bus_free()

    def _push_command(
        self,
        command,
        dest,
        params=(),
        callBack=None,
        callBackParams=None,
        timeout=1000,
        timeoutCallBack=None,
        timeoutCallBackParams=None,
        immediate=False,
        deferredReturn=None,
    ):
        """Push command into outgoing queue."""
        d = None
        if self.hbusRxState != HbusRXState.SBID and immediate is False:
            d = defer.Deferred()
            d.addCallback(
                self._push_command,
                command,
                dest,
                params,
                callBack,
                callBackParams,
                timeout,
                timeoutCallBack,
                timeoutCallBackParams,
            )
            self.outgoingCommands.appendleft(d)

            return d
        else:
            if callBack is not None:
                try:
                    d = self._expect_response(
                        HBUS_RESPONSEPAIRS[command],
                        dest,
                        action=callBack,
                        actionParameters=callBackParams,
                        timeout=timeout,
                        timeoutAction=timeoutCallBack,
                        timeoutActionParameters=timeoutCallBackParams,
                    )
                except:
                    d = None

            elif timeoutCallBack is None:

                try:
                    d = self._expect_response(
                        HBUS_RESPONSEPAIRS[command],
                        dest,
                        None,
                        None,
                        timeout,
                        timeoutCallBack,
                        timeoutCallBackParams,
                    )
                except:
                    d = None

            self.lastSent = (command, dest, params)
            self._send_command(command, dest, params)

            return d

    def _send_command(self, command, dest, params=(), block=False):
        """Send the actual complete command."""
        # warning: blocking
        if block:
            while self.hbusRxState != 0:
                time.sleep(0.01)

        busOp = HbusOperation(
            HbusInstruction(command, len(params), params),
            dest,
            self.hbusMasterAddr,
        )

        # very slow!!
        # self.logger.debug(busOp)

        if command == HBUSCOMMAND_BUSLOCK:

            self.hbusBusState = HbusBusState.LOCKED_THIS
            self.hbusBusLockedWith = dest

        elif command == HBUSCOMMAND_BUSUNLOCK:

            if (
                self.hbusBusState == HbusBusState.LOCKED_THIS
                and self.hbusBusLockedWith == dest
            ):

                self.hbusBusState = HbusBusState.FREE
                self.hbusBusLockedWith = None
                self._bus_free()

            else:

                self.logger.debug(
                    "BUSUNLOCK error: locked with %s, tried unlocking %s"
                    % (self.hbusBusLockedWith, dest)
                )

        op_str = busOp.get_packed()
        self.txBytes += len(op_str)
        if self.masterState == HbusMasterState.hbusMasterScanning:
            reactor.callFromThread(
                self.serial_write, op_str
            )  # @UndefinedVariable
        else:
            self.serial_write(op_str)

    def _expect_response(
        self,
        command,
        source,
        action=None,
        actionParameters=None,
        timeout=1000,
        timeoutAction=None,
        timeoutActionParameters=None,
    ):
        """Expect a response to an outgoing command."""
        d = defer.Deferred()

        d.addCallback(action)
        d.addErrback(timeoutAction)

        pending = HbusPendingAnswer(
            command,
            source,
            timeout,
            d,
            actionParameters,
            timeoutAction,
            timeoutActionParameters,
        )

        # timeout handler
        timeoutHandler = reactor.callLater(
            timeout / 1000, self._response_timeout, pending
        )  # @UndefinedVariable
        pending.timeout_handler = timeoutHandler

        self.expectedResponseQueue.append(pending)

        return d

    def register_new_slave(self, address, slaveInfo=None):
        """Register new device in the bus.

        @param address device address
        @param slaveInfo for virtual devices, complete description
        """
        if slaveInfo is not None:
            if slaveInfo.hbusSlaveIsVirtual:
                # virtual device
                # doesn't know virtual bus number
                addr = HbusDeviceAddress(VIRTUAL_BUS, address)
                slaveInfo.hbusSlaveAddress = addr
                self.virtualDeviceList[addr.global_id] = slaveInfo
            else:
                # not supported
                raise UserWarning(
                    "adding pre-formed real device not supported"
                )
                return
        else:
            self.detectedSlaveList[address.global_id] = HbusDevice(address)

        self.logger.info("New device registered at " + str(address))
        self.logger.debug("New device UID is " + str(address.global_id))

        # self.readBasicSlaveInformation(address)

    def unregister_slave(self, address, virtual=False):
        """Unregister slave by address."""
        if virtual == True:
            del self.virtualDeviceList[
                hbusSlaveAddress(VIRTUAL_BUS, address).global_id
            ]
        else:
            del self.detectedSlaveList[address.global_id]

        self.logger.info("Device at " + str(address) + " removed")

    def _slave_read_start(self):
        """Start reading slave definition."""
        try:
            self.slaveReadDeferred.callback(None)
        except defer.AlreadyCalledError:
            pass

    def _slave_read_end(self, callBackResult):
        """Slave definition retrieval ended."""
        # self.logger.debug("Device information retrieval ended.")

        # self.slaveReadDeferred = None

        self.masterState = HbusMasterState.hbusMasterOperational
        # reactor.callInThread(self.processHiddenObjects)
        self.logger.info("Device information retrieval finished.")
        self.logger.debug("tx: %d, rx %d bytes", self.txBytes, self.rxBytes)

        self.enter_operational()

    def _slave_basic_read_end(self, *params):
        """Slave basic definition retrieval ended."""
        d = defer.Deferred()
        d.addCallback(self._slave_read_ext)

        if params[0].global_id == list(self.detectedSlaveList.keys())[-1]:
            self.slaveReadDeferred.addCallback(self._slave_read_end)

        reactor.callLater(0.1, d.callback, *params)  # @UndefinedVariable

        return d

    def _slave_read_object_fail(self, params):
        """Slave object read failed callback."""
        self.logger.warning("Failure while analyzing device")

        self.slaveScanDeferred.errback(
            IOError("Failure while analyzing device")
        )

    def _slave_basic_read_fail(self, *params):
        """Slave basic read has failed."""
        (
            failure,
            address,
        ) = params

        # try again at enumeration end
        if self.detectedSlaveList[address.global_id].scanRetryCount < 3:
            self.slaveReadDeferred.addCallback(self._slave_read_basic, address)
            self.detectedSlaveList[address.global_id].scanRetryCount += 1
        else:
            if address.global_id == list(self.detectedSlaveList.keys())[-1]:
                self.slaveReadDeferred.addCallback(self._slave_read_end)

    def _slave_ext_read_end(self, *params):
        """Slave extended information retrieval ended."""
        result, address = params

        self.detectedSlaveList[address.global_id].hbusSlaveHiddenObjects = None

    def _slave_ext_read_fail(self, *params):
        """Slave extended retrieval failed."""
        (
            failure,
            address,
        ) = params

        # if self.detectedSlaveList[address.global_id].scanRetryCount < 3:
        #    self.slaveHiddenDeferred.addCallback(self.readExtendedSlaveInformation,address)
        #    self.detectedSlaveList[address.global_id].scanRetryCount += 1

    def _slave_read_ext(self, *params):
        self.logger.debug("Invisible objects being processed now")

        address = params[0]

        if address is None:
            address = params[1]

        self.detectedSlaveList[address.global_id].scanRetryCount = 0

        d = defer.Deferred()

        for obj in list(
            self.detectedSlaveList[
                address.global_id
            ].hbusSlaveHiddenObjects.keys()
        ):
            d.addCallback(self._slave_hidden_object_read, address, obj)
            d.addCallback(self._slave_process_hidden_obj, address, obj)

        d.addCallback(self._slave_ext_read_end, address)
        d.addErrback(self._slave_ext_read_fail, address)
        self.slaveHiddenDeferred = d

        # inicia
        reactor.callLater(0.1, d.callback, None)  # @UndefinedVariable

        return d

    def _slave_process_hidden_obj(self, deferredResult, address, objectNumber):
        """Process hidden object."""
        obj = self.detectedSlaveList[address.global_id].hbusSlaveHiddenObjects[
            objectNumber
        ]
        slave = self.detectedSlaveList[address.global_id]

        objFunction = obj.description.split(":")
        objList = objFunction[0].split(",")

        for objSel in objList:
            x = re.match(r"([0-9]+)-([0-9]+)", objSel)

            if x is not None:
                for rangeObj in range(int(x.group(1)), int(x.group(2)) + 1):

                    if (
                        slave.hbusSlaveObjects[rangeObj].objectExtendedInfo
                        is None
                    ):
                        slave.hbusSlaveObjects[
                            rangeObj
                        ].objectExtendedInfo = {}

                        slave.hbusSlaveObjects[rangeObj].objectExtendedInfo[
                            objFunction[1]
                        ] = obj.last_value

            else:
                if (
                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo
                    is None
                ):
                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo = {}

                    slave.hbusSlaveObjects[int(objSel)].objectExtendedInfo[
                        objFunction[1]
                    ] = obj.last_value

    # TODO: this method is horrible
    def _slave_read_basic(self, deferResult, address):
        """Read basic slave information."""
        self.logger.debug(
            "Initializing device analysis " + str(address.global_id)
        )

        d = defer.Deferred()
        d.addCallback(self._slave_basic_read_end)
        d.addErrback(self._slave_basic_read_fail, address)
        self.slaveScanDeferred = d

        self.detectedSlaveList[address.global_id].readEndedCallback = d
        self.detectedSlaveList[address.global_id].readEndedParams = address

        # BUSLOCK
        # self.sendCommand(HBUSCOMMAND_BUSLOCK,address)

        # self.expectResponse(HBUSCOMMAND_QUERY_RESP,address,self.receiveSlaveInformation,actionParameters=("Q",address))
        self._push_command(
            HBUSCOMMAND_QUERY,
            address,
            params=[0],
            callBack=self._slave_receive,
            callBackParams=("Q", address),
            timeoutCallBack=self._slave_read_object_fail,
        )

        return d

    def _slave_receive(self, data):
        """Receive slave information."""
        self.logger.debug("in receiveSlaveInformation; {}".format(data[0][0]))
        if data[0][0] == "Q":

            self.detectedSlaveList[
                data[0][1].global_id
            ].hbusSlaveDescription = bytes(data[1][4::]).decode("ascii")

            # read device's objects information
            # self.expectResponse(HBUSCOMMAND_RESPONSE,data[0][1],self.receiveSlaveInformation,actionParameters=("V",data[0][1]))
            self._push_command(
                HBUSCOMMAND_GETCH,
                data[0][1],
                params=[0],
                callBack=self._slave_receive,
                callBackParams=("V", data[0][1]),
                timeoutCallBack=self._slave_read_object_fail,
            )

        elif data[0][0] == "V":

            self.detectedSlaveList[
                data[0][1].global_id
            ].hbusSlaveObjectCount = data[1][0]

            self.detectedSlaveList[
                data[0][1].global_id
            ].hbusSlaveEndpointCount = data[1][1]

            self.detectedSlaveList[
                data[0][1].global_id
            ].hbusSlaveInterruptCount = data[1][2]

            self.detectedSlaveList[
                data[0][1].global_id
            ].hbusSlaveCapabilities = data[1][3]

            # capabilities
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveHasAUTH = (
                True if data[1][3] & HbusDeviceCapabilities.AUTHSUP else False
            )
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveHasCRYPTO = (
                True
                if data[1][3] & HbusDeviceCapabilities.CRYPTOSUP
                else False
            )
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveHasEP = (
                True if data[1][3] & HbusDeviceCapabilities.EPSUP else False
            )
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveHasINT = (
                True if data[1][3] & HbusDeviceCapabilities.INTSUP else False
            )
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveHasUCODE = (
                True if data[1][3] & HbusDeviceCapabilities.UCODESUP else False
            )
            self.detectedSlaveList[
                data[0][1].global_id
            ].hbusSlaveHasREVAUTH = (
                True
                if data[1][3] & HbusDeviceCapabilities.REVAUTHSUP
                else False
            )

            (
                self.detectedSlaveList[
                    data[0][1].global_id
                ].hbusSlaveUniqueDeviceInfo,
            ) = struct.unpack("I", bytes(data[1][4:8]))

            # self.detectedSlaveList[data[0][1].global_id].basicInformationRetrieved = True

            self.logger.info(
                "Device at "
                + str(data[0][1])
                + " identified as "
                + str(
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveDescription
                )
                + "("
                + str(data[1][0])
                + ","
                + str(data[1][1])
                + ","
                + str(data[1][2])
                + ") <"
                + str(
                    hex(
                        self.detectedSlaveList[
                            data[0][1].global_id
                        ].hbusSlaveUniqueDeviceInfo
                    )
                )
                + ">"
            )

            self.logger.debug(
                "Retrieving device's objects information "
                + str(data[0][1].global_id)
            )

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects = {}

            # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
            self._push_command(
                HBUSCOMMAND_QUERY,
                data[0][1],
                params=[1],
                callBack=self._slave_receive,
                callBackParams=("O", data[0][1]),
                timeoutCallBack=self._slave_read_object_fail,
            )

        elif data[0][0] == "O":

            currentObject = (
                len(
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveObjects
                )
                + 1
            )

            self.logger.debug(
                "Analysing object "
                + str(currentObject)
                + ", in device with ID "
                + str(data[0][1].global_id)
            )

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                currentObject
            ] = HbusDeviceObject()
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                currentObject
            ].permissions = (data[1][0] & 0x03)

            if data[1][0] & 0x04:
                self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                    currentObject
                ].is_crypto = True

            if data[1][0] & 0x08:
                self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                    currentObject
                ].hidden = True

            if data[1][0] & 0x30 == 0:
                self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                    currentObject
                ].objectDataType = HbusObjDataType.dataTypeInt
            else:
                self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                    currentObject
                ].objectDataType = (data[1][0] & 0x30)

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                currentObject
            ].objectLevel = (data[1][0] & 0xC0) >> 6

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                currentObject
            ].size = data[1][1]

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                currentObject
            ].objectDataTypeInfo = data[1][2]

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveObjects[
                currentObject
            ].description = "".join(bytes(data[1][4::]).decode("ascii"))

            if (
                currentObject + 1
                < self.detectedSlaveList[
                    data[0][1].global_id
                ].hbusSlaveObjectCount
            ):

                # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("O",data[0][1]))
                self._push_command(
                    HBUSCOMMAND_QUERY,
                    data[0][1],
                    params=[currentObject + 1],
                    callBack=self._slave_receive,
                    callBackParams=("O", data[0][1]),
                    timeoutCallBack=self._slave_read_object_fail,
                )
            else:

                # RECEIVES ENDPOINT INFO
                if (
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveEndpointCount
                    > 0
                ):

                    self.logger.debug(
                        "Retrieving device's endpoints information "
                        + str(data[0][1].global_id)
                    )

                    # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                    self._push_command(
                        HBUSCOMMAND_QUERY_EP,
                        data[0][1],
                        params=[0],
                        callBack=self._slave_receive,
                        callBackParams=("E", data[0][1]),
                    )

                elif (
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveInterruptCount
                    > 0
                ):

                    self.logger.debug(
                        "Retrieving device's interrupts information "
                        + str(data[0][1].global_id)
                    )

                    # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self._push_command(
                        HBUSCOMMAND_QUERY_INT,
                        data[0][1],
                        params=[0],
                        callBack=self._slave_receive,
                        callBackParams=("I", data[0][1]),
                        timeoutCallBack=self._slave_read_object_fail,
                    )

                else:
                    # self.pushCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug(
                        "Analysis of device "
                        + str(data[0][1].global_id)
                        + " finished"
                    )
                    # self.processHiddenObjects(self.detectedSlaveList[data[0][1].global_id])
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].basicInformationRetrieved = True

                    self.detectedSlaveList[data[0][1].global_id].sortObjects()

                    if (
                        self.detectedSlaveList[
                            data[0][1].global_id
                        ].readEndedCallback
                        is not None
                    ):
                        reactor.callLater(
                            HBUS_SLAVE_QUERY_INTERVAL,
                            self.detectedSlaveList[
                                data[0][1].global_id
                            ].readEndedCallback.callback,
                            self.detectedSlaveList[
                                data[0][1].global_id
                            ].readEndedParams,
                        )  # @UndefinedVariable

        elif data[0][0] == "E":

            # ENDPOINTS

            currentEndpoint = (
                len(
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveEndpoints
                )
                + 1
            )

            self.logger.debug(
                "Analysing endpoint "
                + str(currentEndpoint)
                + ", device with ID "
                + str(data[0][1].global_id)
            )

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveEndpoints[
                currentEndpoint
            ] = HbusEndpoint()
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveEndpoints[
                currentEndpoint
            ].endpointDirection = ord(data[1][0])
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveEndpoints[
                currentEndpoint
            ].endpointBlockSize = ord(data[1][1])

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveEndpoints[
                currentEndpoint
            ].endpointDescription = "".join(data[1][3::])

            if (
                currentEndpoint + 1
                < self.detectedSlaveList[
                    data[0][1].global_id
                ].hbusSlaveEndpointCount
            ):

                # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("E",data[0][1]))
                self._push_command(
                    HBUSCOMMAND_QUERY_EP,
                    data[0][1],
                    params=[currentEndpoint + 1],
                    callBack=self._slave_receive,
                    callBackParams=("E", data[0][1]),
                    timeoutCallBack=self._slave_read_object_fail,
                )

            else:

                # INTERRUPT INFO
                if (
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveInterruptCount
                    > 0
                ):

                    self.logger.debug(
                        "Retrieving device's endpoints information "
                        + str(data[0][1].global_id)
                    )

                    # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                    self._push_command(
                        HBUSCOMMAND_QUERY_INT,
                        data[0][1],
                        params=[0],
                        callBack=self._slave_receive,
                        callBackParams=("I", data[0][1]),
                        timeoutCallBack=self._slave_read_object_fail,
                    )

                else:
                    # self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                    self.logger.debug(
                        "Analysis of device "
                        + str(data[0][1].global_id)
                        + " finished"
                    )
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].basicInformationRetrieved = True

                    self.detectedSlaveList[data[0][1].global_id].sortObjects()

                    if (
                        self.detectedSlaveList[
                            data[0][1].global_id
                        ].readEndedCallback
                        is not None
                    ):
                        reactor.callLater(
                            HBUS_SLAVE_QUERY_INTERVAL,
                            self.detectedSlaveList[
                                data[0][1].global_id
                            ].readEndedCallback.callback,
                            self.detectedSlaveList[
                                data[0][1].global_id
                            ].readEndedParams,
                        )  # @UndefinedVariable

        elif data[0][0] == "I":

            # INTERRUPTS

            currentInterrupt = (
                len(
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].hbusSlaveInterrupts
                )
                + 1
            )

            self.logger.debug(
                "Analyzing interrupt "
                + str(currentInterrupt)
                + ", device ID "
                + str(data[0][1].global_id)
            )

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveInterrupts[
                currentInterrupt
            ] = HbusInterrupt()
            self.detectedSlaveList[data[0][1].global_id].hbusSlaveInterrupts[
                currentInterrupt
            ].interruptFlags = ord(data[1][0])

            self.detectedSlaveList[data[0][1].global_id].hbusSlaveInterrupts[
                currentInterrupt
            ].interruptDescription = "".join(data[1][2::])

            if (
                currentInterrupt + 1
                < self.detectedSlaveList[
                    data[0][1].global_id
                ].hbusSlaveInterruptCount
            ):

                # self.expectResponse(HBUSCOMMAND_QUERY_RESP,data[0][1],self.receiveSlaveInformation,actionParameters=("I",data[0][1]))
                self._push_command(
                    HBUSCOMMAND_QUERY_INT,
                    data[0][1],
                    params=[currentInterrupt + 1],
                    callBack=self._slave_receive,
                    callBackParams=("I", data[0][1]),
                    timeoutCallBack=self._slave_read_object_fail,
                )

            else:
                # self.sendCommand(HBUSCOMMAND_BUSUNLOCK,data[0][1])
                self.logger.debug(
                    "device analysis "
                    + str(data[0][1].global_id)
                    + " finished"
                )
                # self.processHiddenObjects(self.detectedSlaveList[data[0][1].global_id])
                self.detectedSlaveList[
                    data[0][1].global_id
                ].basicInformationRetrieved = True

                self.detectedSlaveList[data[0][1].global_id].sortObjects()

                if (
                    self.detectedSlaveList[
                        data[0][1].global_id
                    ].readEndedCallback
                    is not None
                ):
                    reactor.callLater(
                        HBUS_SLAVE_QUERY_INTERVAL,
                        self.detectedSlaveList[
                            data[0][1].global_id
                        ].readEndedCallback.callback,
                        self.detectedSlaveList[
                            data[0][1].global_id
                        ].readEndedParams,
                    )  # @UndefinedVariable

        elif data[0][0] == "D":

            # info dump
            pass

    def _slave_object_read(
        self, address, number, callBack=None, timeoutCallback=None
    ):
        """Read slave object."""
        d = None

        # see if this is a virtual device first
        if address.bus_number == VIRTUAL_BUS:
            # read and update
            result = self.pluginManager.m_read_vdev_obj(
                address.dev_number, number
            )
            self.virtualDeviceList[address.global_id].hbusSlaveObjects[
                number
            ].last_value = result

            if callBack is not None:
                callBack(result)
            return

        if (
            self.detectedSlaveList[address.global_id]
            .hbusSlaveObjects[number]
            .permissions
            != HbusObjectPermissions.WRITE
        ):

            d = self._push_command(
                HBUSCOMMAND_GETCH,
                address,
                params=[chr(number)],
                callBack=self._slave_obj_data_rx,
                callBackParams=(address, number, callBack),
                timeoutCallBack=timeoutCallback,
            )

        else:

            self.logger.warning("Write-only object read attempted")
            self.logger.debug(
                "Tried reading object %d of slave with address %s",
                number,
                address,
            )
            raise IOError("cannot read write-only object")

            if callBack is not None:
                callBack(None)

        return d

    def _slave_hidden_object_read(self, *params):
        """Read hidden object."""
        if isinstance(params[0], HbusDeviceAddress):
            address = params[0]
            number = params[1]
        elif isinstance(params[1], HbusDeviceAddress):
            address = params[1]
            number = params[2]
        else:
            raise ValueError("")

        d = None

        if (
            self.detectedSlaveList[address.global_id]
            .hbusSlaveHiddenObjects[number]
            .permissions
            != HbusObjectPermissions.WRITE
        ):

            # self.expectResponse(HBUSCOMMAND_RESPONSE,address,self.receiveSlaveObjectData,actionParameters=(address,number,callBack),timeoutAction=timeoutCallback)
            # self.pushCommand(HBUSCOMMAND_GETCH,address,params=[chr(number)],callBack=self.receiveSlaveObjectData,callBackParams=(address,number,callBack))
            d = self._push_command(
                HBUSCOMMAND_GETCH,
                address,
                params=[chr(number)],
                callBack=self._slave_hidden_obj_data_rx,
                callBackParams=(address, number, None),
                timeoutCallBack=None,
            )

        else:

            self.logger.warning("Write-only object read attempted")
            self.logger.debug(
                "Tried reading object %d of slave with address %s",
                number,
                address,
            )

            # if callBack is not None:
            #    callBack(None)

        return d

    def _slave_obj_data_rx(self, data):
        """Receive object data."""
        self.detectedSlaveList[data[0][0].global_id].hbusSlaveObjects[
            data[0][1]
        ].last_value = data[1][:]
        if data[0][2] is not None:
            data[0][2](data[1])

    def _slave_hidden_obj_data_rx(self, data):
        """Receive hidden object data."""
        self.detectedSlaveList[data[0][0].global_id].hbusSlaveHiddenObjects[
            data[0][1]
        ].last_value = data[1][:]

        if data[0][2] is not None:
            data[0][2](data[1])

    def _slave_object_write(self, address, number, value):
        """Write slave object."""
        # check if is virtual bus
        if address.bus_number == VIRTUAL_BUS:
            self.virtualDeviceList[address.global_id].hbusSlaveObjects[
                number
            ].last_value = value
            self.pluginManager.m_write_vdev_obj(
                address.dev_number, number, value
            )
            return True

        if (
            self.detectedSlaveList[address.global_id]
            .hbusSlaveObjects[number]
            .permissions
            != HbusObjectPermissions.READ
        ):

            self.detectedSlaveList[address.global_id].hbusSlaveObjects[
                number
            ].last_value = value
            size = (
                self.detectedSlaveList[address.global_id]
                .hbusSlaveObjects[number]
                .size
            )

            myParamList = [number, size]
            if isinstance(value, list):
                # truncate value passed to length
                if len(value) > size:
                    self.logger.warning(
                        "writeSlaveObject: passed a value with incorrect length of {}, truncating".format(
                            len(value)
                        )
                    )
                    value = value[0:size]
                myParamList.extend(value)
            else:
                # extend integer value up to object's size
                byte_list = []
                for i in range(0, size):
                    byte_list.append((value & (0xFF) << (8 * i)) >> 8 * i)
                myParamList.extend(byte_list)

            if (
                self.detectedSlaveList[address.global_id].hbusSlaveCapabilities
                & HbusDeviceCapabilities.AUTHSUP
            ):

                myParamList[1] += HBUS_SIGNATURE_SIZE + 1

                msg = struct.pack(
                    "ccccccc",
                    chr(self.hbusMasterAddr.bus_number),
                    chr(self.hbusMasterAddr.dev_number),
                    chr(address.bus_number),
                    chr(address.dev_number),
                    chr(HBUSCOMMAND_SETCH.cmd_byte),
                    chr(number),
                    chr(myParamList[1]),
                )

                i = 0
                while size > 0:
                    struct.pack_into("c", msg, 7 + i, value[i])

                    size -= 1
                    i += 1

                sig = hbus_crypto.hbusCrypto_RabinWilliamsSign(
                    msg,
                    HBUS_ASYMMETRIC_KEYS.privatep,
                    HBUS_ASYMMETRIC_KEYS.privateq,
                )

                myParamList.extend(sig.getByteString())

            self._push_command(HBUSCOMMAND_SETCH, address, params=myParamList)

        else:
            return False
            self.logger.warning("attempted to write to a read-only object")

        return True

    def _slave_object_write_fmt(self, address, number, value):
        """Write slave object with formatted data."""
        # decode formatting and write data to object
        if address.bus_number == VIRTUAL_BUS:
            obj = self.virtualDeviceList[address.global_id].hbusSlaveObjects[
                number
            ]
        else:
            obj = self.detectedSlaveList[address.global_id].hbusSlaveObjects[
                number
            ]

        data = HBUS_DTYPE_OPTIONS[obj.objectDataType][obj.objectDataTypeInfo](
            data=value,
            extinfo=obj.objectExtendedInfo,
            decode=True,
            size=obj.size,
        )

        self._slave_object_write(address, number, data)

    def _slave_ping(
        self, callback, address, successCallback=None, failureCallback=None
    ):
        """Ping slave."""
        if successCallback is None:
            successCallback = self._slave_pong

        if failureCallback is None:
            failureCallback = self._slave_pong_fail

        d = self._push_command(
            HBUSCOMMAND_SEARCH,
            address,
            callBack=successCallback,
            callBackParams=address,
            timeout=3000,
            timeoutCallBack=failureCallback,
            timeoutCallBackParams=address,
        )

        return d

    def _deferred_delay(self, time):
        """Deferred delay."""
        d = defer.Deferred()
        d.addCallback(self._nop_callback)

        reactor.callLater(time, d.callback, None)  # @UndefinedVariable

        return d

    def _nop_callback(self, *params):
        """Do nothing."""

    def _slave_pong(self, *params):
        """Handle slave response to ping."""
        address = params[0][0]

        if address.global_id not in list(self.detectedSlaveList.keys()):
            if address in self.staticSlaveList:
                self.logger.info("Device with static address present")
                self.register_new_slave(address)

        if self.detectedSlaveList[address.global_id].pingRetryCount > 0:
            self.detectedSlaveList[address.global_id].pingRetryCount = 0
            self.detectedSlaveList[address.global_id].pingFailures += 1

        return self._deferred_delay(0.1)

    def _slave_pong_fail(self, *params):
        """Handle slave ping failure."""
        address = params[0].value.args[0]

        if address.global_id in list(self.detectedSlaveList.keys()):

            if self.detectedSlaveList[address.global_id].pingRetryCount < 3:
                self.detectedSlaveList[address.global_id].pingRetryCount += 1
            else:
                self.logger.warning(
                    "Removing device from bus for unresponsiveness"
                )
                self.unregister_slave(address)
        else:
            # this is a static device
            pass

        return self._deferred_delay(0.1)

    def _slave_detect(self, callBack=None, allBusses=False):
        """Detect active slaves."""
        self._push_command(
            HBUSCOMMAND_SEARCH,
            HbusDeviceAddress(self.hbusMasterAddr.bus_number, 255),
        )

        if self.masterState == HbusMasterState.hbusMasterOperational:
            self.masterState = HbusMasterState.hbusMasterChecking
        else:
            self.masterState = HbusMasterState.hbusMasterSearching
            self.logger.info("Starting device search")

        reactor.callLater(5, self._alarm)  # @UndefinedVariable

        self.detectSlavesEnded = callBack

    def slave_verify(self):
        """Verify that detected slaves data has been retrieved."""
        d = defer.Deferred()

        # enumerated devices
        for slave in list(self.detectedSlaveList.values()):

            if slave.hbusSlaveAddress in self.staticSlaveList:
                continue

            d.addCallback(self._slave_ping, slave.hbusSlaveAddress)

        # static devices
        for address in self.staticSlaveList:
            d.addCallback(self._slave_ping, address)

        d.addCallback(self._slave_get_missing)

        # new devices
        d.addCallback(self._slave_detect)

        # starts callback chain (deferred chain)
        d.callback(None)

    def _slave_get_missing(self, callbackResult):
        """Get missing information from slaves."""
        d = defer.Deferred()

        for slave in list(self.detectedSlaveList.values()):
            if slave.basicInformationRetrieved is False:
                d.addCallback(self._slave_read_basic, slave.hbusSlaveAddress)

        self.slaveReadDeferred = d
        reactor.callLater(0.1, self._slave_read_start)  # @UndefinedVariable

        return d

    def _alarm(self):
        """Handle alarm."""
        if self.masterState in [
            HbusMasterState.hbusMasterSearching,
            HbusMasterState.hbusMasterChecking,
        ]:

            if self.masterState == HbusMasterState.hbusMasterSearching:
                self.logger.info(
                    "Device search ended, "
                    + str(self.registeredSlaveCount)
                    + " found"
                )

            if self.detectSlavesEnded is not None:
                self.detectSlavesEnded()

            self.logger.debug("Retrieving devices information...")

            if self.masterState == HbusMasterState.hbusMasterSearching:
                self._slave_static_process()

            self.masterState = HbusMasterState.hbusMasterScanning

            d = defer.Deferred()

            i = 0
            for slave in self.detectedSlaveList:

                if self.detectedSlaveList[slave].basicInformationRetrieved:
                    continue

                d.addCallback(
                    self._slave_read_basic,
                    self.detectedSlaveList[slave].hbusSlaveAddress,
                )
                i += 1

            if i > 0:
                self.slaveReadDeferred = d

                reactor.callLater(
                    0.1, self._slave_read_start
                )  # @UndefinedVariable

            else:

                self.masterState = HbusMasterState.hbusMasterOperational

        elif self.masterState == HbusMasterState.hbusMasterStarting:

            self.masterState = HbusMasterState.hbusMasterIdle

            self._slave_detect()

    def find_device_by_uid(self, uid):
        """Find device by UID."""
        for dev in self.detectedSlaveList:
            if self.detectedSlaveList[dev].hbusSlaveUniqueDeviceInfo == int(
                uid
            ):
                return self.detectedSlaveList[dev].hbusSlaveAddress

        for dev in self.virtualDeviceList:
            if self.virtualDeviceList[dev].hbusSlaveUniqueDeviceInfo == int(
                uid
            ):
                return self.virtualDeviceList[dev].hbusSlaveAddress

        self.logger.debug("device with UID <" + str(int(uid)) + "> not found")
        return None

    def _response_timeout(self, response):
        self.logger.warning("Response timed out")
        self.logger.debug("Response timed out: %s", response)

        if self.hbusBusState == HbusBusState.LOCKED_THIS:
            self._push_command(HBUSCOMMAND_BUSUNLOCK, self.hbusBusLockedWith)

        if self.masterState == HbusMasterState.hbusMasterScanning:
            self.hbusDeviceScanningTimeout = True

        response.dCallback.errback(
            HBUSTimeoutException(response.timeoutActionParameters)
        )

        self.expectedResponseQueue.remove(response)

        # if response.timeoutAction is not None:
        #    response.timeoutAction(response.source)

        # response.tCallback.callback(response.source)

    def periodic_task(self):
        """Periodic task."""
        for r in self.removeQueue:

            if r in self.expectedResponseQueue:

                self.expectedResponseQueue.remove(r)

        del self.removeQueue[:]

        # if allBusses:
        #
        #    for b in range(0,32):
        #
        #        for d in range(0,32):
        #
        #            self.sendCommand(HBUSCOMMAND_SEARCH, HbusDeviceAddress(b,d))
        #            self.expectResponse(HBUSCOMMAND_ACK, HbusDeviceAddress(b,d))
        #
        # else:
        #
        #    for d in range(1,32):
        #
        #        self.sendCommand(HBUSCOMMAND_SEARCH,HbusDeviceAddress(self.hbusMasterAddr.bus_number,d))
        #        self.expectResponse(HBUSCOMMAND_ACK,HbusDeviceAddress(self.hbusMasterAddr.bus_number,d),action=self.registerNewSlave,actionParameters=HbusDeviceAddress(self.hbusMasterAddr.bus_number,d),timeout=10000000)

    def _slave_static_process(self):
        """Process static slaves."""
        for addr in self.staticSlaveList:

            if addr.global_id in self.detectedSlaveList:
                continue

            self.logger.info("Device with static address in %s", str(addr))

            self.register_new_slave(addr)

    def _bus_locked(self):
        """Handle bus locked event."""

    def _bus_free(self):
        """Handle bus free event."""
        while len(self.awaitingFreeBus):

            d = self.awaitingFreeBus.pop()
            d.callback(None)
