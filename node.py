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
    def __init__(self, name = None, mongo_db = None, create = False, id = None, 
            group = None):
        """
        name    - can be ommited
        group   - group belongs to; should be specified
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'node'
        if not bool(name) and bool(create):
            name = self._generate_name()
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = {'port': type(0)}
        if create:
            options = Options()
            group = Group(group)
            mongo_doc = {'name': name, 'group': group.DBRef, 'interfaces': None, 'mac': None, 'switch': None, 'port': None}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            for interface in group._get_json()['interfaces']:
                self.add_ip(interface)
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

    def change_group(self, new_group_name = None):
        if not bool(new_group_name):
            self._logger.error("Group needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        new_group = Group(new_group_name)
        json = self._get_json()
        old_group = Group(id = json['group'].id)
        old_group_interfaces = old_group._get_json()['interfaces']
        for interface in old_group_interfaces:
            self.del_ip(interface)
        self.del_bmc_ip()
        self.unlink(old_group)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'group': new_group.DBRef}}, multi=False, upsert=False)
        self.link(new_group)
        self.add_bmc_ip()
        new_group_interfaces = new_group._get_json()['interfaces']
        for interface in new_group_interfaces:
            self.add_ip(interface)
        return True

    def change_ip(self, interface = None, reqip = None):
        if not bool(interface):
            self._logger.error("'interfaces' should be specified")
            return None
        if not bool(reqip):
            self._logger.error("IP address should be specified")
            return None
        self_group_name = self._get_json()['group']
        group = Group(id = self_group_name.id)
        if not bool(group.get_num_ip(interface, reqip)):
            return None
        if self.del_ip(interface):
            return self.add_ip(interface, reqip)
        return None

    def change_bmc_ip(self, reqip = None):
        if not bool(reqip):
            self._logger.error("IP address should be specified")
            return None
        self_group_name = self._get_json()['group']
        group = Group(id = self_group_name.id)
        if not bool(group.get_num_bmc_ip(reqip)):
            return None
        if self.del_bmc_ip():
            return self.add_bmc_ip(reqip)
        return None
        

    def add_ip(self, interface = None, reqip = None):
        if not bool(interface):
            self._logger.error("'interface' should be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id)
        group_interfaces = group._get_json()['interfaces']
        node_interfaces = None
        try:
            node_interfaces = json['interfaces']
        except:
            pass
        try:
            group_interfaces[interface]
        except:
            self._logger.error("No such interface '{}' for group configured.".format(interface))
            return None
        old_ip = None
        try:
            old_ip = node_interfaces[interface]
        except:
            pass
        if bool(old_ip):
            self._logger.error("IP is already configured for interface '{}'.".format(interface))
            return None
        if not bool(node_interfaces):
            node_interfaces = {}
        ip = group._reserve_ip(interface, reqip)
        if not bool(ip):
            self._logger.error("Cannot reserve ip for interface '{}'.".format(interface))
            return None
        node_interfaces[interface] = ip

        """
        if not bool(mongo_doc) or not interface:
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
        """
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': node_interfaces}}, multi=False, upsert=False)
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
            return True
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
        back_links = self.get_back_links(resolve=True)
        if len(back_links) > 0:
            #back_links = self.get_back_links(resolve=True)
            self._logger.error("Current object is being written as a dependency for the following objects:")
            for elem in back_links:
                self._logger.error(json.dumps(elem, sort_keys=True ))
            return None
        links = self.get_links(resolve=True)
        for link in links:
            self.unlink(link['DBRef'])
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

    # TODO
    @property
    def prescript(self):
        pass
    @property
    def bmcsetup(self):
        pass
    @property
    def partscript(self):
        pass
    @property
    def downloadscript(self):
        pass
    @property
    def netconfigscript(self):
        pass
    @property
    def postscript(self):
        pass
    @property
    def kernel(self):
        
        
        return "compute-vmlinuz-3.10.0-327.3.1.el7.x86_64"
    @property
    def initrd(self):
        return "compute-initramfs-3.10.0-327.3.1.el7.x86_64"
    @property
    def kernopts(self):
        return 'luna.ip=enp0s3:10.141.0.1:16' # luna.ip=dhcp
        return "ip=10.141.0.1::10.24.255.254:255.255.0.0:node001:enp0s3:on"
    @property
    def boot_params(self):
        """
        will return dictionary with all needed params for booting:
        kernel, initrd, kernel opts, ip, net, prefix
        """
        params = {}
        group = Group(id = self.get('group').id, mongo_db = self._mongo_db)
        group_params = group.boot_params()
        params['boot_if'] = group_params['boot_if']
        params['kernel_file'] = group_params['kernel_file']
        params['initrd_file'] = group_params['initrd_file']
        params['kern_opts'] = group_params['kern_opts']
        params['boot_if'] = group_params['boot_if']
        params['net_prefix'] = group_params['net_prefix']
        if (params['boot_if']):
            params['ip'] = self.get_human_ip(params['boot_if'])
        return params






class Group(Base):
    """
    Class for operating with group records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None, 
            prescript = None, bmcsetup = None, bmcnetwork = None,
            partscript = None, osimage = None, interfaces = None, postscript = None, boot_if = None, torrent_if = None):
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
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = {'prescript': type(''), 'partscript': type(''), 'postscript': type(''), 'boot_if': type(''), 'torrent_if': type('')}
        if create:
            options = Options()
            (bmcobj, bmcnetobj) = (None, None)
            if bool(bmcsetup):
                bmcobj = BMCSetup(bmcsetup).DBRef
            if bool(bmcnetwork):
                bmcnetobj = Network(bmcnetwork).DBRef
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
            mongo_doc = {'name': name, 'prescript':  prescript, 'bmcsetup': bmcobj, 'bmcnetwork': bmcnetobj,
                               'partscript': partscript, 'osimage': osimageobj.DBRef, 'interfaces': if_dict, 
                               'postscript': postscript, 'boot_if': boot_if, 'torrent_if': torrent_if}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
            if bmcobj:
                self.link(bmcobj)
            if bmcnetobj:
                self.link(bmcnetobj)
            self.link(osimageobj)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger('group.' + self._name)
        
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

    def set_bmcnetwork(self, bmcnet):
        old_bmcnet_dbref = self._get_json()['bmcnetwork']
        net = Network(bmcnet)
        reverse_links = self.get_back_links()
        if bool(old_bmcnet_dbref):
            self._logger.error("Network is already defined for BMC interface")
            return None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': net.DBRef}}, multi=False, upsert=False)
        self.link(net.DBRef)
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id)
            node.add_bmc_ip()
        return not res['err']

    def del_bmcnetwork(self):
        old_bmcnet_dbref = self._get_json()['bmcnetwork']
        if bool(old_bmcnet_dbref):
            reverse_links = self.get_back_links()
            for link in reverse_links:
                if link['collection'] != 'node':
                    continue
                node = Node(id=link['DBRef'].id)
                node.del_bmc_ip()
            self.unlink(old_bmcnet_dbref)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': None}}, multi=False, upsert=False)
        return not res['err']

    
    def show_bmc_if(self, brief = False):
        bmcnetwork = self._get_json()['bmcnetwork']
        if not bool(bmcnetwork):
            return ''
        (NETWORK, PREFIX) = ("", "")
        try:
            net = Network(id = bmcnetwork.id)
            NETWORK = net.get('NETWORK')
            PREFIX =  str(net.get('PREFIX'))
        except:
            pass
        if brief:
            return "[" +net.name + "]:"+ NETWORK + "/" + PREFIX
        return NETWORK + "/" + PREFIX



    def show_if(self, interface, brief = False):
        interfaces = self._get_json()['interfaces']
        try:
            params = interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return ""
        (outstr, NETWORK, PREFIX) = ("", "", "")
        try:
            net = Network(id = params['network'].id)
            NETWORK = net.get('NETWORK')
            PREFIX =  str(net.get('PREFIX'))
        except:
            pass
        if NETWORK:
            if brief:
                return "[" +net.name + "]:" + NETWORK + "/" + PREFIX
            outstr = "NETWORK=" + NETWORK + "\n"
            outstr += "PREFIX=" + PREFIX
        if params['params'] and not brief:
            outstr += "\n" + params['params']
        return outstr.rstrip()

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
        return interfaces[interface]['params']

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
        interfaces[interface]['params'] = parms
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
            dbref = interfaces[interface]['network']
        except:
            self._logger.error("Interface is not configured for '{}'".format(interface))
            return None
        net = Network(id = dbref.id)
        return net.relnum_to_ip(ipnum)


    def get_num_ip(self, interface, ip):
        interfaces = self._get_json()['interfaces']
        dbref = None
        try:
            dbref = interfaces[interface]['network']
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

    def boot_params(self):
        params = {}
        params['boot_if'] = None
        params['net_prefix'] = None
        osimage = OsImage(id = self.get('osimage').id, mongo_db = self._mongo_db)
        try:
            params['kernel_file'] = osimage.get('kernfile')
        except:
            params['kernel_file'] = ""
        try:
            params['initrd_file'] = osimage.get('initrdfile')
        except:
            params['initrd_file'] = ""
        try:
            params['kern_opts'] = osimage.get('kernopts')
        except:
            params['kern_opts'] = ""
        try:
            params['boot_if'] = self.get('boot_if')
        except:
            params['boot_if'] = ""
            params['net_prefix'] = ""
            return params
        interfaces = self._get_json()['interfaces']
        try:
            if_params = interfaces[params['boot_if']]
        except:
            self._logger.error("Boot interface '{}' does not present in configured interface list '{}'.".format(params['boot_if'], interfaces.keys()))
            params['boot_if'] = ""
            params['net_prefix'] = ""
            return params
        net = None
        try:
            if_net = if_params['network']
            net = Network(id = if_net.id)
        except:
            pass
        if not bool(net):
            self._logger.error("Boot interface '{}' has no network configured".format(params['boot_if']))
            params['boot_if'] = ""
            params['net_prefix'] = ""
            return params
        params['net_prefix'] = net.get('PREFIX')
        return params

        


            

