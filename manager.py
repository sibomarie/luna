#/usr/bin/env python

import luna
import tornado.ioloop
import tornado.web
import tornado.httpserver
import logging
import sys
import pymongo
import binascii
import datetime
import random
import libtorrent
from socket import inet_aton
from struct import pack


import tornado.ioloop
import tornado.web
import tornado.httpserver

class Manager(tornado.web.RequestHandler):
    def initialize(self, params):
        self.server_ip = params['server_ip']
        self.server_port = params['server_port']
        self.mongo = params['mongo']
        self.app_logger = params['app_logger']

    @tornado.web.asynchronous
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
                return self.send_error(400) #  Bad Request
            try:
                req_nodename = self.get_argument('node')
            except:
                req_nodename = None
            if req_nodename:
                try:
                    node = luna.Node(name = req_nodename, mongo_db = self.mongo['node'])
                except:
                    self.app_logger.error("No such node configured in DB. '{}'".format(req_nodename))
                    return self.send_error(400) 
                macs = hwdata.split('|')
                mac = None
                for i in range(len(macs)):
                    if bool(macs[i]):
                        mac = macs[i]
                        break
                if mac:
                    self.mongo['mac'].find_and_modify({'_id': mac}, {'$set': {'name': req_nodename}}, upsert = True)
            macs = set(hwdata.split('|'))
            find_name = None
            for mac in macs:
                if not bool(mac):
                    continue
                find_name_json = self.mongo['mac'].find_one({'_id': mac}, {'_id': 0, 'name': 1})
                if bool(find_name):
                    break
            try:
                find_name = find_name_json['name']
            except:
                self.app_logger.error("No name configured for mad '{}'".format(mac))
                return self.send_error(404)
            if not bool(find_name):
                return self.send_error(404)
            try:
                node = luna.Node(name = find_name, mongo_db = self.mongo)
            except:
                self.app_logger.error("Mac '{}' exists, but node does not '{}'".format(mac, find_name))
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
                return self.send_error(400)
            try:
                node = luna.Node(name = node_name, mongo_db = self.mongo)
            except:
                self.app_logger.error("No such node for install step found '{}'.".format(node_name))
                return self.send_error(400)
            install_params = node.install_params
            self.render("templ_install.cfg", p = install_params)


