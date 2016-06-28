from config import *
import logging
import sys
import time
import threading
import netsnmp
import datetime
import inspect

from bson.dbref import DBRef
from luna.base import Base
from luna.cluster import Cluster

class Switch(Base):
    """
    Class for operating with switch records
    """
    def __init__(self, name = None, mongo_db = None, create = False, id = None,
            ip = None, read = 'public', rw = 'private', oid = None):
        """
        ip      - ip of the switch
        read    - read community
        rw      - rw community
        oid     - could be, for instance
                .1.3.6.1.2.1.17.7.1.2.2.1.2
                .1.3.6.1.2.1.17.4.3.1.2
                .1.3.6.1.2.1.17.7.1.2.2
                .1.3.6.1.2.1.17.4.3.1.2
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'switch'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = { 'ip': type(''), 'read': type(''), 'rw': type(''), 'oid': type('') }
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            passed_vars = inspect.currentframe().f_locals
            for key in self._keylist:
                if type(passed_vars[key]) is not self._keylist[key]:
                    self._logger.error("Argument '{}' should be '{}'".format(key, self._keylist[key]))
                    raise RuntimeError
            mongo_doc = { 'name': name, 'ip': ip, 'read': read, 'rw': rw, 'oid': oid}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

class MacUpdater(object):

    def __init__(self, mongo_db, logger = None, interval = 30):
        self._mongo_db = mongo_db
        self.switch_collection = self._mongo_db['switch']
        self.known_mac_collection = self._mongo_db['switch_mac']

        aging = interval * 2
        self.logger = logger
        self.interval = interval
        self.logger.name = 'MacUpdater'
        self.active = True
        self.known_mac_collection.create_index("updated", expireAfterSeconds = aging )
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()
 
    def run(self):
        counter = self.interval
        cluster = Cluster(mongo_db = self._mongo_db)
        while self.active:
            if counter >= self.interval:
                if cluster.is_active():
                    self.update()
                else:
                    self.logger.info("This is passive node. Doing nothing.")
                    time.sleep(60)
                counter = 0
            counter += 1
            time.sleep(1)

    def stop(self):
        self.active = False

    def update(self):
        self.logger.info("Updating known mac addresses")
        switches = self.switch_collection.find()
        mac_count = 0
        for switch in switches:
            oid = switch['oid']
            ip = switch['ip']
            read = switch['read']
            switch_id = switch['_id']
            mongo_doc = {}
            mongo_doc['switch_id'] = switch_id
            try:
                self.logger.debug("Requesting following data: oid=%s\tip=%s\tcommunity=%s\tswitch_id=%s" % (oid, ip, read, switch_id))
                varlist = netsnmp.VarList(netsnmp.Varbind(oid))
                res = netsnmp.snmpwalk(varlist, Version = 1,  DestHost = ip, Community = read)
                updated = datetime.datetime.utcnow()
                for i in range(len(varlist)):
                    mac = ''
                    port = str(varlist[i].val)
                    for elem in varlist[i].tag.split('.')[-6:]:
                        mac += hex(int(elem)).split('x')[1].zfill(2) + ':'
                    mac = mac[:-1].lower()
                    mongo_doc['mac'] = mac
                    mongo_doc['port'] = port
                    mongo_doc_updated = mongo_doc.copy()
                    mongo_doc_updated['updated'] = updated
                    res = self.known_mac_collection.find_and_modify(mongo_doc, {'$set': mongo_doc_updated}, upsert = True)
                    if not bool(res):
                        mac_count += 1
            except NameError:
                if self.logger:
                    self.logger.error("Cannot reach '{}'".format(ip))
            except:
                err = sys.exc_info()[0]
                if self.logger:
                    self.logger.error(err)
        self.logger.info("Was added {} new mac addresses.".format(mac_count))
        return True
