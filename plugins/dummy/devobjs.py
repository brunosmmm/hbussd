#coding=utf-8
""" dummy plugin devices and objects description
    @author Bruno Morais <brunosmmm@gmail.com>
    @since 24/11/2014
"""

from plugins.hbussd_vdevs import hbusVirtualDevice
from hbusslaves import HbusDeviceObject, HbusObjDataType, HbusObjLevel
from hbus_constants import HbusObjectPermissions as op

value_zero = [0]

def read_zero(objnum):
    global value_zero
    return value_zero

def write_zero(objnum, value):
    global value_zero
    value_zero = value


def getVirtualDevices():
    """Build virtual devices for this plugin"""

    device_zero = hbusVirtualDevice()

    #configure device properly
    device_zero.readObject = read_zero
    device_zero.writeObject = write_zero

    device_zero.device.hbusSlaveIsVirtual = True
    device_zero.device.hbusSlaveDescription = "Dummy plugin virtual device"
    
    #add dummy object
    device_zero.device.hbusSlaveObjectCount = 2
    object_zero = HbusDeviceObject()
    
    object_zero.permissions = op.READ_WRITE
    object_zero.objectDescription = "dummy object"
    object_zero.objectSize = 1
    object_zero.objectDataType = HbusObjDataType.dataTypeUnsignedInt
    object_zero.objectDataTypeInfo = HbusObjDataType.dataTypeUintPercent
    object_zero.objectLastValue = None
    
    device_zero.device.hbusSlaveObjects = {}
    device_zero.device.hbusSlaveObjects[1] = object_zero


    devices = {0: device_zero}

    return devices
