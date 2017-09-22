#coding=utf-8

##@package dummy
# @brief dummy plugin
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 11/23/2014

from hbussd.hbus.evt import *
import logging
#import our things
import plugins.dummy.devobjs

virtualDevices = {}
pluginMgr = None
pluginID = None

##Register plugin
# @param pluginManager plugin manager object
# @param pID this plugin's ID
def register(pluginManager, pID):
    global pluginMgr
    global pluginID
    global virtualDevices

    pluginMgr = pluginManager
    pluginID = pID
    
    virtualDevices = plugins.dummy.devobjs.getVirtualDevices()
    
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
