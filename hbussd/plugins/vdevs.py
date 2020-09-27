"""Virtual device definitions for plugins."""

from hbussd.hbus.slaves import HbusDevice, HbusDeviceObject


class HbusVirtualDevice:
    """Container for virtual devices, add data and handles onto HbusDevice"""

    def __init__(self, pid, pmgr, description=""):
        """Initialize."""
        self._pid = pid
        self._pmgr = pmgr
        self.device = HbusDevice(None)
        # nothing to retrieve, all information will already be present
        self.device.basicInformationRetrieved = True
        self.device.extendedInformationRetrieved = True
        self.device.hbusSlaveObjects = {}

        # is virtual
        self.device.hbusSlaveIsVirtual = True
        self.device.hbusSlaveDescription = description

        # default object count is 1
        self.device.hbusSlaveObjectCount = 1

    def add_object(self, objnum, obj):
        """Add object."""
        if objnum in self.device.hbusSlaveObjects:
            raise KeyError("object already exists")
        if not isinstance(obj, HbusDeviceObject):
            raise TypeError("obj must be a HbusDeviceObject object")
        self.device.hbusSlaveObjects[objnum] = obj
        self.device.hbusSlaveObjectCount += 1  # why?

    def read_object(self, objnum):
        """Prototype for reading virtual object
        @param objnum virtual device's object number
        """
        pass

    def write_object(self, objnum, value):
        """Prototype for writing virtual object
        @param objnum virtual device's object number
        @param value value to be written
        """
        pass

    def master_event(self, event):
        """Receive event."""

    @property
    def plugin_id(self):
        """Get plugin id."""
        return self._pid

    @property
    def plugin_mgr(self):
        """Get plugin manager object."""
        return self._pmgr


class HbusPlugin:
    """Hbus plugin."""

    def __init__(self):
        """Initialize."""
        self._plugin_id = None
        self._plugin_manager = None
        self._devices = {}

    @property
    def plugin_id(self):
        """Plugin id."""
        return self._plugin_id

    @plugin_id.setter
    def plugin_id(self, value):
        """Set plugin id."""
        if self._plugin_id is not None:
            raise RuntimeError("plugin id already set")
        self._plugin_id = value

    @property
    def plugin_manager(self):
        """Plugin manager."""
        return self._plugin_manager

    @plugin_manager.setter
    def plugin_manager(self, value):
        """Set plugin manager."""
        if self._plugin_manager is not None:
            raise RuntimeError("plugin manager already set")
        self._plugin_manager = value

    def log(self, msg):
        """Log events."""
        self.plugin_manager.p_log(self.plugin_id, msg)

    def add_device(self, devnum, device):
        """Add device."""
        if not isinstance(device, HbusVirtualDevice):
            raise TypeError("device must be a HbusVirtualDevice object.")
        if devnum in self._devices:
            raise KeyError(f"device with id {devnum} already exists")
        self._devices[devnum] = device

    def register_devices(self):
        """Register devices."""
        for num, vdev in self._devices.items():
            self.plugin_manager.p_register_vdev(self._plugin_id, num, vdev)
