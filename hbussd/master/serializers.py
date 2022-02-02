"""Serializers for objects."""
# Functions and classes for serialization of objects, JSON use
# @author Bruno Morais <brunosmmm@gmail.com>
# @since 13/02/2014


class GenericSerializer:
    """Generic dictionary-based serializer."""

    def __init__(self):
        """Initialize."""
        self._dict = {}

    def __getitem__(self, key):
        """Get item."""
        return self._dict[key]

    def __setitem__(self, key, value):
        """Set item."""
        self._dict[key] = value

    def __setattr__(self, attr, value):
        """Set attribute."""
        if not attr.startswith("_"):
            self._dict[attr] = value
        else:
            setattr(self, attr, value)

    @property
    def serializable(self):
        """Get serielizable."""
        return self._dict.copy()


class HbusSlaveSerializer(GenericSerializer):
    """Slave serializer."""

    # @param slave device object for information extraction
    def __init__(self, slave):
        """Initialize."""
        super().__init__()
        # Object's description string (device name)
        self.description = slave.hbusSlaveDescription
        # Device's UID
        self.uid = slave.hbusSlaveUniqueDeviceInfo
        # Device's object count
        self.objectcount = slave.hbusSlaveObjectCount
        # Device's endpoint count
        self.endpointcount = slave.hbusSlaveEndpointCount
        # Device's interrupt count
        self.interruptcount = slave.hbusSlaveInterruptCount

        # Current device address in bus
        self.currentaddress = str(slave.hbusSlaveAddress)
        # Device capabilities
        self.capabilities = slave.hbusSlaveCapabilities

    ##Generates device information dictionary
    # @return dictionary for serialization
    def getDict(self):
        return self.__dict__


##hbusSlaveInformation object type preserializer
class HbusObjectSerializer:

    ##Constructor
    # @param obj device object object for data extraction
    def __init__(self, obj):

        ##Object permissions
        self.permissions = obj.permissions
        ##Object descriptor string (name)
        self.description = obj.description
        ##Object size in bytes
        self.size = obj.size
        ##Object last known value
        self.lastvalue = obj.last_value
        ##Object data type
        self.datatype = obj.objectDataType
        ##Object data type information
        self.datatypeinfo = obj.objectDataTypeInfo
        ##Object extended information
        self.extendedinfo = obj.objectExtendedInfo
        ##Object level
        self.objectlevel = obj.objectLevel

    ##Generates device object information dictionary
    # @return dictionary for serialization
    def getDict(self):
        return self.__dict__
