from config import *
import pymongo
import logging
import inspect
import sys
from bson.objectid import ObjectId
from bson.dbref import DBRef

class Base():
    """
    Base for LunaCluster
    Also it is the parent class for the rest classes
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

    def __init__(self, name = None, create = False, nodeprefix = 'node', nodedigits = 3):
        """
        Constructor can be used for creating object by setting create=True
        nodeprefix='node' and nodedigits='3' will give names like node001,
        nodeprefix='compute' and nodedigits='4' will give names like compute0001
        name is used to give default name for mongo document.
        Don't change it is are not sure what you are doing.
        """
        self._logger.error("Please do not call this class")
        raise RuntimeError

    
    def _check_name(self, name, create):
        try:
            self._mongo_client = pymongo.MongoClient()
        except:
            self._logger.error("Unable to connect to MongoDB.")
            raise RuntimeError
        self._logger.debug("Connection to MongoDB was successful.")
        self._mongo_db = self._mongo_client[db_name]
        self._mongo_collection = self._mongo_db[self._collection_name]
        if not name:
            self._logger.error("'name' needs to be specified")
            raise RuntimeError
        mongo_doc = self._mongo_collection.find_one({'name': name})
        if not create and not mongo_doc:
            self._logger.error("It is needed to create object first")
            raise RuntimeError
        if create and mongo_doc and mongo_doc['name'] == name:
            self._logger.error("'{}' is already created".format(name))
            self._wipe_vars()
            return None
        return mongo_doc

    def _debug_function(self):
        """
        Outputs name of the calling function and parameters passed into
        """
        if not logging.getLogger().getEffectiveLevel() == 10:
            return None
        caller = inspect.currentframe().f_back
        f_name = inspect.getframeinfo(caller)[2]
        _, _, _, values = inspect.getargvalues(caller)
        return (f_name, values)

    def _debug_instance(self):
        """
        Outputs tuple of internal data from class
        """
        if not logging.getLogger().getEffectiveLevel() == 10:
            return None
        return (self._name, self._id, self._DBRef, self.nice_json)

    def _wipe_vars(self):
        """
        Erase class variables
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        keys = self.__dict__.keys()
        for key in keys:
            self.__dict__.pop(key, None)
        return None

    def _get_json(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        if self._id:
            return self._mongo_collection.find_one({'_id': self._id})

    def __repr__(self):
        """
        Returns nice JSON
        """
        from bson.json_util import dumps
        return dumps(self._get_json(), sort_keys=True, indent=4, separators=(',', ': '))
        
    def __str__(self):
        """
        Returns name
        """
        return self._name

    @property
    def name(self):
        """
        Name of the object
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
        return self._get_json()

    @property
    def nice_json(self):
        """
        Raw json from MongoDB. One should not use it for change
        """
        from bson.json_util import dumps
        return dumps(self._get_json(), sort_keys=True, indent=4, separators=(',', ': '))

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
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        obj_json = self._get_json()
        if not obj_json[key]:
            self._logger.error("No such key '{}'".format(key))
            return None
        return obj_json[key]

    def set(self, key, value):
        """
        Allow to set variables from keylist
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            val_type = self._keylist[key]
        except:
            self._logger.error("No such key for the given object".format(key))
            return None
        obj_json = self._get_json()
        if not obj_json:
            self._logger.error("No json for the given object".format(key))
            return None
        if type(value) is not val_type:
            self._logger.error("Value '{}' should be '{}' type".format(key, type(obj_json[key])))
            return None
        if type(value) is str:
            value = unicode(value, "utf-8")
        mongo_doc = {key: value}
        self._mongo_collection.update({'_id': self._id}, {'$set': mongo_doc}, multi=False, upsert=False)
        return True

    def rename(self, name):
        """
        Rename object
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        mongo_doc = self._mongo_collection.find_one({'name': name})
        if mongo_doc:
            self._logger.error("Object '{}' exists already".format(name))
            return None
        self._mongo_collection.update({'_id': self._id}, {'$set': {'name': name}}, multi=False, upsert=False)
        self._name = name
        return True

#    def _add_dbref(self, key_name, dbref):
#        if type(dbref) is not DBRef:
#            self._logger.error("Passed argument is not DBRef type")
#            return None
#        if dbref == self._DBRef:
#            self._logger.error("Cant operate with the link to the same object")
#            return None
#        if not self._id:
#            self._logger.error("Was object deleted?")
#            return None
#        self._mongo_collection.update({'_id': self._id}, {'$addToSet': {key_name: dbref}}, multi=False)
#        return True
#
#    def _del_dbref(self, key_name, dbref):
#        if type(dbref) is not DBRef:
#            self._logger.error("Passed argument is not DBRef type")
#            return None
#        if dbref == self._DBRef:
#            self._logger.error("Cannot operate with the links tp the same object")
#            return None
#        if not self._id:
#            self._logger.error("Was object deleted?")
#            return None
#        self._mongo_collection.update({'_id': self._id}, {'$pullAll': {key_name: dbref}}, multi=False)
#        return True
#
#    def add_reference(self, dbref):
#        """
#        Add DBRef to another MongoDB's document
#        """
#        self._add_dbref(used_key, dbref)
#
#    def add_back_reference(self, dbref):
#        """
#        Add DBRef to MongoDB's document where the current document is used
#        """
#        self._add_dbref(usedby_key, dbref)
#
#    def del_reference(self, dbref):
#        """
#        Delete DBRef to another MongoDB's document
#        """
#        self._add_dbref(use_key, dbref)
#
#    def del_back_reference(self, dbref):
#        """
#        Delete DBRef to MongoDB's document where the current document is used
#        """
#        self._add_dbref(usedby_key, dbref)

    def link(self, dbref):
        """
        Unlink objects in MongoDB
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            dbref = dbref.DBRef
        except:
            pass
        if type(dbref) is not type(self._DBRef):
            self._logger.error("Passed argument is not DBRef type")
            return None
        if dbref == self._DBRef:
            self._logger.error("Cant operate with the link to the same object")
            #return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        remote_mongo_collection = self._mongo_db[dbref.collection]
        self._mongo_collection.update({'_id': self._id}, {'$addToSet': {use_key: dbref}}, multi=False, upsert=False)
        remote_mongo_collection.update({'_id': dbref.id}, {'$addToSet': {usedby_key: self._DBRef}}, multi=False, upsert=False)

    def unlink(self, dbref):
        """
        Link objects in MongoDB
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            dbref = dbref.DBRef
        except:
            pass
        if type(dbref) is not type(self._DBRef):
            self._logger.error("Passed argument is not DBRef type")
            return None
        if dbref == self._DBRef:
            self._logger.error("Cant operate with the link to the same object")
            #return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        remote_mongo_collection = self._mongo_db[dbref.collection]
        self._mongo_collection.update({'_id': self._id}, {'$pullAll': {use_key: [dbref]}}, multi=False, upsert=False)
        remote_mongo_collection.update({'_id': dbref.id}, {'$pullAll': {usedby_key: [self._DBRef]}}, multi=False, upsert=False)

    def get_links(self, resolve=False):
        """
        Enumerates all references
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        output = []
        obj_json = self._get_json()
        for dbref in obj_json[use_key]:
            remote_mongo_collection = self._mongo_db[dbref.collection]
            if not resolve:
                name = str(dbref.id)
            else:
                try:
                    name = remote_mongo_collection.find_one({'_id': dbref.id})['name']
                except:
                    name = str(dbref.id)
            output.extend({dbref.collection: name})
        return output



    def get_back_links(self, resolve=False):
        """
        Enumerates all reverse references
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        output = []
        obj_json = self._get_json()
        for dbref in obj_json[usedby_key]:
            remote_mongo_collection = self._mongo_db[dbref.collection]
            if not resolve:
                name = str(dbref.id)
            else:
                try:
                    name = remote_mongo_collection.find_one({'_id': dbref.id})['name']
                except:
                    name = str(dbref.id)
            output.extend([{'collection': dbref.collection, 'name': name}])
        return output
        
    def delete(self):
        """
        Is used to delete the document from MongoDB.
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        import json
        obj_json = self._get_json()
        try:
            usedby_len = len(obj_json[usedby_key])
        except:
            usedby_len = 0
        if not usedby_len == 0:
            back_links = self.get_back_links(resolve=True)
            self._logger.error("Current object is being written as a dependency for the following objects:")
            for elem in back_links:
                self._logger.error(json.dumps(elem, sort_keys=True ))
            return None
        try:
            obj_json_use_arr = obj_json[use_key]
        except:
            obj_json_use_arr = []
        for dbref in obj_json_use_arr:
            self.unlink(dbref)
        ret = self._mongo_collection.remove({'_id': self._id}, multi=False)
        self._wipe_vars()
        return not ret['err']
