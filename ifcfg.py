from config import *
import pymongo
import logging
import inspect
import sys
import os
from bson.objectid import ObjectId
from bson.dbref import DBRef
from luna.base import Base
from luna.options import Options

class IfCfg(Base):
    """
    Class for operating with ifcfg records

    Some tests and examples:

    >>> import luna
    >>> opt = luna.Options(create=True)
    >>> osimage = luna.OsImage(create=True, name='compute', path='/os/compute-image/', kernver='3.10.0-327.3.1.el7.x86_64')
    >>> ifcfg = luna.IfCfg(name = 'internal', create=True, NETWORK = '192.168.17.10', PREFIX = 23, NETMASK = '255.255.255.0' )
    >>> print ifcfg.dump()
    NETWORK="192.168.16.0"
    NETMASK="255.255.254.0"
    PREFIX="23"
    >>> ifcfg.delete()
    True
    >>> ifcfg = luna.IfCfg(name = 'internal', create=True, NETWORK = '192.168.177.10', PREFIX = 21, NETMASK = '255.255.0.0' )
    >>> print ifcfg.dump()
    NETWORK="192.168.176.0"
    NETMASK="255.255.248.0"
    PREFIX="21"
    >>> ifcfg.set('NETWORK', '192.168.133.10')
    True
    >>> print ifcfg.dump()
    NETWORK="192.168.128.0"
    NETMASK="255.255.248.0"
    PREFIX="21"
    >>> ifcfg.set('NETWORK', '300.168.133.10')
    ERROR:luna.base:Cannot compute NETWORK for entered '300.168.133.10'
    >>> print ifcfg.dump()
    NETWORK="192.168.128.0"
    NETMASK="255.255.248.0"
    PREFIX="21"
    >>> ifcfg.set('NETWORK', 'lkdsjldfld')
    ERROR:luna.base:Cannot compute NETWORK for entered 'lkdsjldfld'
    >>> print ifcfg.dump()
    NETWORK="192.168.128.0"
    NETMASK="255.255.248.0"
    PREFIX="21"
    >>> ifcfg.set('prefix', 45)
    ERROR:luna.base:Cannot convert PREFIX=45 to PREFIX and NETMASK
    >>> print ifcfg.dump()
    NETWORK="192.168.128.0"
    NETMASK="255.255.248.0"
    PREFIX="21"
    >>> ifcfg.set('prefix', 8)
    True
    >>> print ifcfg.dump()
    NETWORK="192.0.0.0"
    NETMASK="255.0.0.0"
    PREFIX="8"
    >>> ifcfg.set('prefix', 'dfgdfgdfg')
    ERROR:luna.base:Cannot convert PREFIX=dfgdfgdfg to PREFIX and NETMASK
    >>> print ifcfg.dump()
    NETWORK="192.0.0.0"
    NETMASK="255.0.0.0"
    PREFIX="8"
    >>> ifcfg.delete()
    True
    >>> ifcfg = luna.IfCfg(name = 'internal', create=True, NETWORK = '10.1.45.10', PREFIX = 21, NETMASK = '255.255.0.0' )
    >>> print ifcfg.dump()
    NETWORK="10.1.40.0"
    NETMASK="255.255.248.0"
    PREFIX="21"
    >>> ifcfg.set('NETMASK', '255.0.0.0')
    True
    >>> print ifcfg.dump()
    NETWORK="10.0.0.0"
    NETMASK="255.0.0.0"
    PREFIX="8"
    >>> ifcfg.set('NETMASK', 'sdllkdjfs')
    ERROR:luna.base:Cannot convert NETMASK="sdllkdjfs" to PREFIX and NETMASK
    >>> print ifcfg.dump()
    NETWORK="10.0.0.0"
    NETMASK="255.0.0.0"
    PREFIX="8"
    >>> ifcfg.set('DNS1', '8.8.8.8')
    True
    >>> print ifcfg.dump()
    NETWORK="10.0.0.0"
    DNS1="8.8.8.8"
    NETMASK="255.0.0.0"
    PREFIX="8"
    >>> ifcfg.set('MTU', 9000)
    True
    >>> print ifcfg.dump()
    NETWORK="10.0.0.0"
    DNS1="8.8.8.8"
    NETMASK="255.0.0.0"
    MTU="9000"
    PREFIX="8"
    >>> ifcfg.set('DNS1', 0)
    True
    >>> print ifcfg.dump()
    NETWORK="10.0.0.0"
    NETMASK="255.0.0.0"
    MTU="9000"
    PREFIX="8"
    >>> ifcfg.set('MTU', "")
    True
    >>> print ifcfg.dump()
    NETWORK="10.0.0.0"
    NETMASK="255.0.0.0"
    PREFIX="8"
    >>> ifcfg.delete()
    True
    >>> osimage.delete()
    True
    >>> opt.delete()
    True

    """
    def __init__(self, name = None, create = False, id = None, NETWORK = '', PREFIX = '', NETMASK = ''):
        """
        create  - should be True if we need create osimage
        NETWORK - network
        PREFIX  - should be specified network bits or 
        NETMASK - network mask
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'ifcfg'
        self._masked_fields = [ '_id', 'name', 'freelist', use_key, usedby_key ]
        mongo_doc = self._check_name(name, create, id)
        if create:
            options = Options()
            prefix, netmask = self._calc_prefix_mask(PREFIX, NETMASK)
            if not netmask:
                self._logger.error("Wrong prefix '{}' entered".format(PREFIX))
                raise RuntimeError
            network = self._get_net(NETWORK, prefix)
            if not network:
                self._logger.error("Wrong netmorki '{}' entered".format(NETWORK))
                raise RuntimeError
            freelist = [{'start': 1, 'end': (1<<(32-prefix))-1}]
            mongo_doc = {'name': name, 'NETWORK': network, 'PREFIX': prefix, 'NETMASK': netmask, 'freelist': freelist}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

    def _calc_prefix_mask(self, prefix, netmask):
        import struct, socket
        try:
            prefix = int(prefix)
        except:
            prefix = 0
        if prefix in range(1,32):
            prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
            return (prefix, socket.inet_ntoa(struct.pack('>L', (prefix_num))))
        prefix = 0
        try:
            mask_num = struct.unpack('>L', (socket.inet_aton(netmask)))[0]
        except socket.error:
            return (None, None)
        b = 32
        for i in reversed(range(0,31)):
            if (mask_num & 1<<i) == 0:
                b = i
                break
        prefix = 31-b
        prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return (prefix, socket.inet_ntoa(struct.pack('>L', (prefix_num))))
      
    def _get_net(self, address, prefix):
        import struct, socket
        if type(prefix) is not int:
            self._logger.debug("'prefix' should be integer")
            return None
        if prefix not in range(1,32):
            self._logger.debug("'prefix' should be 1>= and <=32")
            return None
        try:
            socket.inet_aton(address)
        except socket.error:
            self._logger.debug("'{}' does not looks like valid ip-address".format(address))
            return None
        net_num = struct.unpack('>L', (socket.inet_aton(address)))[0]
        mask_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return socket.inet_ntoa(struct.pack('>L', (net_num & mask_num)))

    def _check_ip_in_range(self, net, prefix, ip):
        return self._get_net(net, prefix) == self._get_net(ip, prefix)

    def set(self, key, value):
        if not bool(key) or type(key) is not str:
            self._logger.error("Field should be specified")
            return None
        if key in self._masked_fields:
            self._logger.error("Cannot change '{}' field".format(key))
            return None
        if not bool(value):
            return self.wipe(key)
        key = key.upper()
        value = str(value)
        if key == 'NETWORK':
            PREFIX = self.get('PREFIX')
            NETMASK = self.get('NETMASK')
            if not bool(PREFIX):
                self._logger.error("Wrong prefix '{}' in db".format(PREFIX))
                return None
            NETWORK = self._get_net(value, PREFIX)
            if not bool(NETWORK):
                self._logger.error("Cannot compute NETWORK for entered '{}'".format(value))
                return None
            json = {'NETWORK': NETWORK, 'PREFIX': PREFIX, 'NETMASK': NETMASK}
            need_update = True
        elif key == 'PREFIX':
            PREFIX, NETMASK = self._calc_prefix_mask(value, '')
            if not PREFIX:
                self._logger.error("Cannot convert PREFIX={} to PREFIX and NETMASK".format(value))
                return None
            NETWORK = self.get('NETWORK')

            NETWORK = self._get_net(NETWORK, PREFIX)
            if not bool(NETWORK):
                self._logger.error("Cannot compute NETWORK for prefix = '{}'".format(value))
                raise RuntimeError
            if not self._set_uplimit_ip(PREFIX):
                raise RuntimeError
            json = {'NETWORK': NETWORK, 'PREFIX': PREFIX, 'NETMASK': NETMASK}
            need_update = True
        elif key == 'NETMASK':
            PREFIX, NETMASK = self._calc_prefix_mask(33, value)
            if not PREFIX:
                self._logger.error("Cannot convert NETMASK=\"{}\" to PREFIX and NETMASK".format(value))
                return None
            NETWORK = self.get('NETWORK')
            NETWORK = self._get_net(NETWORK, PREFIX)
            if not bool(NETWORK):
                self._logger.error("Cannot compute NETWORK  for".format(value))
                raise RuntimeError
            if not self._set_uplimit_ip(PREFIX):
                raise RuntimeError
            json = {'NETWORK': NETWORK, 'PREFIX': PREFIX, 'NETMASK': NETMASK}
            need_update = True
        else:
            json = {key: value}
        ret = self._mongo_collection.update({'_id': self._id}, {'$set': json}, multi=False, upsert=False)
        if need_update:
            self.update_nodes(json)
        return not ret['err']

    def get(self, key):
        if not key or type(key) is not str:
            return None
        if key in self._masked_fields:
            return None
        key = key.upper()
        obj_json = self._get_json()
        try:
            return obj_json[key]
        except:
            return None

    def wipe(self, key):
        if not key or type(key) is not str:
            return None
        key = key.upper()
        cant_delete_fields = []
        cant_delete_fields.extend(self._masked_fields)
        cant_delete_fields.extend(['NETWORK'])
        if key in cant_delete_fields:
            self._logger.error("Cannot delete field '{}'".format(key))
            return None
        if key == 'PREFIX':
            if not self.get('NETMASK'):
                self._logger.error("Cannot delete field '{}' as no NETMASK configured".format(key))
                return None
        if key == 'NETMASK':
            if not self.get('PREFIX'):
                self._logger.error("Cannot delete field '{}' as no PREFIX configured".format(key))
                return None
        obj_json = self._get_json()
        try:
            obj_json[key]
        except:
            return None
        ret = self._mongo_collection.update({'_id': self._id},{'$unset': {key: ''}}, multi=False, upsert=False)
        return not ret['err']
    
    def get_json(self):
        obj_json = self._get_json()
        for elem in self._masked_fields:
            try:
                obj_json.pop(elem)
            except:
                pass
        return obj_json


    def dump(self):
        obj_json = self.get_json()
        out = ""
        for key in obj_json.keys():
            out += "{}=\"{}\"".format(key, obj_json[key]) + '\n'
        return out.strip()

    def replace(self, net_json):
        pass

    def update_nodes(self, net_json):
        pass

#    def reserve_ip(self, ip = None):
#        import struct, socket
#        network = self._get_json()['NETWORK']
#        net_num = struct.unpack('>L', (socket.inet_aton(network)))[0]
#        if type(ip) == str:
#            try:
#                ip_num = struct.unpack('>L', (socket.inet_aton(ip)))[0]
#                ip = ip_num - net_num
#            except:
#                self._logger.error("No valid IP entered")
#                raise RuntimeError
#        if bool(ip):
#            relative_ip_num = self._get_ip(ip)
#        else:
#            relative_ip_num = self._get_next_ip()
#        if not relative_ip_num:
#            return None
#        ip_new = net_num + relative_ip_num
#        return socket.inet_ntoa(struct.pack('>L', (ip_new)))



    def _get_next_ip(self):
        obj_json = self._get_json()
        freelist = obj_json['freelist']
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
        freelist = obj_json['freelist']
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
        freelist = obj_json['freelist']
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
        if bool(ip):
            return self._get_ip(ip)
        return self._get_next_ip()

    def release_ip(self, num):
        insert_elem = {'start': num, 'end': num}
        obj_json = self._get_json()
        freelist = obj_json['freelist']
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
        if num <= self._upborder and num > freelist[-1]['end']:
            filled_list.extend([insert_num])
        if len(freelist) == len(filled_list):
            self._logger.error("Cannot release IP. No place for '{}' in list: ''".format(num, freelist))
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


        

if __name__ == "__main__":
    import doctest
    doctest.testmod()
