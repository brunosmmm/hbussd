#coding=utf-8

##@package hbus_except
#Exception events and handling
#@author Bruno Morais <brunosmmm@gmail.com>
#@since 08/19/2013
#@todo Document this

class HBUSDoNotRetryException(Exception):
    
    pass

class HBUSDataAlreadyReceived(Exception):
    
    pass

class HBUSTimeoutException(IOError):
    
    pass

class HBUSRetryInformation:
    
    def __init__(self,attempts=0):
        self.attempts = attempts
