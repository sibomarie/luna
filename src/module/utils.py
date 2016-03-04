import logging
import pymongo

def set_mac_node(mac, node, mongo_db = None):
    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    if not mongo_db:
        try:
            mongo_client = pymongo.MongoClient()
        except:
            logger.error("Unable to connect to MongoDB.")
            raise RuntimeError
        logger.debug("Connection to MongoDB was successful.")
        mongo_db = mongo_client[db_name]
    mongo_collection = mongo_db['mac']
    mongo_collection.remove({'mac': mac})
    mongo_collection.remove({'node': node})
    mongo_collection.insert({'mac': mac, 'node': node})
