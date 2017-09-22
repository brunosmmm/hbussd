#coding=utf-8

##@package hbussd_evt
# @brief Master event system
# @since 11/23/2014
# @author Bruno Morais <brunosmmm@gmail.com>

##Types of events that are broadcasted
class hbusMasterEventType:

    ##Master started
    eventStarted = 0
    ##Master entered operational phase
    eventOperational = 1
    ##Master received interruption
    eventInterruption = 2
    ##Master kicked device from bus
    eventDeviceKicked = 3
    ##Master registered new device in bus
    eventDeviceAdded = 4
    ##Unknown
    eventNone = 5

##Complete event information class
class hbusMasterEvent:

    eventType = hbusMasterEventType.eventNone

    def __init__(self, eventType=hbusMasterEventType.eventNone):
        self.eventType = eventType
