#!/usr/bin/env python
import luna
import libtorrent
import os
import threading
import logging
import datetime
import Queue
import pwd, grp


logger = logging.getLogger('luna-tracker')
torrents = []
running_torrents = {}

flag_seed_mode = 1
flag_override_resume_data = 2
flag_upload_mode = 4
flag_share_mode = 8
flag_apply_ip_filter = 16
flag_paused = 32
flag_auto_managed = 64
flag_duplicate_is_error = 128
flag_merge_resume_trackers = 256
flag_update_subscribe = 512
flag_super_seeding = 1024
flag_sequential_download = 2048
flag_use_resume_save_path = 4096


def setup_logging(debug=False):
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

def get_now(shift = 0):
    return datetime.datetime.utcnow() + datetime.timedelta(seconds = shift)

class LunaTorrentFile(object):  
    def __init__(self, torrent_file = None):
        if not bool(torrent_file):
            logger.error("Torrent file should be specified.")
            raise RuntimeError
        if not os.path.exists(torrent_file):
            logger.error("Cannot open '{}'.".format(torrent_file))
            raise RuntimeError
        try:
            self.torrent_file_info = libtorrent.torrent_info(torrent_file)
        except:
            logger.error("File '{}' is not a torrent file.".format(orrent_file))
            raise RuntimeError
        if self.torrent_file_info.creator() != luna.torrent_key:
            logger.error("File '{}' does not belong to Luna.".format(torrent_file))
            raise RuntimeError
        files_present = self.torrent_file_info.num_files()
        if files_present != 1:
            logger.error("Torrent '{}' contains wrong numer of files: {}.".format(torrent_file, files_present))
            raise RuntimeError
        self._info = self.torrent_file_info
        self._info_hash = self._info.info_hash()
        self._path = os.path.abspath(torrent_file)
        self._basename = os.path.basename(self._path)
        self._dirname = os.path.dirname(self._path)
        self._tarball = self._info.orig_files().pop().path
        self._tarball_id = self.tarball[:36]
        self._id = self._info.comment()
        self._active = self.update_status()
        if not os.path.exists(self._dirname + "/" + self._tarball):
            logger.error("Cannot find tarball '{}' for torrent '{}'.".format(self._dirname + "/" + self._tarball, torrent_file))
            raise RuntimeError
        self._timestamp = get_now()
    @property
    def info_hash(self):
        return self._info_hash
    @property
    def info(self):
        return self._info
    @property
    def active(self):
        return self._active
    @active.setter
    def active(self, flag):
        self._active = flag
    @property
    def id(self):
        return self._id
    @property
    def path(self):
        return self._path
    @property
    def basename(self):
        return self._basename
    @property
    def tarball(self):
        return self._tarball
    @property
    def tarball_id(self):
        return self._tarball_id

    def accessed(self, set_flag = False):
        if not bool(set_flag):
            return self._timestamp
        self._timestamp = get_now()
        return self._timestamp
    def update_status(self):
        osimages = luna.list('osimage')
        for osimage_name in osimages:
            osimage = luna.OsImage(osimage_name)
            if self._id == osimage.get('torrent'):
                self._active = True
                return self._active
        self._active = False
        return self._active

def get_luna_torrents():
    osimage_names = luna.list('osimage')
    luna_torrents = {}
    for name in osimage_names:
        osimage = luna.OsImage(name)
        torr_uid = str(osimage.get('torrent'))
        osimg_name = str(osimage.name)
        tgz_id = str(osimage.get('tarball'))
        luna_torrents[torr_uid] = {}
        luna_torrents[torr_uid]['name'] = osimg_name
        luna_torrents[torr_uid]['tarball_id'] = tgz_id
    return luna_torrents

def check_path():
    options = luna.Options()
    path = options.get('path')
    if not path:
        logger.error("Path needs to be configured")
        raise RuntimeError
    path = str(path) + "/torrents"
    if not os.path.exists(path):
        logger.error("Path '{}' does not exist.".format(path))
        raise RuntimeError
    user = options.get('user')
    group = options.get('group')
    if not user:
        logger.error("User needs to be configured.")
        raise RuntimeError
    if not user:
        logger.error("Gruop needs to be configured.")
        raise RuntimeError
    try:
        user_id = pwd.getpwnam(user)
    except:
        logger.error("No such user '{}' exists.".format(user))
        raise RuntimeError
    try:
        group_id = grp.getgrnam(group)
    except:
        logger.error("No such group '{}' exists.".format(group))
        raise RuntimeError
    path_stat = os.stat(path)
    if path_stat.st_uid != user_id.pw_uid or path_stat.st_gid != group_id.gr_gid:
        logger.error("Path is not owned by '{}:{}'".format(user, group))
        raise RuntimeError
    return path

def get_torrent_files():
    global torrents
    try:
        path = check_path()
    except:
        logger.error("Error is occured with configured path.")
        return None
    files = os.listdir(path)
    os.chdir(path)
    torrents = []
    torrent_files_on_disk = {}
    for filename  in  files:
        if not (os.path.isfile(filename) and filename[-8:] == '.torrent'):
            continue
        try:
            tf = LunaTorrentFile(filename)
        except:
            logger.error("Error with parsing torrent file '{}'".format(filename))
            continue
        print tf.id, tf.tarball, tf.active, tf.accessed()
        torrent_files_on_disk[tf.id] = True
        torrents.extend([tf])

    configured_torrents = get_luna_torrents()
    for configured_torrent in configured_torrents:
        try:
            torrent_files_on_disk[configured_torrent]
        except:
            logger.error("Torrent for osimage '{}' is configured but does not exist on disk.".format(configured_torrents[configured_torrent]['name']))
    
def start_torrent_client():
    global torrents
    try:
        path = check_path()
    except:
        logger.error("Error is occured with configured path.")
        return None
    if not bool(torrents):
        logger.info("No torrents. Exiting.")
        return None
    os.chdir(path)
    options = luna.Options()
    portmin = options.get('torrent_listen_port_min') or 7052
    portmax = options.get('torrent_listen_port_max') or 7200
    print portmin
    print portmax
    try:
        t_session = libtorrent.session()
        t_session.listen_on(portmin, portmax)
    except:
        logger.error("Failed to open listening ports")
        raise RuntimeError
    #t_session.flag_share_mode = True
    #t_session.flag_seed_mode = True
    #t_session.flag_super_seeding = 1
    flags = flag_seed_mode | flag_upload_mode | flag_super_seeding | flag_auto_managed
    print flags
    parm_dict = {"save_path": "./", 'flags': flags, 'ti': torrents[0].info}
    t_session.async_add_torrent(parm_dict)
    #t_session.resume()
    #print torrents[0].id
    #print t_session.is_paused()
    #print t_session.find_torrent(torrents[0].id)
    import time
    time.sleep(60)
    return None
    for torrent in torrents:
        print torrent.info_hash, torrent.id
        logger.info("Processing torrent".format(torrent.basename))
        flags = flag_seed_mode | flag_upload_mode | flag_super_seeding | flag_auto_managed
        parm_dict = {"save_path": "./", 'flags': flags, 'ti': torrent.info}
        t_session.async_add_torrent(parm_dict)
    
            
        
    
        
    
        
    



        

if __name__ == '__main__':
    setup_logging()
    get_luna_torrents()
    get_torrent_files()
    start_torrent_client()

