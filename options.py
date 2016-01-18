from config import *
import pymongo
import logging
import inspect
import sys
from bson.objectid import ObjectId
from bson.dbref import DBRef
from luna.base import Base

class Options(Base):
    """
    Class for storing options and tunables for LunaCluster
    Also it is the parent class for OsImage
    """

    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    _logger = logging.getLogger(__name__)
    _collection_name = None
    _mongo_collection = None
    _keylist = None
    _id = None
    _name = None
    _DBRef = None
    _json = None

    def __init__(self, name = None, create = False, nodeprefix = 'node', nodedigits = 3, debug = 0):
        """
        Constructor can be used for creating object by setting create=True
        nodeprefix='node' and nodedigits='3' will give names like node001,
        nodeprefix='compute' and nodedigits='4' will give names like compute0001
        name is used to give default name for mongo document.
        Don't change it is are not sure what you are doing.

        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._logger.debug("Connecting to MongoDB.")
        self._collection_name = 'options'
        if name == None or name == '':
            name = 'general'
        mongo_doc = self._check_name(name, create)
        if create:
            mongo_doc = {'name': name, 'nodeprefix': nodeprefix, 'nodedigits': nodedigits}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._keylist = {'nodeprefix': type(''), 'nodedigits': type(0), 'debug': type(0)}

        self._logger.debug("Current instance:'{}".format(self._debug_instance()))
