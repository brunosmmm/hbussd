"""Dummy plugin."""
from hbussd.plugins.vdevs import HbusVirtualDevice, HbusPlugin
from hbussd.hbus.slaves import HbusDeviceObject, HbusObjDataType
from hbussd.hbus.constants import HbusObjectPermissions as op


plugin = HbusPlugin()


class DummyDevice(HbusVirtualDevice):
    """Dummy device."""

    def __init__(self, *args):
        """Initialize."""
        super().__init__(*args, "Dummy plugin virtual device")
        self._value_zero = [0]

        object_zero = HbusDeviceObject()
        object_zero.permissions = op.READ_WRITE
        object_zero.description = "dummy object"
        object_zero.size = 1
        object_zero.objectDataType = HbusObjDataType.dataTypeUnsignedInt
        object_zero.objectDataTypeInfo = HbusObjDataType.dataTypeUintPercent
        object_zero.last_value = None
        self.add_object(1, object_zero)

    def read_object(self, objnum):
        """Read objects."""
        return self._value_zero

    def write_object(self, objnum, value):
        """Write objects."""
        self._value_zero = value

    def master_event(self, event):
        """Event."""
        print("evt received")


def register(plugin_manager, plugin_id):
    """Register plugin."""
    device_zero = DummyDevice(plugin_manager, plugin_id)
    plugin.add_device(0, device_zero)

    # save id
    plugin.plugin_id = plugin_id
    plugin.plugin_manager = plugin_manager

    # register devices
    plugin.register_devices()
    plugin.log("Dummy plugin registered")


def unregister():
    """Unregister plugin"""
    plugin.log("Dummy plugin unregistered")


def master_event(event):
    """Master event occurred."""
    plugin.log("I got an event!")
