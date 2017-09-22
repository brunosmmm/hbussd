#coding=utf-8

"""Simple plugin management for hbussd
   @package hbussd_plugin
   @since 11/23/2014
   @author Bruno Morais <brunosmmm@gmail.com>
"""

import imp
import os
import logging
import uuid

PLUGIN_MAIN = "__init__" #plugin main file

class HbusPluginInfo(object):
    """Plugin manager plugin container"""

    def __init__(self, data):
        self.active = False
        self.data = data
        self.module = None

class HbusPluginManager(object):
    """Plugin manager"""

    plugins = {}

    def __init__(self, pluginpath, master):
        self.path = pluginpath
        self.__master = master
        self.vdevtranslator = {} #virtual device addresses translator
        self.logger = logging.getLogger('hbussd.hbusPluginMgr')

    def scan_plugins(self):
        """Scan folder for plugins"""
        self.plugins = {}

        plist = os.listdir(self.path)
        for pid in plist:
            path = os.path.join(self.path, pid)
            if os.path.isdir(path) != True or PLUGIN_MAIN+'.py' not in os.listdir(path):
                continue

            info = imp.find_module(PLUGIN_MAIN, [path])
            self.plugins[pid] = HbusPluginInfo(data=info)

    def get_available_plugins(self):
        """Return list of plugins found by scan"""
        return list(self.plugins.keys())

    def m_load_plugin(self, plugin):
        """Loads and activates plugin
        @param plugin plugin id
        """

        if plugin not in list(self.plugins.keys()):
            raise UserWarning("plugin is not available")

        if self.plugins[plugin].active == True:
            raise UserWarning("plugin is already loaded")


        pid = imp.load_module(PLUGIN_MAIN, *self.plugins[plugin].data)
        self.plugins[plugin].module = pid
        #create logger for plugin
        self.plugins[plugin].logger = logging.getLogger('hbussd.hbusPluginMgr.'+plugin)
        pid.register(self, plugin) #plugin entry point
        self.plugins[plugin].active = True

    def m_unload_plugin(self, plugin):
        """Deactivates and unloads plugin
        @param plugin plugin id
        """

        if plugin not in list(self.plugins.keys()):
            raise UserWarning("plugin is not available")

        if self.plugins[plugin].active == False:
            raise UserWarning("plugin is not loaded")

        self.plugins[plugin].module.unregister(self)
        self.plugins[plugin].active = False

    def m_evt_broadcast(self, event):
        """Event broadcasts
        @param event event container
        """
        for plugin in list(self.plugins.keys()):
            if self.plugins[plugin].active == True:
                self.plugins[plugin].module.masterEventOccurred(event)

    def m_read_vdev_obj(self, devicenum, objnum):
        """Read an object from a virtual device
        @param deviceNum virtual device number
        @param objNum object number in device
        """

        if devicenum not in list(self.vdevtranslator.keys()):
            raise UserWarning("virtual device not found")

        uid, plugin, dnum = self.vdevtranslator[devicenum]
        #read and return
        return self.plugins[plugin].module.readVirtualDeviceObject(dnum, objnum)

    def m_write_vdev_obj(self, devicenum, objnum, value):
        """Write a value to a virtual device object
        @param deviceNum virtual device number
        @param objNum object number in device
        @param value value written
        """

        if devicenum not in list(self.vdevtranslator.keys()):
            raise UserWarning("virtual device not found")

        uid, plugin, dnum = self.vdevtranslator[devicenum]
        #write
        self.plugins[plugin].module.writeVirtualDeviceObject(dnum, objnum, value)

    #Begin functions accessed by plugins

    def p_register_vdev(self, plugin, devicenum, deviceinfo):
        """Register a virtual device from a plugin
        @param plugin plugin id
        @param deviceNum plugin's device number
        @param deviceInfo virtual device description
        @return uuid generated
        """
        #generate uuid
        uid = uuid.uuid4()
        #register a virtual device in the master, get an address
        devnumber = self.__master.getnewvirtualaddress(uid.int)
        #save generated uid
        deviceinfo.hbusSlaveUniqueDeviceInfo = uid.int
        #add to local translator
        self.vdevtranslator[devnumber] = (uid, plugin, devicenum)
        self.__master.registerNewSlave(devnumber, deviceinfo)
        return (uid.int, devnumber)


    def p_unregister_vdev(self, plugin, devicenum):
        """Unregister a virtual device
        @param plugin plugin id
        @param deviceNum plugin's device number
        """

        devaddr = None
        for key, uid, pid, num in self.vdevtranslator.items():
            if pid == plugin and num == devicenum:
                #found
                devaddr = key

        if devaddr == None:
            self.logger.debug('device not found')
            return

        self.__master.unregisterSlave(devaddr, virtual=True)


    def p_interrupt(self, pluginid, interrupt):
        """Interruption from plugin
        @param pluginID plugin id
        @param interrupt interrupt container
        """
        pass

    def p_log(self, pluginid, msg, level=logging.DEBUG):
        """Log output from plugin
        @param pluginID plugin identification
        @param msg message to log
        @param level logging level
        """
        if pluginid not in list(self.plugins.keys()):
            self.logger.debug('plugin '+pluginid+' not activated!')
            return

        self.plugins[pluginid].logger.log(level, msg)
