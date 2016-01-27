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

class Switch(Base):
    """
    Class for operating with switch records
    """
    def __init__(self, name = None, create = False, id = None, 
            ip = None, read = None, rw = None):
        """
        ip      - ip of the switch
        read    - read community
        rw      - rw community
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'switch'
        mongo_doc = self._check_name(name, create, id)
        self._keylist = { 'ip': type(''), 'read': type(''), 'rw': type('') }
        if create:
            import inspect
            options = Options()
            passed_vars = inspect.currentframe().f_locals
            for key in self._keylist:
                if type(passed_vars[key]) is not self._keylist[key]:
                    self._logger.error("Argument '{}' should be '{}'".format(key, self._keylist[key]))
                    raise RuntimeError
            mongo_doc = { 'name': name, 'ip': ip, 'read': read, 'rw': rw }
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

# >>> l1 = netsnmp.VarList(netsnmp.Varbind('1.3.6.1.2.1.17.7.1.2.2.1.2'))
# >>> res = netsnmp.snmpwalk(l1, Version = 1,  DestHost = 'switch', Community='public')
# >>> for i in range(len(l1)):
#...     print "%s %s" % (l1[i].tag,  l1[i].val)
#... 
#>>> s = '64.141.92.54.133.134'
#>>> for n in s.split('.'):
#...     print hex(int(n)).split('x')[1]
# 1.3.6.1.2.1.17.4.3.1.2     1.3.6.1.2.1.17.7.1.2.2      1.3.6.1.2.1.17.4.3.1.2
