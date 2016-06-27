__version__ = '0.0.1a'
__all__ = ['cluster', 'osimage', 'bmcsetup', 'node', 'switch', 'network', 'tracker', 'manager']
__author__ = 'Dmitry Chirikov'

from luna.config import *
import pymongo
from cluster import Cluster
from osimage import OsImage
from bmcsetup import BMCSetup
from node import Node, Group
from switch import Switch, MacUpdater
from network import Network
from tracker import *
from manager import Manager
from utils import *

def list(collection):
    import logging
    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    try:
        mongo_client = pymongo.MongoClient(get_con_options())
    except:
        logger.error("Unable to connect to MongoDB.")
        raise RuntimeError
    logger.debug("Connection to MongoDB was successful.")
    mongo_db = mongo_client[db_name]
    mongo_collection = mongo_db[collection]
    ret = []
    for doc in mongo_collection.find({}):
        try:
            ret.extend([doc['name']])
        except:
            ret.extend([doc['_id']])
    return ret
