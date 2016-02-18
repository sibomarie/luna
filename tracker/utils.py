#!/usr/bin/env python
#
# Common utilities for Pytt.
#
# @author: Sreejith K <sreejithemk@gmail.com>
# Created on 12th May 2011
# http://foobarnbaz.com

from luna.config import *
import pymongo
import datetime
import os
import logging
import logging.handlers
#import shelve
import libtorrent
from socket import inet_aton
from struct import pack
import tornado.web
import binascii
import random
try:
    from ConfigParser import RawConfigParser
    from httplib import responses
except ImportError:
    from configparser import RawConfigParser
    from http.client import responses


# Paths used by Pytt.
CONFIG_PATH = os.path.expanduser('~/.pytt/config/pytt.conf')
DB_PATH = os.path.expanduser('~/.pytt/db/pytt.db')
LOG_PATH = os.path.expanduser('~/.pytt/log/pytt.log')

# Some global constants.
PEER_INCREASE_LIMIT = 30
DEFAULT_ALLOWED_PEERS = 50
MAX_ALLOWED_PEERS = 200
INFO_HASH_LEN = 20 * 2  # info_hash is hexified.
PEER_ID_LEN = 20  * 2  # peer_hash is hexified.

# HTTP Error Codes for BitTorrent Tracker
INVALID_REQUEST_TYPE = 100
MISSING_INFO_HASH = 101
MISSING_PEER_ID = 102
MISSING_PORT = 103
INVALID_INFO_HASH = 150
INVALID_PEER_ID = 151
INVALID_NUMWANT = 152
GENERIC_ERROR = 900

# Pytt response messages
PYTT_RESPONSE_MESSAGES = {
    INVALID_REQUEST_TYPE: 'Invalid Request type',
    MISSING_INFO_HASH: 'Missing info_hash field',
    MISSING_PEER_ID: 'Missing peer_id field',
    MISSING_PORT: 'Missing port field',
    INVALID_INFO_HASH: 'info_hash is not %d bytes' % INFO_HASH_LEN,
    INVALID_PEER_ID: 'peer_id is not %d bytes' % PEER_ID_LEN,
    INVALID_NUMWANT: 'Peers more than %d is not allowed.' % MAX_ALLOWED_PEERS,
    GENERIC_ERROR: 'Error in request',
}
# add our response codes to httplib.responses
responses.update(PYTT_RESPONSE_MESSAGES)

logger = logging.getLogger('tornado.access')


def setup_logging(debug=False):
    """Setup application logging.
    """
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_handler = logging.handlers.RotatingFileHandler(LOG_PATH,
                                                       maxBytes=1024*1024,
                                                       backupCount=2)
    root_logger = logging.getLogger('')
    root_logger.setLevel(level)
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format)
    log_handler.setFormatter(formatter)
    root_logger.addHandler(log_handler)


#def create_config(path):
#    """Create default config file.
#    """
#    logging.info('creating default config at %s' % CONFIG_PATH)
#    config = RawConfigParser()
#    config.add_section('tracker')
#    config.set('tracker', 'port', '8080')
#    config.set('tracker', 'interval', '5')
#    config.set('tracker', 'min_interval', '1')
#    with open(path, 'w') as f:
#        config.write(f)


#def create_pytt_dirs():
#    """Create directories to store config, log and db files.
#    """
#    logging.info('setting up directories for Pytt')
#    for path in [CONFIG_PATH, DB_PATH, LOG_PATH]:
#        dirname = os.path.dirname(path)
#        if not os.path.exists(dirname):
#            os.makedirs(dirname)
#    # create the default config if its not there.
#    if not os.path.exists(CONFIG_PATH):
#        create_config(CONFIG_PATH)


class BaseHandler(tornado.web.RequestHandler):
    """Since I dont like some tornado craps :-)
    """
    def decode_argument(self, value, name):
        # info_hash is raw_bytes, hexify it.
        if name in ['info_hash', 'peer_id'] :
            value = binascii.hexlify(value)
        return super(BaseHandler, self).decode_argument(value, name)


#class ConfigError(Exception):
#    """Raised when config error occurs.
#    """


#class Config:
#    """Provide a single entry point to the Configuration.
#    """
#    __shared_state = {}
#
#    def __init__(self):
#        """Borg pattern. All instances will have same state.
#        """
#        self.__dict__ = self.__shared_state
#
#    def get(self):
#        """Get the config object.
#        """
#        if not hasattr(self, '__config'):
#            self.__config = RawConfigParser()
#            if self.__config.read(CONFIG_PATH) == []:
#                raise ConfigError('No config at %s' % CONFIG_PATH)
#        return self.__config
#
#    def close(self):
#        """Close config connection
#        """
#        if not hasattr(self, '__config'):
#            return 0
#        del self.__config


#class Database:
#    """Provide a single entry point to the database.
#    """
#    __shared_state = {}
#
#    def __init__(self):
#        """Borg pattern. All instances will have same state.
#        """
#        self.__dict__ = self.__shared_state
#
#    def get(self):
#        """Get the shelve object.
#        """
#        if not hasattr(self, '__db'):
#            self.__db = shelve.open(DB_PATH, writeback=True)
#        return self.__db
#
#    def close(self):
#        """Close db connection
#        """
#        if not hasattr(self, '__db'):
#            return 0
#        self.__db.close()
#        del self.__db


class MongoBackEnd:
    __shared_state = {}
    mongo_client = None
    def __init__(self):
        self.mongo_client = None
        self.__dict__ = self.__shared_state
    def get(self):
        try:
            self.mongo_client = pymongo.MongoClient()
        except:
            logger.error("Unable to connect to MongoDB.")
            raise RuntimeError
        logger.debug("Connection to MongoDB was successful.")
        mongo_db =  self.mongo_client[db_name]
        return mongo_db['tracker']

    def close(self):
        logger.debug("Connection to MongoDB closed.")
        try:
            self.mongo_client.close()
        except:
            logger.error("Connect to MongoDB was not opened.")
        

def get_mongo():
    return MongoBackEnd().get()
        
def close_mongo():
    return MongoBackEnd().close()

#def get_config():
#    """Get a connection to the configuration.
#    """
#    return Config().get()


#def get_db():
#    """Get a persistent connection to the database.
#    """
#    return Database().get()
#
#
#def close_db():
#    """Close db connection.
#    """
#    Database().close()
#
#
#def no_of_seeders(info_hash):
#    """Number of peers with the entire file, aka "seeders".
#    """
#    db = get_db()
#    mongo = get_mongo()
#    
#    count = 0
#    if info_hash in db:
#        for peer_info in db[info_hash]:
#            if peer_info[3] == 'completed':
#                count += 1
#    return count
#
#
#def no_of_leechers(info_hash):
#    """Number of non-seeder peers, aka "leechers".
#    """
#    db = get_db()
#    mongo = get_mongo()
#    count = 0
#    if info_hash in db:
#        for peer_info in db[info_hash]:
#            if peer_info[3] == 'started':
#                count += 1
#    return count
#
#
#def store_peer_info(info_hash, peer_id, ip, port, status, uploaded, downloaded, left):
#    """Store the information about the peer.
#    """
#    db = get_db()
#    mongo = get_mongo()
#    if info_hash in db:
#        if (peer_id, ip, port, status) not in db[info_hash]:
#            db[info_hash].append((peer_id, ip, port, status))
#    else:
#        db[info_hash] = [(peer_id, ip, port, status)]
#    updated = datetime.datetime.utcnow()
#    # json = {'info_hash': info_hash, 'peer_id': peer_id, 
#    json = {'peer_id': peer_id, 'status': status, 'updated': updated,
#            'uploaded': uploaded, 'downloaded': downloaded, 'left': left} 
#    if not bool(status):
#        json.pop('status')
#    mongo.find_and_modify({'info_hash': info_hash, 'ip': ip, 'port': port}, {'$set': json}, upsert = True)



# TODO: add ipv6 support
#def get_peer_list(info_hash, numwant, compact, no_peer_id):
#   """Get all the peer's info with peer_id, ip and port.
#    Eg: [{'peer_id':'#1223&&IJM', 'ip':'162.166.112.2', 'port': '7887'}, ...]
#    """
#    db = get_db()
#    mongo = get_mongo()
#    if compact:
#        byteswant = numwant * 6
#        compact_peers = b''
#        # make a compact peer list
#        if info_hash in db:
#            for peer_info in db[info_hash]:
#                ip = inet_aton(peer_info[1])
#                port = pack('>H', int(peer_info[2]))
#                compact_peers += (ip+port)
#        logging.debug('compact peer list: %r' % compact_peers[:byteswant])
#        return compact_peers[:byteswant]
#    else:
#        peers = []
#        if info_hash in db:
#            for peer_info in db[info_hash]:
#                p = {}
#                p['peer_id'], p['ip'], p['port'], _ = peer_info
#                p['peer_id'] = binascii.unhexlify(p['peer_id'])
#                if no_peer_id:
#                    del p['peer_id']
#                peers.append(p)
#        logging.debug('peer list: %r' % peers[:numwant])
#        return peers[:numwant]

def update_peers(info_hash, peer_id, ip, port, status, uploaded, downloaded, left):
    """Store the information about the peer.
    """
    mongo = get_mongo()
    updated = datetime.datetime.utcnow()
    # json = {'info_hash': info_hash, 'peer_id': peer_id, 
    json = {'peer_id': peer_id, 'status': status, 'updated': updated,
            'uploaded': uploaded, 'downloaded': downloaded, 'left': left} 
    if not bool(status):
        json.pop('status')
    mongo.find_and_modify({'info_hash': info_hash, 'ip': ip, 'port': port}, {'$set': json}, upsert = True)

def get_peers(info_hash, numwant, compact, no_peer_id, age):
    mongo = get_mongo()
    time_age = datetime.datetime.utcnow() - datetime.timedelta(seconds = age)
    # '6c756e616c756e616c756e616c756e616c756e61'
    mongo_cursor = mongo.find({'info_hash': info_hash, 'updated': {'$gte': time_age}}, {'peer_id': 1, 'ip': 1, 'port': 1, 'status': 1})
    server_records = mongo.find({'info_hash': info_hash, 'peer_id': binascii.hexlify('lunalunalunalunaluna'), 'port': {'$ne': 0}}, {'peer_id': 1, 'ip': 1, 'port': 1, 'status': 1})
    peer_tuple_list = []
    n_leechers = 0
    n_seeders = 0
    for doc in mongo_cursor:
        try:
            n_leechers += int(doc['status'] == 'started')
            n_seeders += int(doc['status'] == 'completed')
        except:
            pass
        peer_tuple_list.extend([(binascii.unhexlify(doc['peer_id']), doc['ip'], doc['port'])])
    for doc in server_records:
        try:
            n_leechers += int(doc['status'] == 'started')
            n_seeders += int(doc['status'] == 'completed')
        except:
            pass
        peer_tuple_list.extend([(binascii.unhexlify(doc['peer_id']), doc['ip'], doc['port'])])
    # It's believed it will get better 'cohesion'
    if numwant > len(peer_tuple_list):
        numwant = len(peer_tuple_list)
    random_peer_list = random.sample(peer_tuple_list, numwant)
    compact_peers = b''
    peers = []
    for peer_info in random_peer_list:
        if compact:
            ip = inet_aton(peer_info[1])
            port = pack('>H', int(peer_info[2]))
            compact_peers += (ip+port)
            continue
        p['peer_id'], p['ip'], p['port'] = peer_info
        peers.append(p)
    if compact:
        logging.debug('compact peer list: %r' % compact_peers)
        return (n_seeders, n_leechers, compact_peers)
    logging.debug('peer list: %r' % peers)
    return (n_seeders, n_leechers, peers)
