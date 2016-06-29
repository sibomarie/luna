from config import *
import logging
import pymongo
import ConfigParser
import urllib
import sys
import os
import subprocess

def set_mac_node(mac, node, mongo_db = None):
    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    if not mongo_db:
        try:
            mongo_client = pymongo.MongoClient(get_con_options())
        except:
            logger.error("Unable to connect to MongoDB.")
            raise RuntimeError
        logger.debug("Connection to MongoDB was successful.")
        mongo_db = mongo_client[db_name]
    mongo_collection = mongo_db['mac']
    mongo_collection.remove({'mac': mac})
    mongo_collection.remove({'node': node})
    mongo_collection.insert({'mac': mac, 'node': node})

def get_con_options():
    conf = ConfigParser.ConfigParser()
    if not conf.read("/etc/luna.conf"):
        return "localhost"
    try:
        replicaset = conf.get("MongoDB", "replicaset")
    except:
        replicaset = None
    try:
        server = conf.get("MongoDB", "server")
    except:
        server = 'localhost'
    try:
        authdb = conf.get("MongoDB", "authdb")
    except:
        authdb = 'admin'
    try:
        user = conf.get("MongoDB", "user")
        password = urllib.quote_plus(conf.get("MongoDB", "password"))
    except:
        user = None
        password = None
    if user and password and replicaset:
        auth_str = 'mongodb://' + user + ':' + password + '@' + server + '/' + authdb + '?replicaSet=' + replicaset
        return auth_str
    if user and password:
        auth_str = 'mongodb://' + user + ':' + password + '@' + server + '/' + authdb
        return auth_str
    return "localhost"


def rsync_data(host = None, lpath = None, rpath = None):

    if not host or not lpath:
        sys.stderr.write("Hostname or path did not specified")
        sys.exit(1)
    lpath = os.path.abspath(lpath)
    if not rpath:
        rpath = os.path.dirname(lpath)

    # check if someone run rsync already
    pidfile = "/run/luna_rsync.pid"
    try:
        pf = file(pidfile,'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None

    if pid:
        message = "pidfile %s already exist.\n"
        sys.stdout.write(message % pidfile)
        try:
            os.kill(pid, 0)
        except OSError:
            pass
        else:
            message = "Process %s is running.\n"
            sys.stderr.write(message % pid)
            sys.exit(1)

    pf = file(pidfile,'w+')
    pid = os.getppid()
    pf.write("%s\n" % pid)
    pf.close()

    # check if someone run rsync on other node to prevent circular syncing
    ssh_proc = subprocess.Popen(['/usr/bin/ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null', host,
            'ls', pidfile],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        close_fds=True)
    streamdata = ssh_proc.communicate()[0]

    if not ssh_proc.returncode:
        message = "Pidfile %s exists on node %s. Probably syncronization is going from remote to local node. Exiting.\n"
        sys.stderr.write(message % (pidfile, host))
        os.remove(pidfile)
        sys.exit(1)

    cmd = r'''/usr/bin/rsync -avz -HAX -e "/usr/bin/ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress --delete ''' + lpath + r''' root@''' + host + r''':''' + rpath
    try:
        rsync_out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stat_symb = ['\\', '|', '/', '-']
        i = 0
        while True:
            line = rsync_out.stdout.readline()
            if line == '':
                break
            i = i + 1
            sys.stdout.write(stat_symb[i % len(stat_symb)])
            sys.stdout.write('\r')
    except:
        os.remove(pidfile)
        sys.stdout.write('\r')
        sys.stderr.write("Interrupt.")
        sys.exit(1)
    os.remove(pidfile)
    return True


