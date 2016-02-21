from config import *
import pymongo
import logging
import inspect
import sys
import os
import pwd
import grp
import subprocess
import threading
from bson.objectid import ObjectId
from bson.dbref import DBRef
from luna.base import Base
from luna.options import Options
import libtorrent
import uuid
#import tarfile
import shutil

class OsImage(Base):
    """
    Class for operating with osimages records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None, path = '', kernver = '', kernopts = ''):
        """
        create  - shoulld be True if we need create osimage
        path    - path to / of the image/ can be ralative, if needed (will be converted to absolute)
        kernver - kernel version (will be checked on creation)
        kernopt - kernel options
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'osimage'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        if bool(kernopts) and type(kernopts) is not str:
            self._logger.error("Kernel options should be 'str' type")
            raise RuntimeError
        self._keylist = {'path': type(''), 'kernver': type(''), 'kernopts': type(''),
                        'kernmodules': type(''), 'dracutmodules': type(''), 'tarball': type(''), 
                        'torrent': type(''), 'kernfile': type(''), 'initrdfile': type('')}
        if create:
            options = Options()
            path = os.path.abspath(path)
            path_suspected_doc = self._mongo_collection.find_one({'path': path})
            if path_suspected_doc and path_suspected_doc['path'] == path:
                self._logger.error("Cannot create 'osimage' with the same 'path' as name='{}' has".format(path_suspected_doc['name']))
                raise RuntimeError
            if kernver == 'ANY':
                try:
                    kernver = self.get_package_ver(path, 'kernel')[0]
                except:
                    pass
            if not self._check_kernel(path, kernver):
                raise RuntimeError
            mongo_doc = {'name': name, 'path': path, 'kernver': kernver, 'kernopts': kernopts}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)

    
    def list_kernels(self):
        return self.get_package_ver(self.path, 'kernel')

    def get_package_ver(self, path, package):
        import rpm
        rpm.addMacro("_dbpath", path + '/var/lib/rpm')
        ts = rpm.TransactionSet()
        package_vers = list()
        mi = ts.dbMatch( 'name', package )
        for h in mi:
            ver = "%s-%s.%s" % (h['VERSION'], h['RELEASE'], h['ARCH'])
            package_vers.extend([ver])
        return package_vers
    """
    def __getattr__(self, key):
        try:
            self._keylist[key]
        except:
            raise AttributeError()
        return self.get(key)

    def __setattr__(self, key, value):
        if key == 'path':
            kernver = self.kernver
            if not self._check_kernel(value, kernver):
                self._logger.error("No kernel-'{}' in '{}'".format(kernver, value))
                return None
        elif key == 'kernver':
            path = self.path
            if not self._check_kernel(path, value):
                self._logger.error("No kernel-'{}' in '{}'".format(kernver, value))
                return None
        try:
            self._keylist[key]
            self.set(key, value)
        except:
            self.__dict__[key] = value
        """

    def _check_kernel(self, path, kernver):
        import os
        os_image_kernvers = None
        req_kernver = None
        if not os.path.isdir(path):
            self._logger.error("{} is not valid dir".format(path))
            return None
        try:
            os_image_kernvers = self.get_package_ver(path,'kernel')
            req_kernver = os_image_kernvers.index(kernver)
        except:
            if os_image_kernvers == []:
                self._logger.error("No kernel package installed in {}".format(path))
                return None
            self._logger.error("Kernel version '{}' not in list {} from {}. Kernel Version or osimage path are incorrect?".format(kernver, os_image_kernvers, path))
            return None
        return True


    """
    @property
    def path(self):
        return self.get('path')

    @path.setter
    def path(self, value):
        self.set('path', value)
    """
    def create_tarball(self):
        # TODO check if root
        path = Options().get('path')
        if not path:
            self._logger.error("Path needs to be configured.")
            return None
        user = Options().get('user')
        if not user:
            self._logger.error("User needs to be configured.")
            return None
        group = Options().get('group')
        if not group:
            self._logger.error("Group needs to be configured.")
            return None
        path_to_store = path + "/torrents"
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = grp.getgrnam(group).gr_gid
        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)
        uid = str(uuid.uuid4())
        tarfile_path = path_to_store + "/" + uid + ".tgz"
        image_path = self.get('path')
        #tarball = tarfile.open(tarfile_path, "w:gz")
        #tarball.add(image_path, arcname=os.path.basename(image_path + "/."))
        #tarball.close()
        try:
            tar_out = subprocess.Popen(['/usr/bin/tar', 
                    '-C', image_path + '/.', 
                    '--one-file-system', 
                    '--xattrs', 
                    '--selinux', 
                    '--acls',
                    '--checkpoint=100',
                    '-c', '-z', '-f', tarfile_path, '.'], stderr=subprocess.PIPE) # dirty, but 4 times faster
            stat_symb = ['\\', '|', '/', '-']
            i = 0
            while True:
                line = tar_out.stderr.readline()
                if line == '':
                    break
                i = i + 1
                sys.stdout.write(stat_symb[i % len(stat_symb)])
                sys.stdout.write('\r')
        except:
            os.remove(tarfile_path)
            sys.stdout.write('\r')
            return None
        os.chown(tarfile_path, user_id, grp_id)
        self.set('tarball', str(uid))
        return True
    
    def set(self, key, value):
        res = super(OsImage, self).set(key, value)
        if key == 'kernver' and res:
            return self.place_bootfiles()
        return res

    def create_initrd(self):
        path = Options().get('path')
        if not path:
            self._logger.error("Path needs to be configured.")
            return None
        path_to_store = "/tmp"
        dracut_modules = self.get('dracutmodules') + " luna"
        kern_modules = self.get('kernmodules')

    def place_bootfiles(self):
        path = Options().get('path')
        if not path:
            self._logger.error("Path needs to be configured.")
            return None
        path_to_store = path + "/boot"

    def create_torrent(self):
        # TODO check if root
        tarball_uid = self.get('tarball')
        if not bool(tarball_uid):
            self._logger.error("No tarball in DB.")
            return None
        tarball = Options().get('path') + "/torrents/" + tarball_uid + ".tgz"
        if not os.path.exists(tarball):
            self._logger.error("Wrong path in DB.")
            return None
        tracker_address = Options().get('tracker_address')
        if tracker_address == '':
            self._logger.error("Tracker address needs to be configured.")
            return None
        tracker_port = Options().get('tracker_port')
        if tracker_port == 0:
            self._logger.error("Tracker port needs to be configured.")
            return None
        user = Options().get('user')
        if not user:
            self._logger.error("User needs to be configured.")
            return None
        group = Options().get('group')
        if not group:
            self._logger.error("Group needs to be configured.")
            return None
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = grp.getgrnam(group).gr_gid
        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(tarball))
        uid = str(uuid.uuid4())
        torrentfile = str(Options().get('path')) + "/torrents/" + uid
        fs = libtorrent.file_storage()
        libtorrent.add_files(fs, os.path.basename(tarball))
        t = libtorrent.create_torrent(fs)
        t.add_tracker("http://" + str(tracker_address) + ":" + str(tracker_port) + "/announce")
        t.set_creator(torrent_key)
        t.set_comment(uid)
        libtorrent.set_piece_hashes(t, ".")
        f = open(torrentfile, 'w')
        f.write(libtorrent.bencode(t.generate()))
        f.close()
        self.set('torrent', str(uid))
        os.chown(torrentfile, user_id, grp_id)
        shutil.move(torrentfile, torrentfile + ".torrent")
        os.chdir(old_cwd)
        return True


