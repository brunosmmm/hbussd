#coding=utf-8

##@package hbussd_plugin
# @brief Simple plugin management for hbussd
# @since 11/23/2014
# @author Bruno Morais <brunosmmm@gmail.com>

import imp
import os
import logging
import inspect

pluginMain = "__init__"

##Plugin manager plugin container
class hbusPluginInfo:
    
    def __init__(self,data):
        self.active = False
        self.data = data
        self.module = None

##Plugin manager
class hbusPluginManager:

    
    def __init__(self,pluginPath,master):
        self.path = pluginPath
        self.__master = master
        self.virtualDeviceTranslator = {}
        self.logger = logging.getLogger('hbussd.hbusPluginMgr')

    ##Scan plugin folder for plugins
    def scanPlugins(self):
        self.plugins = {}

        pList = os.listdir(self.path)
        for p in pList:
            path = os.path.join(self.path, p)
            if os.path.isdir(path) != True or pluginMain+'.py' not in os.listdir(path):
                continue
            
            info = imp.find_module(pluginMain, [path])
            self.plugins[p] = hbusPluginInfo(data=info)
    
    ##Return list of plugins found by scan
    def getAvailablePlugins(self):
        return self.plugins.keys()

    ##Loads and activates plugin
    # @param plugin plugin id
    def loadPlugin(self,plugin):
        
        if plugin not in self.plugins.keys():
            raise UserWarning("plugin is not available")
        
        if self.plugins[plugin].active == True:
            raise UserWarning("plugin is already loaded")
            
        
        p = imp.load_module(pluginMain, *self.plugins[plugin].data)
        self.plugins[plugin].module = p
        #create logger for plugin
        self.plugins[plugin].logger = logging.getLogger('hbussd.hbusPluginMgr.'+plugin)
        p.register(self,plugin) #plugin entry point
        self.plugins[plugin].active = True

    ##Deactivates and unloads plugin
    # @param plugin plugin id
    def unloadPlugin(self,plugin):
        
        if plugin not in self.plugins.keys():
            raise UserWarning("plugin is not available")
        
        if self.plugins[plugin].active == False:
            raise UserWarning("plugin is not loaded")

        self.plugins[plugin].module.unregister(self)
        self.plugins[plugin].active = False
    
    ##Register virtual device
    def pluginRegisterVirtualDevice(self,plugin):
        #register a virtual device in the master, get an address
        #add to local translator
        pass
        
    ##Unregister virtual device
    def pluginUnregisterVirtualDevice(self):
        pass

    ##Interruption from plugin
    # @param pluginID plugin id
    # @param interrupt interrupt container
    def pluginInterrupt(self,pluginID,interrupt):
        pass

    ##Log output from plugin
    # @param pluginID plugin identification
    # @param msg message to log
    # @param level logging level
    def pluginLog(self,pluginID,msg,level=logging.DEBUG):
        
        if pluginID not in self.plugins.keys():
            self.logger.debug('plugin '+pluginID+' not activated!')
            return
        
        self.plugins[pluginID].logger.log(level,msg)
        
    ##Event broadcasts
    # @param event event container
    def masterEventBroadcast(self,event):
        for plugin in self.plugins.keys():
            if self.plugins[plugin].active == True:
                self.plugins[plugin].module.masterEventOccurred(event)
