# coding=utf-8

"""Integrated web server for control, using pyBottle
  @package hbus_web
  @author Bruno Morais <brunosmmm@gmail.com>
  @date 2013-2015
  TODO: better documentation"""

import logging
import re
import string

import pkg_resources
from bottle import (
    TEMPLATE_PATH,
    ServerAdapter,
    request,
    route,
    run,
    static_file,
    template,
)

from hbussd.master.master import *


class AttachToTwisted(ServerAdapter):
    """Attach to existing reactor."""

    def run(self, handler):
        from twisted.internet import reactor
        from twisted.python.threadpool import ThreadPool
        from twisted.web import server, wsgi

        thread_pool = ThreadPool()
        thread_pool.start()
        reactor.addSystemEventTrigger("after", "shutdown", thread_pool.stop)
        factory = server.Site(wsgi.WSGIResource(reactor, thread_pool, handler))
        reactor.listenTCP(self.port, factory, interface=self.host)


class HBUSWEB:
    """HBUS Web server class"""

    # wait for asynchronous operations
    wait = False

    # TODO: decouple master object
    def __init__(self, port, hbusMaster):
        """Class constructor
        @param port HTTP port
        @param hbusMaster main master object reference for manipulation
        """

        try:
            views = pkg_resources.resource_filename("hbussd", "data/views")
            # distribution found!
            TEMPLATE_PATH.insert(0, views)

            self.static_file_path = pkg_resources.resource_filename(
                "hbussd", "data/web_static"
            )
        except pkg_resources.DistributionNotFound:
            pass

        # Server port
        self.port = port
        # main master object
        self.hbusMaster = hbusMaster
        # Minimum object level visible on web interface
        self.objectLevel = 0

        # get logger
        self.logger = logging.getLogger("hbussd.hbusweb")

    def index(self):
        """Generates main page template
        @return template HTML"""

        return template(
            "hbus_index",
            slaves=list(self.hbusMaster.detectedSlaveList.values()),
            masterStatus=self.hbusMaster.get_information_data(),
            re=re,
        )

    def favicon(self):
        """Favorite icon for web browser
        @return icon file"""

        return static_file("favicon.ico", root=self.static_file_path)

    def readSlaveObject(self, uid=None, obj=None):
        """Reads an object value and displays it
        @param uid device UID
        @param obj object number
        @return requested data"""

        self.wait = False

        def waitForSlaveRead(dummy):

            self.wait = False

        m = re.match(r"0x([0-9A-Fa-f]+)L?", uid)
        devUID = m.group(1)

        addr = self.hbusMaster.find_device_by_uid(int(devUID, 16))

        if addr is None:
            s = None
        else:
            if addr.bus_number == 254:
                s = self.hbusMaster.virtualDeviceList[addr.global_id]
            else:
                s = self.hbusMaster.detectedSlaveList[addr.global_id]

        if obj is not None:
            try:
                self.wait = True
                self.hbusMaster.slave_object_read(
                    addr,
                    int(obj),
                    callBack=waitForSlaveRead,
                    timeoutCallback=waitForSlaveRead,
                )

                while self.wait:
                    pass
            except Exception as ex:
                self.logger.debug("error reading device object: {}".format(ex))
                raise

        if s is not None:
            try:
                data = s.hbusSlaveObjects[int(obj)].getFormattedValue()
            except TypeError:
                data = "?"
                raise
        else:
            data = "?"

        if data is None:
            data = "?"

        return data

    def slaveInfo(self, addr=None, uid=None, obj=None):
        """Templates a page with device information
        @param addr device address
        @param uid device UID
        @param obj object number
        @return template HTML"""

        getN = 0

        self.wait = False

        def waitForSlaveRead(dummy):

            self.wait = False

        if addr is not None:
            devAddr = string.split(addr, ":")
            device = HbusDeviceAddress(int(devAddr[0]), int(devAddr[1]))

            s = self.hbusMaster.detectedSlaveList[device.global_id]
        elif uid is not None:
            m = re.match(r"0x([0-9A-Fa-f]+)L?", uid)
            devUID = m.group(1)

            addr = self.hbusMaster.find_device_by_uid(int(devUID, 16))

            if addr is None:
                s = None
            else:
                if addr.bus_number == 254:
                    s = self.hbusMaster.virtualDeviceList[addr.global_id]
                else:
                    s = self.hbusMaster.detectedSlaveList[addr.global_id]

            if obj is not None:

                try:
                    self.wait = True
                    self.hbusMaster.slave_object_read(
                        addr,
                        int(obj),
                        callBack=waitForSlaveRead,
                        timeoutCallback=waitForSlaveRead,
                    )

                    getN = int(obj)

                    while self.wait:
                        pass
                except:
                    pass

            if s is None:

                # TODO: retur error template, device not available

                pass

            writeObjectCount = len(
                [
                    x
                    for x in list(s.hbusSlaveObjects.values())
                    if x.permissions & 0x02
                    and x.objectLevel >= self.objectLevel
                    and x.hidden is False
                ]
            )
            readObjectCount = len(
                [
                    x
                    for x in list(s.hbusSlaveObjects.values())
                    if x.permissions & 0x01
                    and x.objectLevel >= self.objectLevel
                    and x.hidden is False
                ]
            )

        return template(
            "hbus_slave_info",
            slave=s,
            hbusSlaveObjectDataType=HbusObjDataType(),
            objectLevel=self.objectLevel,
            masterStatus=self.hbusMaster.get_information_data(),
            readObjCount=readObjectCount,
            writeObjCount=writeObjectCount,
            re=re,
            getNumber=getN,
        )

    # TODO: document this properly
    def busList(self):
        """Generates a bus list"""

        from json import dumps

        from bottle import response

        rv = []
        for bus in self.hbusMaster.get_information_data().activeBusses:

            rv.append([{"busNumber": bus}])

        response.content_type = "application/json"
        return dumps(rv)

    def slaveWriteObject(self, uid=None, obj=None):
        """Writes value to device object
        @param uid device UID
        @param obj object number
        @return template HTML with updated data"""

        if uid is not None:
            m = re.match(r"0x([0-9A-Fa-f]+)L?", uid)
            devUID = m.group(1)

            addr = self.hbusMaster.find_device_by_uid(int(devUID, 16))

            if addr is None:
                s = None
            else:
                if addr.bus_number == 254:
                    s = self.hbusMaster.virtualDeviceList[addr.global_id]
                else:
                    s = self.hbusMaster.detectedSlaveList[addr.global_id]

            if s is None:

                # TODO: return error template, device not available

                pass

        return template(
            "hbus_slave_object_set",
            slave=s,
            hbusSlaveObjectDataType=HbusObjDataType,
            objectLevel=self.objectLevel,
            masterStatus=self.hbusMaster.get_information_data(),
            objectNumber=int(obj),
            re=re,
            percentToRange=self.percentToRange,
        )

    # TODO: document this
    def slaveInfoSet(self, uid=None, obj=None):

        newObjValue = request.forms.get("value")

        if uid is not None:
            m = re.match(r"0x([0-9A-Fa-f]+)L?", uid)
            devUID = m.group(1)

            addr = self.hbusMaster.find_device_by_uid(int(devUID, 16))

            if addr is None:
                s = None
            else:
                if addr.bus_number == 254:
                    s = self.hbusMaster.virtualDeviceList[addr.global_id]
                else:
                    s = self.hbusMaster.detectedSlaveList[addr.global_id]

            if obj is not None:
                # try:
                self.hbusMaster.slave_object_write_fmt(
                    addr, int(obj), newObjValue
                )

                # except:
                #    pass

            # writeObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x02 and x.objectLevel > self.objectLevel])
            # readObjectCount = len([x for x in s.hbusSlaveObjects.values() if x.permissions & 0x01 and x.objectLevel > self.objectLevel])

        return template(
            "hbus_slave_object_set",
            slave=s,
            hbusSlaveObjectDataType=HbusObjDataType(),
            objectLevel=self.objectLevel,
            masterStatus=self.hbusMaster.get_information_data(),
            objectNumber=int(obj),
            re=re,
            percentToRange=self.percentToRange,
        )
        # readObjCount=readObjectCount,writeObjCount=writeObjectCount)

    def slavesByBus(self, busNumber=None):
        """Generates page with devices from a bus
        @param busNumber bus number
        @return template HTML"""

        if int(busNumber) == 255:
            slaveList = list(self.hbusMaster.detectedSlaveList.values())
            slaveList.extend(list(self.hbusMaster.virtualDeviceList.values()))
        elif int(busNumber) == 254:
            # virtual device bus
            slaveList = list(self.hbusMaster.virtualDeviceList.values())
        else:
            slaveList = []
            for slave in list(self.hbusMaster.detectedSlaveList.values()):
                if slave.hbusSlaveAddress.bus_number == int(busNumber):
                    slaveList.append(slave)
        return template(
            "hbus_slave_by_bus",
            slaveList=slaveList,
            masterStatus=self.hbusMaster.get_information_data(),
            busNumber=busNumber,
            re=re,
        )

    def setLevel(self, level=None):
        """Sets level filter for visible objects on web interface
        @param level minimum level"""

        if level is None:
            return

        try:
            self.objectLevel = int(level)
        finally:
            return

    def staticFiles(self, filename):
        """Fetches static files
        @param filename name of file to be fetched
        @return file"""

        return static_file(filename, root=self.static_file_path)

    def percentToRange(self, percentStr):
        """Converts percent values to scaled
        @param percentStr percent string
        @return value"""

        if percentStr == "?" or percentStr is None:
            return "0"

        s = re.sub(r"\.[0-9]+%$", "", percentStr)

        return s

    def run(self):
        """pyBottle main loop"""

        # creates routes
        route("/")(self.index)
        route("/index.html")(self.index)

        route("/slave-addr/<addr>")(self.slaveInfo)
        route("/slave-uid/<uid>")(self.slaveInfo)
        route("/slave-uid/<uid>/get-<obj>")(self.slaveInfo)
        route("/slave-uid/<uid>/set-<obj>")(self.slaveWriteObject)
        route("/slave-uid/<uid>/set-<obj>", method="POST")(self.slaveInfoSet)
        route("/slave-uid/<uid>/objdata-<obj>")(self.readSlaveObject)
        route("/busses")(self.busList)

        # list of devices by bus number
        route("/bus/<busNumber>")(self.slavesByBus)

        route("/static/<filename>")(self.staticFiles)
        route("/favicon.ico")(self.favicon)

        # hidden options
        route("/set-level/<level>")(self.setLevel)

        run(host="0.0.0.0", port=self.port, server=AttachToTwisted, debug=True)
