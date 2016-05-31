from config import *
import logging
import struct
import socket
from bson.dbref import DBRef
from luna.base import Base
from luna.cluster import Cluster

class Network(Base):
    """
    Class for operating with ifcfg records

    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None, NETWORK = None, PREFIX = None):
        """
        create  - should be True if we need create osimage
        NETWORK - network
        PREFIX  - should be specified network bits or
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'network'
        self._keylist = {'NETWORK': long, 'PREFIX': int}
        mongo_doc = self._check_name(name, mongo_db, create, id)
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            num_net = self.get_base_net(NETWORK, PREFIX)
            if not num_net:
                self._logger.error("Cannot compute NETWORK/PREFIX")
                raise RuntimeError
            else:
                freelist = [{'start': 1, 'end': (1<<(32-PREFIX))-1}]
                mongo_doc = {'name': name, 'NETWORK': num_net, 'PREFIX': PREFIX, 'freelist': freelist}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)

    def absnum_to_ip(self, numip):
        try:
            ip = socket.inet_ntoa(struct.pack('>L', numip))
        except:
            self._logger.error("Cannot compute numeric ip = '{}' to human readable".format(numip))
            return None
        return ip

    def ip_to_absnum(self, ip):
        try:
            absnum = struct.unpack('>L', (socket.inet_aton(ip)))[0]
        except:
            self._logger.error("Cannot compute ip = '{}'".format(ip))
            return None
        return absnum

    def relnum_to_ip(self, numip):
        num_net = self._get_json()['NETWORK']
        return self.absnum_to_ip(num_net + numip)

    def ip_to_relnum(self, ip):
        num_net = self._get_json()['NETWORK']
        num_ip = self.ip_to_absnum(ip)
        if not self.ip_in_net(ip):
            self._logger.error("Ip = '{}' is not in network.".format(ip))
            return None
        return num_ip - num_net

    def get_base_net(self, address, prefix):
        if type(prefix) is not int:
            self._logger.error("'prefix' should be integer")
            return None
        if prefix not in range(1,32):
            self._logger.error("'prefix' should be 1>= and <=32")
            return None
        if type(address) is long or type(address) is int:
            net_num = address
        else:
            try:
                net_num = struct.unpack('>L', (socket.inet_aton(address)))[0]
            except socket.error:
                self._logger.debug("'{}' does not looks like valid ip-address".format(address))
                return None
        mask_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return net_num & mask_num

    def ip_in_net(self, ip):
        if type(ip) is int:
            num_ip = ip
        else:
            num_ip = self.ip_to_absnum(ip)
        num_net = self._get_json()['NETWORK']
        prefix = self._get_json()['PREFIX']
        return self.get_base_net(num_net, prefix) == self.get_base_net(ip, prefix)

    def set(self, key, value):
        if not bool(key) or type(key) is not str :
            self._logger.error("Field should be specified")
            return None
        if not key in self._keylist:
            self._logger.error("Cannot change '{}' field".format(key))
            return None
        if key == 'NETWORK':
            prefix = self._get_json()['PREFIX']
            network = self.get_base_net(value, prefix)
            if not bool(network):
                self._logger.error("Cannot compute NETWORK for entered '{}'".format(value))
                return None
            json = {'NETWORK': network, 'PREFIX': prefix}
        else:
            network = self._get_json()['NETWORK']
            new_network = self.get_base_net(network, value)
            if not bool(new_network):
                self._logger.error("Cannot compute NETWORK for prefix = '{}'".format(value))
                raise RuntimeError
            if not self._set_uplimit_ip(value):
                self._logger.error("Cannot set PREFIX as some IPs are reserved out of the new border.".format(value))
                raise RuntimeError
            json = {'NETWORK': new_network, 'PREFIX': value}
        ret = self._mongo_collection.update({'_id': self._id}, {'$set': json}, multi=False, upsert=False)
        return not ret['err']

    def get(self, key):
        if not key or type(key) is not str:
            return None
        obj_json = self._get_json()
        if key == 'NETWORK':
            return self.absnum_to_ip(obj_json[key])
        if key == 'NETMASK':
            prefix = obj_json['PREFIX']
            prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
            return socket.inet_ntoa(struct.pack('>L', (prefix_num)))
        if key == 'PREFIX':
            return obj_json['PREFIX']
        return None

    def _get_next_ip(self):
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        if not bool(freelist):
            self._logger.error("No more IPs avalilable")
            return None
        first_elem = freelist[0]
        if first_elem['start'] == first_elem['end']:
            freelist.pop(0)
            res = self._save_free_list(freelist)
            if not res:
                self._logger.error("Error during saving to MongoDB")
                return None
            return first_elem['start']
        freelist[0] = {'start': first_elem['start'] + 1, 'end': first_elem['end']}
        res = self._save_free_list(freelist)
        if not res:
            self._logger.error("Error during saving to MongoDB")
            return None
        return first_elem['start']

    def _get_ip(self, num):

        def change_elem(num, elem):
            find = False
            if num not in range(elem['start'], elem['end']+1):
                return ( find, [elem] )
            find = True
            if elem['end'] == elem['start']:
                return ( find, None )
            if num == elem['start']:
                return ( find, [{'start': elem['start'] + 1, 'end': elem['end']}] )
            if num == elem['end']:
                return ( find, [{'start': elem['start'], 'end': elem['end'] - 1}] )
            return ( find, [{'start': elem['start'], 'end': num-1}, {'start': num+1, 'end': elem['end']}] )
 
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        if not bool(freelist):
            self._logger.error("No more IPs avalilable")
            return None
        start = freelist[0]['start']
        finish = freelist[-1]['end']
        if num not in range(start, finish + 1):
            self._logger.error("Requested IP '{}' is out of range".format(num))
            return None
        new_list = []
        find = False
        for elem in freelist:
            new_elem = change_elem(num, elem)
            if new_elem[0]:
                find = True
            if not new_elem[1]:
                continue
            new_list.extend(new_elem[1])
        freelist = new_list[:]
        ret = self._save_free_list(freelist)
        if not ret:
            return None
        if find:
            return num
        self._logger.error("Requested IP '{}' is out of free range".format(num))
        return None
 
    def _set_uplimit_ip(self, prefix):
        border = (1<<(32-prefix))-1
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        last_elem = freelist[-1]
        if last_elem['start'] > border:
            self._logger.error("Cannot cut list of free IPs. Requested cut to '{}'".format(border))
            return False
        freelist[-1] = {'start': last_elem['start'], 'end': border}
        return self._save_free_list(freelist)

    def _save_free_list(self, freelist):
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'freelist': freelist}}, multi=False, upsert=False)
        if res['err']:
            self._logger.error("Error while saving list of free IPs: '{}'".format(freelist))
        return not res['err']
 
    def reserve_ip(self, ip = None):
        if type(ip) is str:
            num = self.ip_to_relnum(ip)
        else:
            num = ip
        if bool(ip):
            return self._get_ip(num)
        return self._get_next_ip()

    def release_ip(self, ip):
        if type(ip) is str:
            num = self.ip_to_relnum(ip)
        else:
            num = ip
        insert_elem = {'start': num, 'end': num}
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        filled_list = []
        for elem in freelist:
            try:
                prev_end = filled_list[-1]['end']
            except:
                prev_end = 0
            next_start = elem['start']
            if num in range(prev_end + 1, next_start):
                filled_list.extend([insert_elem])
            filled_list.extend([elem])
        prefix = self._get_json()['PREFIX']
        upborder = (1<<(32-prefix))-1
        if num <= upborder and num > freelist[-1]['end']:
            filled_list.extend([num])
        if len(freelist) == len(filled_list):
            self._logger.error("Cannot release IP. No place for '{}' in list: '{}'".format(num, freelist))
            return False
        defrag_list = []
        defrag_list.extend([filled_list.pop(0)])
        for key in filled_list:
            if defrag_list[-1]['end'] == (key['start'] - 1):
                defrag_list[-1]['end'] = key['end']
            else:
                defrag_list.extend([key])
        self._save_free_list(defrag_list)
        return True
 
    def get_used_ips(self):
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist'][:]
        except:
            return None
        lastip = freelist[-1]['start']
        ips = []
        for i in range(1,lastip):
            if i in range(freelist[0]['start'], freelist[0]['end']+1):
                continue
            if i > freelist[0]['end']:
                freelist.pop(0)
            ips.extend([self.relnum_to_ip(i)])
        return ips
