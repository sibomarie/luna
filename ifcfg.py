from config import *
import pymongo
import logging
import inspect
import sys
import os
from bson.objectid import ObjectId
from bson.dbref import DBRef
from luna.base import Base
from luna.options import Options

class IfCfg(Base):
    """
    Class for operating with ifcfg records
    """
    def __init__(self, name = None, create = False, network = '', prefix = '', netmask = ''):
        """
        create  - shoulld be True if we need create osimage
        network - network
        prefix  - should be specified network bits or 
        netmask - network mask
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        options = Options()
        self._collection_name = 'ifcfg'
        mongo_doc = self._check_name(name, create)
        if create:

            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.set('kernopts', 5)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self.link(options)

    def _calc_prefix_mask(prefix, netmask):
        import struct, socket
        try:
            prefix = int(prefix)
        except:
            prefix = 0
        if prefix in range(1,32):
            print prefix 
            prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
            return (prefix, socket.inet_ntoa(struct.pack('>L', (prefix_num))))
        prefix = 0
        try:
            mask_num = struct.unpack('>L', (socket.inet_aton(netmask)))[0]
        except socket.error:
            return (None, None)
        b = 32
        for i in reversed(range(0,31)):
            if (mask_num & 1<<i) == 0:
                b = i
                break
        prefix = 31-b
        prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return (prefix, socket.inet_ntoa(struct.pack('>L', (prefix_num))))
      


    def _get_net(self, address, prefix)
        import struct, socket
        if type(prefix) is not int:
            self._logger.debug("'prefix' should be integer")
            return None
        if prefix not in range(1,32):
            self._logger.debug("'prefix' should be 1>= and <=32")
            return None
        try:
            socket.inet_aton(address)
        except socket.error:
            self._logger.debug("'{}' does not looks like valid ip-address".format(address))
            return None
        net_num = struct.unpack('>L', (socket.inet_aton(address)))[0]
        mask_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return socket.inet_ntoa(struct.pack('>L', (net_num & mask_num)))

    def _check_ip_in_range(self, net, prefix, ip):
        return self._get_net(net, prefix) == self.get_net(ip, prefix)
