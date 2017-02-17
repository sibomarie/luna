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

import os
import sys
import pwd
import grp
import rpm
import uuid
import shutil
import logging
import tempfile
import subprocess
import libtorrent

from platform import linux_distribution
from bson.dbref import DBRef

from luna.base import Base
from luna.cluster import Cluster


class OsImage(Base):
    """Class for operating with osimages records"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False, id=None,
                 path='', kernver='', kernopts='',
                 grab_list='grab_default_centos.lst'):
        """
        path      - path to / of the image (will be converted to absolute)
        kernver   - kernel version (will be checked on creation)
        kernopt   - kernel options
        grab_list - rsync exclude list for grabbing live node to image
        """

        self.log.debug("function args {}".format(self._debug_function()))

        # Define the schema used to represent osimage objects

        self._collection_name = 'osimage'
        self._keylist = {'path': type(''), 'kernver': type(''),
                         'kernopts': type(''), 'kernmodules': type(''),
                         'dracutmodules': type(''), 'tarball': type(''),
                         'torrent': type(''), 'kernfile': type(''),
                         'initrdfile': type(''), 'family': type(''),
                         'grab_exclude_list': type(''),
                         'grab_filesystems': type('')}

        # Check if this osimage is already present in the datastore
        # Read it if that is the case

        osimage = self._get_object(name, mongo_db, create, id)

        if bool(kernopts) and type(kernopts) is not str:
            self.log.error("Kernel options should be 'str' type")
            raise RuntimeError

        if create:
            cluster = Cluster(mongo_db=self._mongo_db)
            path = os.path.abspath(path)

            duplicate = self._mongo_collection.find_one({'path': path})
            if duplicate:
                self.log.error("Path belongs to osimage '{}'"
                               .format(duplicate['name']))
                raise RuntimeError

            if not os.path.isdir(path):
                self.log.error("'{}' is not a valid directory".format(path))
                raise RuntimeError

            real_root = os.open("/", os.O_RDONLY)
            os.chroot(path)
            dist = linux_distribution(supported_dists=('debian', 'redhat'))
            os.fchdir(real_root)
            os.chroot(".")
            os.close(real_root)

            if dist[0].lower() in ['debian', 'ubuntu']:
                self._family = 'debian'
            elif dist[0].lower() in ['centos linux', 'fedora', 'redhat']:
                self._family = 'redhat'

            kernels = self.get_package_ver(path, 'kernel')
            if not kernels:
                self.log.error("No kernels installed in '{}'".format(path))
                raise RuntimeError
            elif not kernver:
                kernver = kernels[0]
            elif kernver not in kernels:
                self.log.error("Available kernels are '{}'".format(kernels))
                raise RuntimeError

            grab_list_path = cluster.get('path') + '/templates/' + grab_list
            if not os.path.isfile(grab_list_path):
                self.log.error("'{}' is not a file.".format(grab_list_path))
                raise RuntimeError

            with open(grab_list_path) as lst:
                grab_list_content = lst.read()

            # Store the new osimage in the datastore

            osimage = {'name': name, 'path': path, 'family': self._family,
                       'kernver': kernver, 'kernopts': kernopts,
                       'dracutmodules': 'luna,-i18n,-plymouth',
                       'kernmodules': 'ipmi_devintf,ipmi_si,ipmi_msghandler',
                       'grab_exclude_list': grab_list_content,
                       'grab_filesystems': '/,/boot'}

            self.log.debug("Saving osimage '{}' to the datastore"
                           .format(osimage))

            self.store(osimage)

            # Link this osimage to its dependencies and the current cluster

            self.link(cluster)

        self.log = logging.getLogger(__name__ + '.' + self._name)

    def list_kernels(self):
        return self.get_package_ver(self.get('path'), 'kernel')

    def get_package_ver(self, path, package):
        versions = list()

        try:
            family = self._family
        except AttributeError:
            family = self.get('family')

        if family == 'debian':
            cmd = ("dpkg --admindir=" + path + "/var/lib/dpkg -l "
                   "| awk '/^.i +linux-image-extra/ && $2~/[0-9]/ {print $2}' "
                   "| cut -d'-' -f4- | sort -r")
            ps = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            out = ps.communicate()[0].strip().splitlines()
            versions.extend(out)

        elif family == 'redhat':
            rpm.addMacro("_dbpath", path + '/var/lib/rpm')
            ts = rpm.TransactionSet()
            try:
                mi = ts.dbMatch('name', package)
                for h in mi:
                    version = "%s-%s.%s" % (h['VERSION'],
                                            h['RELEASE'], h['ARCH'])
                    versions.append(version)
            except rpm.error:
                versions = []

        return versions

    def create_tarball(self):
        # TODO check if root
        cluster = Cluster(mongo_db=self._mongo_db)
        path = cluster.get('path')
        user = cluster.get('user')
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid

        path_to_store = path + "/torrents"
        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)
            os.chmod(path_to_store, 0644)

        uid = str(uuid.uuid4())
        tarfile = path_to_store + "/" + uid + ".tgz"
        image_path = self.get('path')

        try:
            # dirty, but 4 times faster
            tar_out = subprocess.Popen(['/usr/bin/tar',
                                        '-C', image_path + '/.',
                                        '--one-file-system',
                                        '--xattrs',
                                        '--selinux',
                                        '--acls',
                                        '--checkpoint=100',
                                        '-c', '-z', '-f', tarfile, '.'],
                                       stderr=subprocess.PIPE)

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
            os.remove(tarfile)
            sys.stdout.write('\r')
            return None

        os.chown(tarfile, user_id, grp_id)
        os.chmod(tarfile, 0644)
        self.set('tarball', str(uid))

        return True

    def create_torrent(self):
        # TODO check if root
        tarball_uid = self.get('tarball')
        if not tarball_uid:
            self.log.error("No tarball in DB.")
            return None

        cluster = Cluster(mongo_db=self._mongo_db)
        tarball = cluster.get('path') + "/torrents/" + tarball_uid + ".tgz"
        if not os.path.exists(tarball):
            self.log.error("Wrong path in DB.")
            return None

        tracker_address = cluster.get('frontend_address')
        if tracker_address == '':
            self.log.error("Tracker address needs to be configured.")
            return None

        tracker_port = cluster.get('frontend_port')
        if tracker_port == 0:
            self.log.error("Tracker port needs to be configured.")
            return None

        user = cluster.get('user')
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid

        old_cwd = os.getcwd()
        os.chdir(os.path.dirname(tarball))

        uid = str(uuid.uuid4())
        torrentfile = cluster.get('path') + "/torrents/" + uid + ".torrent"

        fs = libtorrent.file_storage()
        libtorrent.add_files(fs, os.path.basename(tarball))
        t = libtorrent.create_torrent(fs)
        t.add_tracker(("http://" + str(tracker_address) +
                       ":" + str(tracker_port) + "/announce"))

        t.set_creator(torrent_key)
        t.set_comment(uid)
        libtorrent.set_piece_hashes(t, ".")

        f = open(torrentfile, 'w')
        f.write(libtorrent.bencode(t.generate()))
        f.close()
        os.chown(torrentfile, user_id, grp_id)

        self.set('torrent', str(uid))
        os.chdir(old_cwd)

        return True

    def pack_boot(self):
        def mount(source, target, fs):
            subprocess.Popen(['/usr/bin/mount', '-t', fs, source, target])

        def umount(source):
            subprocess.Popen(['/usr/bin/umount', source])

        def prepare_mounts(path):
            mount('devtmpfs', path + '/dev', 'devtmpfs')
            mount('proc', path + '/proc', 'proc')
            mount('sysfs', path + '/sys', 'sysfs')

        def cleanup_mounts(path):
            umount(path + '/dev')
            umount(path + '/proc')
            umount(path + '/sys')

        tmp_path = '/tmp'  # in chroot env
        image_path = self.get('path')
        kernver = self.get('kernver')
        kernfile = self.name + '-vmlinuz-' + kernver
        initrdfile = self.name + '-initramfs-' + kernver

        cluster = Cluster(mongo_db=self._mongo_db)
        path = cluster.get('path')
        user = cluster.get('user')

        path_to_store = path + "/boot"
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid

        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)

        modules_add = []
        modules_remove = []
        drivers_add = []
        drivers_remove = []

        dracutmodules = self.get('dracutmodules')
        if dracutmodules:
            for i in dracutmodules.split(','):
                if i[0] != '-':
                    modules_add.extend(['--add', i])
                else:
                    modules_remove.extend(['--omit', i[1:]])

        kernmodules = self.get('kernmodules')
        if kernmodules:
            for i in kernmodules.split(','):
                if i[0] != '-':
                    drivers_add.extend(['--add-drivers', i])
                else:
                    drivers_remove.extend(['--omit-drivers', i[1:]])

        prepare_mounts(image_path)

        try:
            dracut_modules = subprocess.Popen(['/usr/sbin/chroot', image_path,
                                               'dracut', '--kver', kernver,
                                               '--list-modules'],
                                              stdout=subprocess.PIPE)
            luna_exists = False
            while dracut_modules.poll() is None:
                line = dracut_modules.stdout.readline()
                if line.strip() == 'luna':
                    luna_exists = True

            if not luna_exists:
                self.log.error("No luna dracut module in osimage '{}'"
                               .format(self.name))
                raise RuntimeError

            dracut_cmd = (['/usr/sbin/chroot', image_path,
                           'dracut', '--force', '--kver', kernver] +
                          modules_add + modules_remove + drivers_add +
                          drivers_remove + [tmp_path + '/' + initrdfile])

            create = subprocess.Popen(dracut_cmd, stdout=subprocess.PIPE)
            while create.poll() is None:
                line = create.stdout.readline()

        except:
            self.log.error("Error while building initrd.")
            cleanup_mounts(image_path)
            return None

        cleanup_mounts(image_path)

        shutil.copy(image_path + tmp_path + '/' + initrdfile, path_to_store)
        shutil.copy(image_path + '/boot/vmlinuz-' + kernver,
                    path_to_store + '/' + kernfile)
        os.chown(path_to_store + '/' + initrdfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + initrdfile, 0644)
        os.chown(path_to_store + '/' + kernfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + kernfile, 0644)

        self.set('kernfile', kernfile)
        self.set('initrdfile', initrdfile)

    def copy_boot(self):
        tmp_path = '/tmp'  # in chroot env
        image_path = self.get('path')
        kernver = self.get('kernver')
        initrdfile = self.name + '-initramfs-' + kernver
        kernfile = self.name + '-vmlinuz-' + kernver

        cluster = Cluster(mongo_db=self._mongo_db)

        user = cluster.get('user')
        user_id = pwd.getpwnam(user).pw_uid
        grp_id = pwd.getpwnam(user).pw_gid

        path = cluster.get('path')
        path_to_store = path + "/boot"

        if not os.path.exists(path_to_store):
            os.makedirs(path_to_store)
            os.chown(path_to_store, user_id, grp_id)

        shutil.copy(image_path + '/boot/initramfs-' + kernver + '.img',
                    path_to_store + '/' + initrdfile)
        shutil.copy(image_path + '/boot/vmlinuz-' + kernver,
                    path_to_store + '/' + kernfile)
        os.chown(path_to_store + '/' + initrdfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + initrdfile, 0644)
        os.chown(path_to_store + '/' + kernfile, user_id, grp_id)
        os.chmod(path_to_store + '/' + kernfile, 0644)

        self.set('kernfile', kernfile)
        self.set('initrdfile', initrdfile)

        self.log.warning(("Boot files were copied, but luna modules might not "
                          "have been added to initrd. Please check "
                          "/etc/dracut.conf.d in the image"))
        return True

    def grab_host(self, host, dry_run=True, verbose=False):
        grab_exclude_list = self.get('grab_exclude_list')
        grab_filesystems = self.get('grab_filesystems')
        osimage_path = self.get('path')

        # chech if we can proceed

        if grab_exclude_list is None:
            self.log.error('No grab_exclude_list defined for osimage.')
            return None

        if grab_filesystems is None:
            self.log.error('No grab_filesystems defined for osimage.')
            return None

        # grab_filesystems will be an array with a single element at least '/'

        if grab_filesystems:
            grab_filesystems = grab_filesystems.split(',')
        else:
            grab_filesystems = ['/']

        # Create temp file with exclude content
        file_prefix = self.name + '.excl_list.rsync.'
        file_desc, exclude_file_name = tempfile.mkstemp(prefix=file_prefix)

        with open(exclude_file_name, 'a') as ex_file:
            ex_file.write(grab_exclude_list)

        # Construct rsync command line

        rsync_opts = r'''-avxz -HAX '''
        rsync_opts += r'''-e "/usr/bin/ssh -o StrictHostKeyChecking=no '''
        rsync_opts += r'''-o UserKnownHostsFile=/dev/null" '''
        rsync_opts += r'''--progress --delete --exclude-from='''
        rsync_opts += exclude_file_name + r''' '''

        if dry_run:
            rsync_opts += r''' --dry-run '''
            verbose = True

        # enumarete all filesystems
        for fs in grab_filesystems:
            ret_code = 0

            # Sanitize fs

            fs = fs.strip()
            if not fs:
                continue

            # Use absolute path

            if fs[-1] != '/':
                fs += '/'
            if fs[0] != '/':
                fs = '/' + fs
            self.log.info("Fetching {} from {}".format(fs, host))

            # Path on master where to grab. Create it locally if needed

            local_fs = osimage_path + fs
            if not os.path.exists(local_fs) and not dry_run:
                os.makedirs(local_fs)

            # Rsync comand. Finally

            cmd = r'''/usr/bin/rsync ''' + rsync_opts + r''' root@''' + host
            cmd += r''':''' + fs + r''' ''' + local_fs

            if verbose:
                self.log.info('Running command: {}'.format(cmd))

            try:
                rsync_out = subprocess.Popen(cmd, shell=True,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

                # Status symbols
                stat_symb = ['\\', '|', '/', '-']

                i = 0
                while True:
                    line = rsync_out.stdout.readline()

                    if verbose:
                        self.log.info(line.strip())
                    else:
                        # Draw status symbols
                        i = i + 1
                        sys.stdout.write(stat_symb[i % len(stat_symb)])
                        sys.stdout.write('\r')

                    # No lines in output? Exit.
                    if not line:
                        rsync_stdout, rsync_err = rsync_out.communicate()
                        ret_code = rsync_out.returncode
                        break

                # If exit code of rsync is not 0, print stderr
                if ret_code:
                    for l in rsync_err.split('\n'):
                        self.log.error(l)

            # Ctrl+C
            except KeyboardInterrupt:
                sys.stdout.write('\r')
                self.log.error('Interrupt.')
                ret_code = 1

            if ret_code:
                break

        self.log.info('Success.')

        # remove temp file
        os.remove(exclude_file_name)
