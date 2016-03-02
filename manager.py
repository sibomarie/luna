#/usr/bin/env python

import luna
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen
import logging
import sys
import pymongo
import binascii
import datetime
import random
import libtorrent
import threading
import datetime
import time
from socket import inet_aton
from struct import pack
from bson.dbref import DBRef


import tornado.ioloop
import tornado.web
import tornado.httpserver


last_switch_update = None
lock_last_switch_update = threading.Lock()
switch_table_updater_running = False
lock_switch_table_updater_running = threading.Lock()
switch_mac_table = None
lock_switch_mac_table = threading.Lock()

class Manager(tornado.web.RequestHandler):
    """
    def get_name_from_known_macs(self, macs):
        global last_switch_update
        global switch_mac_table
        cur_time = datetime.datetime.utcnow()
        if last_switch_update and cur_time - datetime.timedelta(seconds = 5) > last_switch_update:
            return (None, None)
        out_mac = None
        if not bool(switch_mac_table):
            return (None, None)
        switch_mac_table_local = switch_mac_table[:]
        for record in switch_mac_table_local:
            for mac in macs:
                if mac != record[0]:
                    continue
                try:
                    node_name = self.mongo['node'].find_one({'switch': record[1], 'port': record[2]}, {'_id': 0, 'name': 1})['name']
                except:
                    node_name = None
                if bool(node_name):
                    out_mac = mac
                    break
            if bool(node_name):
                break
        if not bool(node_name):
            return (None, None)
        return (node_name, out_mac)
    
    def switch_table_updater_2(self,  callback=None):
        print '------'
        time.sleep(1)
        callback(123)

    def switch_table_updater(self,  callback=None):
        global last_switch_update
        global lock_switch_table_updater_running
        cur_time = datetime.datetime.utcnow()
        if last_switch_update and cur_time - datetime.timedelta(seconds = 5) <= last_switch_update:
            print 'no need to update'
            callback(None)
            return
        if not lock_switch_table_updater_running.acquire(False):
            print 'another proc is running'
            callback(None)
            return
        last_switch_update = cur_time
        print "==============updating switch table", lock_switch_table_updater_running, last_switch_update
        time.sleep(10)
        lock_switch_table_updater_running.release()
        callback(None)
        return
    """
    def initialize(self, params):
        self.server_ip = params['server_ip']
        self.server_port = params['server_port']
        self.mongo = params['mongo_db']
        self.app_logger = params['app_logger']

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        step = self.get_argument('step')
        if step == 'boot':
            nodes = luna.list('node')
            self.render("templ_ipxe.cfg", server_ip = self.server_ip, server_port = self.server_port, nodes = nodes)
        if step == 'discovery':
            try:
                hwdata = self.get_argument('hwdata')
            except:
                hwdata = None
            if not bool(hwdata):
                self.send_error(400) #  Bad Request
                return
            try:
                req_nodename = self.get_argument('node')
            except:
                req_nodename = None
            if req_nodename:
                try:
                    node = luna.Node(name = req_nodename, mongo_db = self.mongo['node'])
                except:
                    self.app_logger.error("No such node configured in DB. '{}'".format(req_nodename))
                    self.send_error(400)
                    return
                macs = hwdata.split('|')
                mac = None
                for i in range(len(macs)):
                    if bool(macs[i]):
                        mac = macs[i]
                        break
                if mac:
                    mac = mac.lower()
                    self.mongo['mac'].find_and_modify({'_id': mac}, {'$set': {'name': req_nodename}}, upsert = True)
            macs = set(hwdata.split('|'))
            find_name = None
            for mac in macs:
                if not bool(mac):
                    continue
                mac = mac.lower()
                find_name_json = self.mongo['mac'].find_one({'_id': mac}, {'_id': 0, 'name': 1})
                if bool(find_name):
                    break
            try:
                find_name = find_name_json['name']
            except:
                self.app_logger.error("No name configured for mac '{}'".format(mac.lower()))
                #return self.send_error(404)
                self.send_error(404)
                return
            if not bool(find_name):
                """
                (find_name, mac) = self.get_name_from_known_macs(macs)
                if not bool(find_name):
                    resp = yield tornado.gen.Task(self.switch_table_updater)
                    self.send_error(404)
                    return
                """
                finded_mac = None
                for mac in macs:
                    mac_cursor = self.mongo['switch_mac'].find({'mac': mac})
                    for elem in mac_cursor:
                        switch_id = elem['switch_id']
                        port = elem['port']
                        try:
                            find_name = self.mongo['node'].find_one({'switch': DBRef('switch', switch_id), 'port': port}, {})['name']
                            finded_mac = mac
                        except:
                            finded_mac = None
                        if finded_mac:
                            break
                    if finded_mac:
                        break
                if not bool(finded_mac):
                    self.send_error(404)
                    return
                self.mongo['mac'].find_and_modify({'_id': finded_mac}, {'$set': {'name': find_name}}, upsert = True)
            try:
                node = luna.Node(name = find_name, mongo_db = self.mongo)
            except:
                self.app_logger.error("Mac '{}' exists, but node does not '{}'".format(mac.lower(), find_name))
            http_path = "http://" + self.server_ip + ":" + str(self.server_port) + "/boot/"
            boot_params = node.boot_params
            if not boot_params['boot_if']:
                boot_params['ifcfg'] = 'dhcp'
            else:
                boot_params['ifcfg'] = boot_params['boot_if'] + ":" + boot_params['ip'] + "/" + str(boot_params['net_prefix'])
            boot_params['delay'] = 10
            self.render("templ_nodeboot.cfg",
                    params = boot_params, server_ip = self.server_ip,
                    server_port = self.server_port, nodename = node.name)
        if step == 'install':
            try:
                node_name = self.get_argument('node')
            except:
                self.app_logger.error("No nodename for install step specified.")
                #return self.send_error(400)
                self.send_error(400)
                return
            try:
                node = luna.Node(name = node_name, mongo_db = self.mongo)
            except:
                self.app_logger.error("No such node for install step found '{}'.".format(node_name))
                #return self.send_error(400)
                self.send_error(400)
                return
                #self.finish()
            install_params = node.install_params
            if not bool(install_params['torrent']):
                #return self.send_error(404)
                self.send_error(404)
                return
                #self.finish()
            self.render("templ_install.cfg", p = install_params, server_ip = self.server_ip, server_port = self.server_port,)


