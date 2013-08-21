#coding=utf-8
'''
Created on 19/08/2013

@author: bruno
'''

class HBUSDoNotRetryException(StandardError):
    
    pass

class HBUSDataAlreadyReceived(StandardError):
    
    pass

class HBUSTimeoutException(IOError):
    
    pass

class HBUSRetryInformation:
    
    def __init__(self,attempts=0):
        self.attempts = attempts