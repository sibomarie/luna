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

class BMCSetup(Base):
    """
    Class for operating with bmcsetup records
    """
    def __init__(self, name = None, create = False, id = None, 
            userid = 3, user = 'ladmin', password = 'ladmin', netchannel = 1, mgmtchannel = 1):
        """
        userid      - default user id
        user        - username
        password    - pasword
        netchannel  - network channel
        mgmtchannel - management channel
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'bmcsetup'
        mongo_doc = self._check_name(name, create, id)
        self._keylist = {'userid': type(0), 'user': type(''), 'password': type(''), 'netchannel': type(0), 'mgmtchannel': type(0)}
        if create:
            import inspect
            options = Options()
            passed_vars = inspect.currentframe().f_locals
            for key in self._keylist:
                if type(passed_vars[key]) is not self._keylist[key]:
                    self._logger.error("Argument '{}' should be '{}'".format(key, self._keylist[key]))
                    raise RuntimeError
            mongo_doc = {'name': name, 'userid': userid, 'user': user,
                    'password': password, 'netchannel': netchannel,
                    'mgmtchannel': mgmtchannel}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

