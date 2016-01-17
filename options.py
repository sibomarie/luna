from config import *
import pymongo
import logging
import sys
from bson.objectid import ObjectId
from bson.dbref import DBRef

class Options():
    """
    Class for storing options and tunables for LunaCluster
    Also it is the parent class for OsImage
    """

    logging.basicConfig(level=logging.INFO)
    _logger = logging.getLogger(__name__)
    _collection_name = None
    _mongo_collection = None
    _keylist = None
    _id = None
    _name = None
    _DBRef = None
    _json = None

    def __init__(self, name='general', create=False, nodeprefix='node', nodedigits=3):
        """
        Constructor can be used for creating object by setting create=True
        nodeprefix='node' and nodedigits='3' will give names like node001,
        nodeprefix='compute' and nodedigits='4' will give names like compute0001
        name is used to give default name for mongo document.
        Don't change it is are not sure what you are doing.

        >>> import luna
        >>> lunaopts = luna.Options(name='testsectoin')
        ERROR:luna.options:It is needed to create collection first


        """
        self._logger.debug("Arguments: create='{}', nodeprefix='{}', nodedigits={}, name='{}'".format(create, nodeprefix, nodedigits, name))
        self._logger.debug("Connecting to MongoDB.")
        try:
            mongo_client = pymongo.MongoClient()
        except:
            self._logger.error("Unable to connect to MongoDB.")
            raise
        self._collection_name = 'options'
        self._keylist = ['nodeprefix', 'nodedigits']
        self._logger.debug("Connection to MongoDB was successful.")
        mongo_db = mongo_client[db_name]
        self._mongo_collection = mongo_db[self._collection_name]
        self._json = self._mongo_collection.find_one({'name': name})
        if not create and not self._json:
            self._logger.error("It is needed to create collection first")
            return None
        if create and self._json['name'] == name:
            self._logger.error("Already created")
            return None
        self._logger.debug("json: '{}'".format(self._json))
        if create:
            mongo_doc = {'name': name, 'nodeprefix': nodeprefix, 'nodedigits': nodedigits}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self._update_json()
        else:
            self._name = self._json['name']
            self._id = self._json['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

    def _update_json(self):
        if self._id:
            self._json = self._mongo_collection.find_one({'_id': self._id})

    def __repr__(self):
        """
        Returns nice JSON
        """
        from bson.json_util import dumps
        return dumps(self._json, sort_keys=True, indent=4, separators=(',', ': '))
        
    def __str__(self):
        """
        Returns nice JSON
        """
        from bson.json_util import dumps
        return dumps(self._json, sort_keys=True, indent=4, separators=(',', ': '))

    @property
    def name(self):
        """
        Name of the options section
        """
        return self._name

    @property
    def id(self):
        """
        MongoDB's '_id' value of the document
        """
        return self._id

    @property
    def DBRef(self):
        """
        MongoDB DBRef of the document
        """
        return self._DBRef
    
    @property
    def json(self):
        """
        Raw json from MongoDB. One should not use it for change
        """
        return self._json

    @property
    def keylist(self):
        """
        List of the 'simple' fields one can change (no data structures here)
        """
        return self._keylist
        
    def get(self, key):
        """
        Allow to get variables from keylist
        """
        if not self._json:
            self._logger.error("No such key '{}'".format(key))
            return None
        return self._json[key]

    def set(self, key, value):
        """
        Allow to set variables from keylist
        """
        try:
            req_key = self._keylist.index(key)
        except:
            self._logger.error("No such key for the given object".format(key))
            return None
        if not self._json:
            self._logger.error("No json for the given object".format(key))
            return None
        if type(value) is str:
            value = unicode(value, "utf-8")
        if type(value) is not type(self._json[key]):
            self._logger.error("Value '{}' should be '{}' type".format(key, type(self._json[key])))
            return None
        mongo_doc = {key: value}
        self._mongo_collection.update({'_id': self._id}, {'$set': mongo_doc}, multi=False, upsert=False)
        self._update_json()
        return True

    def rename(self, name):
        """
        Rename object
        """
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        mongo_doc = self._mongo_collection.find_one({'name': name})
        if mongo_doc:
            self._logger.error("Object '{}' exists already".format(name))
            return None
        self._mongo_collection.update({'_id': self._id}, {'$set': {'name': name}}, multi=False, upsert=False)
        self._update_json()
        self._name = name
        return True

        
    def _add_dbref(self, key_name, dbref):
        if type(dbref) is not DBRef:
            self._logger.error("Passed argument is not DBRef type")
            return None
        if dbref == self._DBRef:
            self._logger.error("Cant operate with the link to myself")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        self._mongo_collection.update({'_id': self._id}, {'$addToSet': {key_name: dbref}}, multi=False)
        self._update_json()
        return True

    def _del_dbref(self, key_name, dbref):
        if type(dbref) is not DBRef:
            self._logger.error("Passed argument is not DBRef type")
            return None
        if dbref == self._DBRef:
            self._logger.error("Cannot operate with the link to myself")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        self._mongo_collection.update({'_id': self._id}, {'$pullAll': {key_name: dbref}}, multi=False)
        self._update_json()
        return True

    def add_reference(self, dbref):
        """
        Add DBRef to another MongoDB's document
        """
        self._add_dbref(used_key, dbref)

    def add_back_reference(self, dbref):
        """
        Add DBRef to MongoDB's document where the current document is used
        """
        self._add_dbref(usedby_key, dbref)

    def del_reference(self, dbref):
        """
        Delete DBRef to another MongoDB's document
        """
        self._add_dbref(use_key, dbref)

    def del_back_reference(self, dbref):
        """
        Delete DBRef to MongoDB's document where the current document is used
        """
        self._add_dbref(usedby_key, dbref)
    # TODO
    def get_references(self):
        pass
    # TODO
    def get_back_references(self):
        pass
    # TODO
    def delete(self):
        """
        Is used to delete the options section from MongoDB.
        """
        if not len(self._json['_usedby_']) == 0:
            self._logger.error("Current object is being concidered as dependency for the following objects: ")
            # need to list and resolve all the objects from _used_by_ array
        # need to delete back links from the objects in _use_ array
        
        self._collection_name = None
        self._mongo_collection = None
        self._keylist = None
        self._id = None
        self._name = None
        self._DBRef = None
        self._json = None
        
        
            


