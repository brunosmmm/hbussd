#coding=utf-8

##@package dummy
# @brief dummy plugin
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 11/23/2014

from hbussd_evt import *
import logging

virtualDevices = []
pluginMgr = None
pluginID = None

##Register plugin
# @param pluginManager plugin manager object
# @param pID this plugin's ID
def register(pluginManager, pID):
    global pluginMgr
    global pluginID
    pluginMgr = pluginManager
    pluginID = pID

##Unregister plugin from hbussd
def unregister():
    pass

##Read object from virtual device originating in this plugin
# @param device device id
# @param obj object number
def virtualDeviceReadObject(device, obj):
    pass

##Writes a virtual device object
# @param device device id
# @param obj object number
# @param value value written
def virtualDeviceWriteObject(device, obj, value):
    pass

##Master event broadcast receiver
# @param event event container
def masterEventOccurred(event):
    pluginMgr.pluginLog(pluginID,"I got an event!")
