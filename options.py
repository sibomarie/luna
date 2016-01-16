from config import *
import pymongo
import logging
import sys
from bson.objectid import ObjectId
from bson.dbref import DBRef

class Options():
    collection_name = 'options'
    def __init__(self, create=False, nodeprefix='node', nodedigits='3'):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.debug("Connecting to MongoDB")
        try:
            mongo_client = pymongo.MongoClient()
        except:
            logger.error("ERROR: Unable to connect to MongoDB")
            raise
        logger.debug("Connection to MongoDB was successful")
        mongo_db = mongo_client[db_name]
        mongo_collection = mongo_db[self.collection_name]
        mongo_doc = mongo_collection.find_one()
        if not create and not mongo_doc:
            logger.error("It is needed to create collection first")
            raise RuntimeError
        if create and mongo_doc:
            logger.error("Already created")
            raise RuntimeError
        if create:
            mongo_doc = {'nodeprefix': nodeprefix, 'nodedigits': nodedigits}
            self.nodeprefix = nodeprefix
            self.nodedigits = nodedigits
            self._id = mongo_collection.insert(mongo_doc)
            self.DBRef = DBRef(self.collection_name, self._id)
        else:
            self.nodeprefix = mongo_doc['nodeprefix']
            self.nodedigits = mongo_doc['nodedigits']
            self._id = mongo_doc['_id']
            self.DBRef = DBRef(self.collection_name, self._id)
            


