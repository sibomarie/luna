#!/usr/bin/env python
import luna
import libtorrent as lt
import os
import threading
import logging
import datetime
import Queue
import pwd, grp
import time


logger = logging.getLogger('luna-torrent')
torrents = {}
#running_torrents = {}
t_session = None

SOFTTIMEOUT = 15
HARDTIMEOUT = 60
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
            self.torrent_file_info = lt.torrent_info(torrent_file)
        except:
            logger.error("File '{}' is not a torrent file.".format(torrent_file))
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
        self._tarball_id = self._tarball[:36]
        self._id = self._info.comment()
        self._active = self.update_status()
        if not os.path.exists(self._dirname + "/" + self._tarball):
            logger.error("Cannot find tarball '{}' for torrent '{}'.".format(self._dirname + "/" + self._tarball, torrent_file))
            raise RuntimeError
        self._timestamp = get_now()
        self._need_to_delete = False
        self._duplicate = False
        self._uploaded = 0

    def __repr__(self):
        return str({'id': self._id,
                'tarball_id': self._tarball_id,
                'tarball': self._tarball,
                'info_hash': str(self._info_hash),
                'info': self._info,
                'active': self._active,
                'need_to_delete': self._need_to_delete,
                'accessed': self._timestamp
            })
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
    def need_to_delete(self):
        return self._need_to_delete
    @need_to_delete.setter
    def need_to_delete(self, flag):
        self._need_to_delete = flag
    @property
    def duplicate(self):
        return self._duplicate
    @duplicate.setter
    def duplicate(self, flag):
        self._duplicate = flag
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
    @property
    def uploaded(self):
        return self._uploaded
    @uploaded.setter
    def uploaded(self, val):
        self._uploaded = val
    @property
    def become_inactive(self):
        return self._become_inactive
    @become_inactive.setter
    def become_inactive(self, val):
        self._become_inactive = val

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
                self._become_inactive = None
                return self._active
        self._active = False
        self._become_inactive = get_now()
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

def update_torrents():
    global torrents
    try:
        path = check_path()
    except:
        logger.error("Error is occured with configured path.")
        return None
    files = os.listdir(path)
    os.chdir(path)
    torrent_files_on_disk = {}
    for filename  in  files:
        try:
            file_extention = filename[-8:]
        except:
            logger.error("File '{}' seems not to be a torrent file".forman(filename))
            continue
        if not (os.path.isfile(filename) and file_extention == '.torrent'):
            continue
        try:
            tf = LunaTorrentFile(filename)
        except:
            logger.error("Error with parsing torrent file '{}'".format(filename))
            continue
        #torrent_files_on_disk[tf.id] = True
        try:
            old_tf = torrents[tf.id]
            if tf.info_hash.as_string() != old_tf.info_hash.as_string():
                logger.error("Was '{}' replaced? It has the same name but different info_hash.".format(filename))
                continue
        except: 
            logger.info("New torrent file was found. '{}'".format(filename))
            torrents[tf.id] = tf
    find_old_torrents()
    find_duplicates()
    for uid in torrents:
        if torrents[uid].duplicate == True:
            logger.info("Duplicate torrent file '{}'".format(torrents[uid].basename))
    return True

def find_duplicates():
    duplicates = {}
    for file_id in torrents:
        tf = torrents[file_id]
        info_hash = str(tf.info_hash)
        try:
            duplicates[info_hash]
        except:
            duplicates[info_hash] = False
            continue
        duplicates[info_hash] = True
    for file_id in torrents:
        tf = torrents[file_id]
        if duplicates[str(tf.info_hash)] and not tf.active:
            logger.info("Duplicate '{}' info_hash was found in '{}'.".format(str(tf.info_hash), tf.basename))
            torrents[file_id].duplicate = True
            continue
        if duplicates[str(tf.info_hash)]:
            logger.info("Duplicate info_hash '{}' was found for this active torrent '{}'.".format(info_hash, tf.basename))
    # revert duplicate flag for one of inactive torrents
    for uid in duplicates:
        if not duplicates[uid]:
            continue
        find_dup = False
        for file_id in torrents:
            if find_dup:
                continue
            if str(torrents[file_id].info_hash) == uid:
                logger.info("For duplicate info_hash '{}' will submit torrent '{}'.".format(info_hash, torrents[file_id].basename))
                torrents[file_id].duplicate = False
                find_dup = True

    
def find_old_torrents():
    global torrents
    configured_torrents = get_luna_torrents()
    for configured_torrent in configured_torrents:
        try:
            torrents[configured_torrent]
        except:
            logger.error("Torrent for osimage '{}' is configured but does not exist on disk.".format(configured_torrents[configured_torrent]['name']))
    for file_id in torrents:
        tf = torrents[file_id]
        try:
            configured_torrents[tf.id]
        except:
            if tf.active:
                logger.error("Torrent '{}' was deleted from luna DB.".format(tf.id))
            tf.active = False

def start_torrent_client():
    global t_session
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
    try:
        t_session = lt.session()
    except:
        logger.error("Failed to open libtorrent session.")
        raise RuntimeError
    try:
        t_session.listen_on(portmin, portmax)
    except:
        logger.error("Failed to open listening ports.")
        raise RuntimeError
    #t_session.flag_share_mode = True
    #t_session.flag_seed_mode = True
    #t_session.flag_super_seeding = 1
    flags = flag_seed_mode | flag_upload_mode | flag_super_seeding
    parm_dict = {"save_path": str(options.get('path')) + "/torrents", 'flags': flags}
    #t_session.async_add_torrent(parm_dict)
    #t_session.resume()
    #print torrents[0].id
    #print t_session.is_paused()
    #print t_session.find_torrent(torrents[0].id)
    for tf in torrents:
        if torrents[tf].duplicate:
            continue
        if torrents[tf].need_to_delete:
            continue
        logger.info("Starting torrent '{}' for '{}'".format(torrents[tf].basename, torrents[tf].tarball))
        parm_dict['ti'] = torrents[tf].info
        t_session.async_add_torrent(parm_dict)
        
def get_lt_alerts():
    global t_session
    alert = t_session.pop_alert()
    while alert:
        logger.info("Libtorrent alert: '{}'".format(str(alert)))
        alert = t_session.pop_alert()
def main_loop():
    while True:
        remove_files()
        get_lt_alerts()
        update_inactive_torrents()
        time.sleep(2)
        print t_session.get_torrents()
def update_inactive_torrents():
    for uid in torrents:
        tf = torrents[uid]
        if tf.need_to_delete:
            continue
        if tf.duplicate:
            continue
        active_torr = t_session.find_torrent(tf.info_hash)
        if tf.active:
            if not active_torr.is_valid():
                logger.info("Something is not right. Torrent '{}' marked as active. But not seeding. Tarball is '{}'".format(tf.basename, tf.tarball))
            continue
        if active_torr.status().total_upload != tf.uploaded:
            logger.info("Torrent '{}' for '{}' still in use. '{}' bytes uploaded.".format(tf.basename, tf.tarball, active_torr.status().total_upload))
            for i in active_torr.get_peer_info():
                logger.info("'{}' used by '{}'".format(tf.basename, i.ip))
            tf.uploaded = active_torr.status().total_upload
            tf.accessed(True)
        if tf.accessed() < get_now(-SOFTTIMEOUT):
            logger.info("Timeout for inactive torrent '{}' for '{}'. Files will be deleted.".format(tf.basename, tf.tarball))
            tf.need_to_delete = True
            t_session.remove_torrent(active_torr)
        if tf.become_inactive < get_now(-HARDTIMEOUT):
            logger.info("Hard timeout for inactive torrent '{}' for '{}'. Files will be deleted.".format(tf.basename, tf.tarball))
            tf.need_to_delete = True
            t_session.remove_torrent(active_torr)
            

def remove_files():
    pass


if __name__ == '__main__':
    setup_logging()
#    get_luna_torrents()
    update_torrents()
    start_torrent_client()
    #print torrents
    #get_lt_alerts()
    main_loop()

