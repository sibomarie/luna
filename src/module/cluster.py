'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

from config import *
import logging
import os
import socket
import subprocess
import pwd
import grp
from bson.dbref import DBRef
from luna.base import Base

class Cluster(Base):
    """
    Class for storing options and procedures for luna
    TODO rename to 'Cluster'
    """

    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    _logger = logging.getLogger(__name__)
    _collection_name = None
    _mongo_collection = None
    _keylist = None
    _id = None
    _name = None
    _DBRef = None
    _json = None

    def __init__(self, mongo_db = None, create = False, id = None, nodeprefix = 'node', nodedigits = 3, path = None, user = None, group = None):
        """
        Constructor can be used for creating object by setting create=True
        nodeprefix='node' and nodedigits='3' will give names like node001,
        nodeprefix='compute' and nodedigits='4' will give names like compute0001
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._logger.debug("Connecting to MongoDB.")
        self._collection_name = 'cluster'
        name = 'general'
        self._mongo_db = mongo_db
        mongo_doc = self._check_name(name, mongo_db, create, id)
        if create:
            try:
                path =  os.path.abspath(path)
            except:
                self._logger.error("No path specified.")
                raise RuntimeError
            if not os.path.exists(path):
                self._logger.error("Wrong path '{}' specified.".format(path))
                raise RuntimeError
            try:
                user_id = pwd.getpwnam(user)
            except:
                self._logger.error("No such user '{}' exists.".format(user))
                raise RuntimeError
            try:
                group_id = grp.getgrnam(group)
            except:
                self._logger.error("No such group '{}' exists.".format(group))
                raise RuntimeError
            path_stat = os.stat(path)
            if path_stat.st_uid != user_id.pw_uid or path_stat.st_gid != group_id.gr_gid:
                self._logger.error("Path is not owned by '{}:{}'".format(user, group))
                raise RuntimeError
            mongo_doc = {'name': name, 'nodeprefix': nodeprefix, 'nodedigits': nodedigits, 'user': user,
                        'debug': 0, 'path': path, 'frontend_address': '', 'frontend_port': '7050',
                        'server_port': 7051, 'tracker_interval': 10,
                        'tracker_min_interval': 5, 'tracker_maxpeers': 200,
                        'torrent_listen_port_min': 7052, 'torrent_listen_port_max': 7200, 'torrent_pidfile': '/run/luna/ltorrent.pid',
                        'lweb_pidfile': '/run/luna/lweb.pid', 'lweb_num_proc': 0, 'cluster_ips': None,
                        'named_include_file': '/etc/named.luna.zones', 'named_zone_dir': '/var/named'}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._keylist = {'nodeprefix': type(''), 'nodedigits': type(0), 'debug': type(0), 'user': type(''),
                        'path': type(''), 'frontend_address': type(''), 'frontend_port': type(0),
                        'server_port': type(0), 'tracker_interval': type(0),
                        'tracker_min_interval': type(0), 'tracker_maxpeers': type(0),
                        'torrent_listen_port_min': type(0), 'torrent_listen_port_max': type(0), 'torrent_pidfile': type(''),
                        'lweb_pidfile': type(''), 'lweb_num_proc': type(0),
                        'cluster_ips': type(''), 'named_include_file': type(''), 'named_zone_dir': type('')}

        self._logger.debug("Current instance:'{}".format(self._debug_instance()))

    def __getattr__(self, key):
        try:
            self._keylist[key]
        except:
            raise AttributeError()
        return self.get(key)

    def __setattr__(self, key, value):
        try:
            self._keylist[key]
            self.set(key, value)
        except:
            self.__dict__[key] = value

    def set(self, key, value):
        if key == 'path':
            try:
                value =  os.path.abspath(value)
            except:
                self._logger.error("No path specified.")
                return None
            if not os.path.exists(value):
                self._logger.error("Wrong path specified.")
                return None
            return super(Cluster, self).set(key, value)
        if key in ['server_address', 'tracker_address']:
            try:
                socket.inet_aton(value)
            except:
                self._logger.error("Wrong ip address specified.")
                return None
            return super(Cluster, self).set(key, value)
        if key == 'user':
            try:
                pwd.getpwnam(value)
            except:
                self._logger.error("No such user exists.")
                return None
        if key == 'cluster_ips':
            val = ''
            for ip in value.split(","):
                try:
                    socket.inet_aton(ip.strip())
                except:
                    self._logger.error("Wrong ip address specified.")
                    return None
                val += ip + ','
            val = val[:-1]
            ips = val.split(',')
            return super(Cluster, self).set(key, val)
        return super(Cluster, self).set(key, value)

    def get_cluster_ips(self):
        ips = self.get('cluster_ips')
        ips = ips.split(",")
        local_ip = ''
        for ip in ips:
            stdout = subprocess.Popen(['/usr/sbin/ip', 'addr', 'show', 'to', ip], stdout=subprocess.PIPE).stdout.read()
            if not stdout == '':
                local_ip = ip
                break
        cluster_ips = []
        cluster_ips.append(local_ip)
        for ip in ips:
            if not ip == local_ip:
                cluster_ips.append(ip)
        return cluster_ips

    def is_active(self):
        
        try:
            cluster_ips = self.get('cluster_ips')
        except:
            return True

        ip = self.get('frontend_address')
        if not ip:
            return True
        stdout = subprocess.Popen(['/usr/sbin/ip', 'addr', 'show', 'to', ip], stdout=subprocess.PIPE).stdout.read()
        if stdout:
            return True
        return False
    def is_ha(self):
        try:
            cluster_ips = self.get('cluster_ips')
        except:
            return False
        if bool(cluster_ips):
            return True
        return False

    def makedns(self):
        from luna.network import Network
        from bson.objectid import ObjectId
        from tornado import template
        import pwd
        import grp
        import os
        
        # get network _id configured for cluster
        obj_json = self._get_json()
        try:
            rev_links = obj_json[usedby_key]
        except:
            self._logger.error("No IP addresses for network '{}' configured.".format(self.name))
            return None
        netids = []
        for elem in rev_links:
            if elem == 'network':
                for netid in rev_links[elem]:
                    netids.extend([netid])

        # fill network dictionary {'netname': {'ns_hostname': 'servername', 'ns_ip': 'IP', 'hosts' {'name': 'IP'}}}
        networks = {}
        for netid in netids:
            netobj = Network(id = ObjectId(netid))
            networks[netobj.name] = {}
            master_ip = netobj.get('ns_ip')
            networks[netobj.name]['ns_hostname'] = netobj.get('ns_hostname')
            networks[netobj.name]['ns_ip'] = master_ip
            networks[netobj.name]['hosts'] = netobj.resolve_used_ips()
            # some inout for reverse zones
            # here is steps to figure out which octets in ipadresses are common for all ips in network.
            # we can not rely on mask here, as mask can not be devisible by 8 (/12, /15, /21, etc)
            arr1 = [int(elem) for elem in master_ip.split('.')]
            logical_arr1 = [True, True, True, True]
            for host in networks[netobj.name]['hosts']:
                ip = networks[netobj.name]['hosts'][host]
                arr2 = [int(elem) for elem in ip.split('.')]
                logical_arr = [ bool(arr1[n] == arr2[n]) for n in range(len(arr1))]
                logical_arr2 = [logical_arr[n] & logical_arr1[n] for n in range(len(logical_arr))]
                arr1 = arr2[:]
                logical_arr1 = logical_arr2[:]
            # get fist octet in ip adresses which is changing
            mutable_octet = [i for i in range(len(logical_arr1)) if not logical_arr1[i]][0]
            # generate zone file name
            revzonename = '.'.join(list(reversed(master_ip.split('.')[:mutable_octet]))) + ".in-addr.arpa"
            networks[netobj.name]['mutable_octet'] = mutable_octet
            networks[netobj.name]['rev_zone_name'] = revzonename

        # figure out paths
        includefile = self.get('named_include_file')
        zonedir = self.get('named_zone_dir')
        if not includefile:
            self._logger.error("named_include_file should be configured")
            return None
        if not zonedir:
            self._logger.error("named_zone_dir should be configured")
            return None

        # load templates
        tloader = template.Loader(self.get('path') + '/templates')

        # create include file for named.conf
        namedconffile = open(includefile, 'w')
        zonenames = []
        for network in networks:
            zonenames.extend([network, networks[network]['rev_zone_name']])

        namedconffile.write(tloader.load('templ_named_conf.cfg').generate(networks = zonenames))
        namedconffile.close()
        nameduid = pwd.getpwnam("named").pw_uid
        namedgid = grp.getgrnam("named").gr_gid
        os.chown(includefile, 0, namedgid)
        self._logger.info("Created '{}'".format(includefile))

        # remove zone files
        filelist = [ f for f in os.listdir(zonedir) if f.endswith(".luna.zone") ]
        for f in filelist:
            filepath = zonedir + "/" + f
            try:
                os.remove(filepath)
                self._logger.info("Removed old '{}'".format(filepath))
            except:
                self._logger.info("Unable to remove '{}'".format(filepath))
        # create zone files 
        for network in networks:
            # create zone
            z = {}
            z['master_hostname'] = networks[network]['ns_hostname']
            z['master_ip'] = networks[network]['ns_ip']
            z['serial_num'] = 1
            z['hosts'] = networks[network]['hosts']
            zonefilepath = zonedir + "/" + network + ".luna.zone"
            zonefile = open(zonefilepath, 'w')
            zonefile.write(tloader.load('templ_zone.cfg').generate(z = z))
            zonefile.close()
            os.chown(zonefilepath, nameduid, namedgid)
            self._logger.info("Created '{}'".format(zonefilepath))
            revzonepath = zonedir + "/" + networks[network]['rev_zone_name'] + ".luna.zone"
            z['master_hostname'] = networks[network]['ns_hostname'] + "." + network
            z['hosts'] = {}
            for host in networks[network]['hosts']:
                hostname = host + "." + network
                iparr = [int(elem) for elem in networks[network]['hosts'][host].split('.')]
                reverseiplist = list(reversed(iparr[networks[network]['mutable_octet']:]))
                reverseip = '.'.join([str(elem) for elem in reverseiplist])
                z['hosts'][hostname] = reverseip
            zonefile = open(revzonepath, 'w') 
            zonefile.write(tloader.load('templ_zone_arpa.cfg').generate(z = z))
            zonefile.close()
            os.chown(revzonepath, nameduid, namedgid)
            self._logger.info("Created '{}'".format(revzonepath))
        return True




