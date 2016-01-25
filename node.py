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
from luna.ifcfg import IfCfg
from luna.osimage import OsImage
from luna.bmcsetup import BMCSetup

class Node(Base):
    """
    Class for operating with node records
    """
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
        self._keylist = {}
        if create:
            options = Options()
            group = Group(group)
            mongo_doc = {'name': name, 'group': group.DBRef, 'interfaces': None}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.add_ip()
            self.link(group)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

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
                mongo_doc[iface] = {'IPADDR': ip}
        if bool(reqip):
            mongo_doc = json['interfaces']
            ip = group._reserve_ip(interface, reqip)
            if not bool(ip):
                self._logger.error("Cannot reserve ip for interface '{}'".format(interface))
                return None
            mongo_doc[interface] = {'IPADDR': ip}
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
                ip = json['interfaces'][iface]['IPADDR']
                group._release_ip(iface, ip)
                mongo_doc.pop(iface)
            res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': mongo_doc}}, multi=False, upsert=False)
            return not res['err']
        try:
            ip = json['interfaces'][interface]['IPADDR']
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
            ip = json['bmcsetup']
        except:
            pass
        if bool(ip):
            self._logger.error("IP is already assigned on bmc network")
            return None
        ip = group._reserve_bmc_ip(reqip)
        if not bool(ip):
            self._logger.error("Cannot reserve ip for bmc interface")
            return None
        mongo_doc = {'IPADDR': ip}
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': mongo_doc}}, multi=False, upsert=False)
        return not res['err']

    def del_bmc_ip(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id)
        try:
            ip = json['bmcnetwork']['IPADDR']
        except:
            self._logger.error("No IP configured on bmc network")
            return None
        res = group._release_bmc_ip(ip)
        if bool(res):
            mongo_doc = None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': mongo_doc}}, multi=False, upsert=False)
        return not res['err']

class Group(Base):
    """
    Class for operating with group records
    """
    def __init__(self, name = None, create = False, id = None, 
            prescript = None, bmcsetup = None, bmcnetwork = None,
            partscript = None, osimage = None, interfaces = None, postscript = None):
        """
        prescript   - preinstall script
        bmcsetup    - bmcsetup options
        bmcnetwork  - ifcfg options used for bmc networking
        partscript  - parition script
        osimage     - osimage
        interfaces  - dictionary of the newtork interfaces and ifcfg options:
                        {'eth0': 'ifcfg-internal', 'eth1': 'ifcfg-storage'}
        postscript  - postinstall script
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'group'
        mongo_doc = self._check_name(name, create, id)
        self._keylist = {'prescript': type(''), 'partscript': type(''), 'postscript': type('')}
        if create:
            options = Options()
            bmcobj = BMCSetup(bmcsetup)
            bmcnetobj = IfCfg(bmcnetwork)
            osimageobj = OsImage(osimage)
            if type(interfaces) is not type({}):
                self._logger.error("'interfaces' should be dictionary") 
                raise RuntimeError
            ifcfgs = {}
            ifcfgobj_arr = []
            for interface in interfaces:
                ifcfgobj = IfCfg(interfaces[interface])
                ifcfgobj_arr.extend([ifcfgobj])
                ifcfgs[interface] = ifcfgobj.DBRef
            if not bool(partscript):
                partscript = "mount -t ramfs ramfs /sysroot"
            if not bool(prescript):
                prescript = ''
            if not bool(postscript):
                postscript = ''
            mongo_doc = {'name': name, 'prescript':  prescript, 'bmcsetup': bmcobj.DBRef, 'bmcnetwork': bmcnetobj.DBRef,
                               'partscript': partscript, 'osimage': osimageobj.DBRef, 'interfaces': ifcfgs, 
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

    def add_interface(self, interface, ifcfg):
        pass
#        reverse_links = self.get_back_links()
#        for dbref in reverse_links:
#            if dbref.collection != 'node':
#                continue
#            node = Node(id=dbref.id)
#            node.release_ip(interface)

    def del_interface(self, interface):
        pass

    def change_ifcfg(self, interface, ifcfg):
        pass

    def _reserve_ip(self, interface = None, ip = None):
        if not bool(interface):
            self._logger.error("Interface needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['interfaces'][interface]
        except:
            self._logger.error("No such interface '{}'".format(interface))
            return None
        ifcfg = IfCfg(id = net_dbref.id)
        return ifcfg.reserve_ip(ip)

            

    def _release_ip(self, interface, ip):
        if not bool(interface):
            self._logger.error("Interface needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['interfaces'][interface]
        except:
            self._logger.error("No such interface '{}'".format(interface))
            return None
        ifcfg = IfCfg(id = net_dbref.id)
        return ifcfg.release_ip(ip)

    def _reserve_bmc_ip(self, ip = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("No bmc network configured")
            return None
        ifcfg = IfCfg(id = net_dbref.id)
        return ifcfg.reserve_ip(ip)

    def _release_bmc_ip(self, ip):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("No bmc network configured")
            return None
        ifcfg = IfCfg(id = net_dbref.id)
        return ifcfg.release_ip(ip)
