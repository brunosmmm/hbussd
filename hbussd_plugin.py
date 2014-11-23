#coding=utf-8

##@package hbussd_plugin
# @brief Simple plugin management for hbussd
# @since 11/23/2014
# @author Bruno Morais <brunosmmm@gmail.com>

import imp
import os

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
    def loadPlugin(self,plugin):
        
        if plugin not in self.plugins.keys():
            raise UserWarning("plugin is not available")
        
        if self.plugins[plugin].active == True:
            raise UserWarning("plugin is already loaded")
            
        
        p = imp.load_module(pluginMain, *self.plugins[plugin].data)
        self.plugins[plugin].module = p
        p.register(self) #plugin entry point

    ##Deactivates and unloads plugin
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
        
        
    ##Event broadcasts
    def masterEventBroadcast(self,event):
        for plugin in self.plugins.keys():
            if plugin.active == True:
                plugin.module.masterEventOccurred(event)
