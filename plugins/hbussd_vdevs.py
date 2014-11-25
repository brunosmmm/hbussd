#coding=utf-8
"""Virtual device definitions for plugins
   @author Bruno Morais <brunosmmm@gmail.com>
   @since 24/11/2014
"""

from hbusslaves import HbusDevice

class hbusVirtualDevice:
    """Container for virtual devices, add data and handles onto HbusDevice
    """
    def __init__(self):
        self.device = HbusDevice(None)
        #nothing to retrieve, all information will already be present
        self.device.basicInformationRetrieved = True
        self.device.extendedInformationRetrieved = True
        self.device.hbusSlaveObjects = {}

    def readObject(self, objnum):
        """Prototype for reading virtual object
        @param objnum virtual device's object number
        """
        pass

    def writeObject(self, objnum, value):
        """Prototype for writing virtual object
        @param objnum virtual device's object number
        @param value value to be written
        """
        pass
