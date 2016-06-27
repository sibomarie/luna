from config import *
import logging
import pymongo
import ConfigParser
import urllib

def set_mac_node(mac, node, mongo_db = None):
    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    if not mongo_db:
        try:
            mongo_client = pymongo.MongoClient(get_con_options())
        except:
            logger.error("Unable to connect to MongoDB.")
            raise RuntimeError
        logger.debug("Connection to MongoDB was successful.")
        mongo_db = mongo_client[db_name]
    mongo_collection = mongo_db['mac']
    mongo_collection.remove({'mac': mac})
    mongo_collection.remove({'node': node})
    mongo_collection.insert({'mac': mac, 'node': node})

def get_con_options():
    conf = ConfigParser.ConfigParser()
    if not conf.read("/etc/luna.conf"):
        return "localhost"
    try:
        replicaset = conf.get("MongoDB", "replicaset")
    except:
        replicaset = None
    try:
        server = conf.get("MongoDB", "server")
    except:
        server = 'localhost'
    try:
        authdb = conf.get("MongoDB", "authdb")
    except:
        authdb = 'admin'
    try:
        user = conf.get("MongoDB", "user")
        password = urllib.quote_plus(conf.get("MongoDB", "password"))
    except:
        user = None
        password = None
    if user and password and replicaset:
        auth_str = 'mongodb://' + user + ':' + password + '@' + server + '/' + authdb + '?replicaSet=' + replicaset
        return auth_str
    if user and password:
        auth_str = 'mongodb://' + user + ':' + password + '@' + server + '/' + authdb
        return auth_str
    return "localhost"

