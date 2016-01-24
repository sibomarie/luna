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
from luna.node import Node


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

    def _reserve_ip(self, interface, ip)
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

