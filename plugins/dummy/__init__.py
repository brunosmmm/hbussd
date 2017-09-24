#coding=utf-8

##@package dummy
# @brief dummy plugin
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 11/23/2014

from hbussd.hbus.evt import *
from hbussd.plugins.vdevs import hbusVirtualDevice
from hbussd.hbus.slaves import HbusDeviceObject, HbusObjDataType
from hbussd.hbus.constants import HbusObjectPermissions as op

virtualDevices = {}
pluginMgr = None
pluginID = None

value_zero = [0]

def read_zero(objnum):
    global value_zero
    return value_zero

def write_zero(objnum, value):
    global value_zero
    print('write_zero, write = ', value)
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
    object_zero.description = "dummy object"
    object_zero.size = 1
    object_zero.objectDataType = HbusObjDataType.dataTypeUnsignedInt
    object_zero.objectDataTypeInfo = HbusObjDataType.dataTypeUintPercent
    object_zero.last_value = None

    device_zero.device.hbusSlaveObjects = {1: object_zero}

    devices = {0: device_zero}

    return devices

##Register plugin
# @param pluginManager plugin manager object
# @param pID this plugin's ID
def register(pluginManager, pID):
    global pluginMgr
    global pluginID
    global virtualDevices

    pluginMgr = pluginManager
    pluginID = pID
    
    virtualDevices = getVirtualDevices()
    
    #register devices
    for num, vdev in virtualDevices.items():
        pluginMgr.p_register_vdev(pluginID, num, vdev.device)

##Unregister plugin from hbussd
def unregister():
    pass

##Read object from virtual device originating in this plugin
# @param device device id
# @param obj object number
def readVirtualDeviceObject(device, obj):
    return virtualDevices[device].readObject(obj)

##Writes a virtual device object
# @param device device id
# @param obj object number
# @param value value written
def writeVirtualDeviceObject(device, obj, value):
    virtualDevices[device].writeObject(obj, value)

##Master event broadcast receiver
# @param event event container
def masterEventOccurred(event):
    pluginMgr.p_log(pluginID,"I got an event!")
