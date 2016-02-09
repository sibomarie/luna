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
from luna.network import Network
from luna.osimage import OsImage
from luna.bmcsetup import BMCSetup

class Node(Base):
    """
    Class for operating with node records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, create = False, id = None, 
            group = None):
        """
        name    - can be ommited
        group   - group belongs to; should be specified
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'node'
        if not bool(name) and bool(create):
            name = self._generate_name()
        mongo_doc = self._check_name(name, create, id)
        self._keylist = {'port': type(0)}
        if create:
            options = Options()
            group = Group(group)
            mongo_doc = {'name': name, 'group': group.DBRef, 'interfaces': None, 'mac': None, 'switch': None, 'port': None}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.add_ip()
            self.add_bmc_ip()
            self.link(group)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)

    def _generate_name(self):
        options = Options()
        prefix = options.get('nodeprefix')
        digits = options.get('nodedigits')
        back_links = options.get_back_links()
        max_num = 0
        for link in back_links:
            if not link['collection'] == self._collection_name:
                continue
            node = Node(id = link['DBRef'].id)
            name = node.name
            nnode = int(name.lstrip(prefix))
            if nnode > max_num:
                max_num = nnode
        ret_name = prefix + str(max_num + 1).zfill(digits)
        return ret_name

    def add_ip(self, interface = None, reqip = None):
        if bool(reqip) and not bool(interface):
            self._logger.error("'interfaces' should be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id)
        group_interfaces = group._get_json()['interfaces']
        mongo_doc = {}
        if not bool(json['interfaces']) or not interface:
            for iface in group_interfaces:
                try:
                    if bool(json['interfaces'][iface]):
                        self._logger.error("IP already assigned on '{}'".format(iface))
                        mongo_doc[iface] = json['interfaces'][iface]
                        continue
                except:
                    pass
                ip = group._reserve_ip(iface)
                if not bool(ip):
                    self._logger.error("Cannot reserve ip for interface '{}'".format(iface))
                    return None
                mongo_doc[iface] = ip
        if bool(reqip):
            mongo_doc = json['interfaces']
            ip = group._reserve_ip(interface, reqip)
            if not bool(ip):
                self._logger.error("Cannot reserve ip for interface '{}'".format(interface))
                return None
            mongo_doc[interface] = ip
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': mongo_doc}}, multi=False, upsert=False)
        return not res['err']



    def del_ip(self, interface = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id)
        try:
            mongo_doc = json['interfaces'].copy()
        except:
            self._logger.error("No interfaces found")
            return None
        if not bool(mongo_doc):
            self._logger.error("All interfaces are already deleted")
            return None
        if not bool(interface):
            for iface in json['interfaces']:
                ip = json['interfaces'][iface]
                group._release_ip(iface, ip)
                mongo_doc.pop(iface)
            res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': mongo_doc}}, multi=False, upsert=False)
            return not res['err']
        try:
            ip = json['interfaces'][interface]
        except:
            self._logger.error("No such interface '{}' found. If it already deleted?".format(interface))
            return None
        group._release_ip(interface, ip)
        mongo_doc.pop(interface)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': mongo_doc}}, multi=False, upsert=False)
        return not res['err']

    def add_bmc_ip(self, reqip = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id)
        ip = 0
        try:
            ip = json['bmcnetwork']
        except:
            pass
        if bool(ip):
            self._logger.error("IP is already assigned on bmc network")
            return None
        ip = group._reserve_bmc_ip(reqip)
        if not bool(ip):
            self._logger.error("Cannot reserve ip for bmc interface")
            return None
        mongo_doc = ip
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': mongo_doc}}, multi=False, upsert=False)
        return not res['err']

    def del_bmc_ip(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id)
        try:
            ip = json['bmcnetwork']
        except:
            self._logger.error("No IP configured on bmc network")
            return None
        res = group._release_bmc_ip(ip)
        if bool(res):
            mongo_doc = None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': mongo_doc}}, multi=False, upsert=False)
        return not res['err']

    def set_mac(self, mac = None):
        import re
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        if type(mac) == type('') and re.match('(([a-fA-F0-9]{2}:){4}([a-fA-F0-9]{2}))', mac):
            res = self._mongo_collection.update({'_id': self._id}, {'$set': {'mac': mac}}, multi=False, upsert=False)
            return not res['err']
        return None

        

    def clear_mac(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'mac': None}}, multi=False, upsert=False)
        return not res['err']
        

    def set_switch(self, name):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        switch = switch(name)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'switch': switch.DBRef}}, multi=False, upsert=False)
        if not res['err']:
            self.link(switch.DBRef)
        return not res['err']

    def clear_switch(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        switch = switch(name)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'switch': None}}, multi=False, upsert=False)
        if not res['err']:
            self.unlink(switch.DBRef)
        return not res['err']
        
    def set_port(self, num):
        self.set('port', num)

    def delete(self):
        """
        Delete node
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
        self.del_bmc_ip()
        self.del_ip()
        ret = self._mongo_collection.remove({'_id': self._id}, multi=False)
        self._wipe_vars()
        return not ret['err']

    def get_interfaces(self):
        try:
            return self._get_json()['interfaces'].keys()
        except:
            return {}

    def get_human_ip(self, interface):
        json = self._get_json()
        group = Group(id = json['group'].id)
        try:
            ipnum = json['interfaces'][interface]
        except:
            self._logger.error("No IPADDR for interface '{}' configured".format(interface))    
            return None
        return group.get_human_ip(interface, ipnum)

    def _get_num_ip(self, interface, ip):
        json = self._get_json()
        group = Group(id = json['group'].id)
        try:
            num_ip = json['interfaces'][interface]
        except:
            self._logger.error("No such interface for node".format(interface))    
            return None
        return group.get_num_ip(interface, ip)

    def get_human_bmc_ip(self):
        json = self._get_json()
        group = Group(id = json['group'].id)
        try:
            ipnum = json['bmcnetwork']
        except:
            self._logger.error("No IPADDR for interface bmc configured")
            return None
        return group.get_human_bmc_ip(ipnum)

    def _get_num_bmc_ip(self, ip):
        json = self._get_json()
        group = Group(id = json['group'].id)
        return group.get_num_bmc_ip(ip)

class Group(Base):
    """
    Class for operating with group records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, create = False, id = None, 
            prescript = None, bmcsetup = None, bmcnetwork = None,
            partscript = None, osimage = None, interfaces = None, postscript = None):
        """
        prescript   - preinstall script
        bmcsetup    - bmcsetup options
        bmcnetwork  - used for bmc networking
        partscript  - parition script
        osimage     - osimage
        interfaces  - list of the newtork interfaces
        postscript  - postinstall script
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'group'
        mongo_doc = self._check_name(name, create, id)
        self._keylist = {'prescript': type(''), 'partscript': type(''), 'postscript': type('')}
        if create:
            options = Options()
            bmcobj = BMCSetup(bmcsetup)
            bmcnetobj = Network(bmcnetwork)
            osimageobj = OsImage(osimage)
            if bool(interfaces) and type(interfaces) is not type([]):
                self._logger.error("'interfaces' should be list") 
                raise RuntimeError
            if_dict = {}
            if not bool(interfaces):
                interfaces = []
            for interface in interfaces:
                if_dict[interface] = {'network': None, 'params': ''}
            if not bool(partscript):
                partscript = "#!/bin/bash\nmount -t ramfs ramfs /sysroot"
            if not bool(prescript):
                prescript = "#!/bin/bash"
            if not bool(postscript):
                postscript = "#!/bin/bash"
            mongo_doc = {'name': name, 'prescript':  prescript, 'bmcsetup': bmcobj.DBRef, 'bmcnetwork': bmcnetobj.DBRef,
                               'partscript': partscript, 'osimage': osimageobj.DBRef, 'interfaces': if_dict, 
                               'postscript': postscript}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
            self.link(bmcobj)
            self.link(bmcnetobj)
            self.link(osimageobj)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)
        
    def osimage(self, osimage_name):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        osimage = OsImage(osimage_name)
        old_dbref = self._get_json()['osimage']
        self.unlink(old_dbref)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'osimage': osimage.DBRef}}, multi=False, upsert=False)
        self.link(osimage.DBRef)
        return not res['err']

    def bmcsetup(self, bmcsetup_name):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        bmcsetup = BMCSetup(bmcsetup_name)
        old_dbref = self._get_json()['bmcsetup']
        self.unlink(old_dbref)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcsetup': bmcsetup.DBRef}}, multi=False, upsert=False)
        self.link(bmcsetup.DBRef)
        return not res['err']

    def bmcnetwork(self, bmcnet):
        self._logger.error("Not implemented.")
        return None
        old_bmcnet_dbref = self._get_json()['bmcnetwork']
        net = Network(bmcnet)
        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id)
            node.del_bmc_ip()
        self.unlink(old_bmcnet_dbref)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcsetup': net.DBRef}}, multi=False, upsert=False)
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id)
            node.add_bmc_ip()
        return True

    def add_interface(self, interface):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        old_parms = None
        try:
            old_parms = interfaces[interface]
        except:
            pass
        if bool(old_parms):
            self._logger.error("Interface already exists")
            return None
        interfaces[interface] = {'network': None, 'params': ''}
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if res['err']:
            self._logger.error("Error adding interface '{}'".format(interface))
            return None
        return True

    def get_if_parms(self, interface):
        interfaces = self._get_json()['interfaces']
        try:
            interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        return interfaces[interface]['parms']

    def set_if_parms(self, interface, parms = ''):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        try:
            interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        interfaces[interface]['parms'] = parms
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if res['err']:
            self._logger.error("Error setting network parameters for interface '{}'".format(interface))
            return None
        return True

    def set_net_to_if(self, interface, network):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        net = Network(network)
        old_params = None
        try:
            old_parms = interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        old_net = None
        try:
            old_net = old_parms['network']
        except:
            pass
        if bool(old_net):
            self._logger.error("Network is already defined for this interface '{}'".format(interface))
            return None
        interfaces[interface]['network'] = net.DBRef
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if res['err']:
            self._logger.error("Error adding network for interface '{}'".format(interface))
            return None
        self.link(net.DBRef)
        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id)
            node.add_ip(interface)
        return True

    def del_net_from_if(self, interface):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        old_params = None
        try:
            old_parms = interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        net_dbref = None
        try:
            net_dbref = old_parms['network']
        except:
            self._logger.error("Network is not configured for interface '{}'".format(interface))
            return None
        if not bool(net_dbref):
            self._logger.error("Network is not configured for interface '{}'".format(interface))
            return None
        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id)
            node.del_ip(interface)
        self.unlink(net_dbref)
        interfaces[interface]['network'] = None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if res['err']:
            self._logger.error("Error adding network for interface '{}'".format(interface))
            return None
        return True

    def del_interface(self, interface):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        self.del_net_from_if(interface)
        interfaces = self._get_json()['interfaces']
        interfaces.pop(interface)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if res['err']:
            self._logger.error("Error deleting interface '{}'".format(interface))
            return None
        return True

    def _reserve_ip(self, interface = None, ip = None):
        if not bool(interface):
            self._logger.error("Interface needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['interfaces'][interface]['network']
        except:
            self._logger.error("No such interface '{}'".format(interface))
            return None
        net = Network(id = net_dbref.id)
        return net.reserve_ip(ip)

            

    def _release_ip(self, interface, ip):
        if not bool(interface):
            self._logger.error("Interface needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['interfaces'][interface]['network']
        except:
            self._logger.error("No such interface '{}'".format(interface))
            return None
        net = Network(id = net_dbref.id)
        return net.release_ip(ip)

    def _reserve_bmc_ip(self, ip = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("No bmc network configured")
            return None
        net = Network(id = net_dbref.id)
        return net.reserve_ip(ip)

    def _release_bmc_ip(self, ip):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("No bmc network configured")
            return None
        net = Network(id = net_dbref.id)
        return net.release_ip(ip)

    def get_human_ip(self, interface, ipnum):
        interfaces = self._get_json()['interfaces']
        dbref = None
        try:
            dbref = interfaces[interface]
        except:
            self._logger.error("Interface is not configured for '{}'".format(interface))
            return None
        net = Network(id = dbref.id)
        return net.relnum_to_ip(ipnum)


    def get_num_ip(self, interface, ip):
        interfaces = self._get_json()['interfaces']
        dbref = None
        try:
            dbref = interfaces[interface]
        except:
            self._logger.error("Interface is not configured for '{}'".format(interface))
            return None
        net = Network(id = dbref.id)
        return net.ip_to_relnum(ip)

    def get_human_bmc_ip(self, ipnum):
        dbref = None
        try:
            dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("Interface is not configured for BMC")
            return None
        net = Network(id = dbref.id)
        return net.relnum_to_ip(ipnum)

    def get_num_bmc_ip(self, ip):
        dbref = None
        try:
            dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("Interface is not configured for BMC")
            return None
        net = Network(id = dbref.id)
        return net.ip_to_relnum(ip)
