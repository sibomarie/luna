#!/usr/bin/env python
#
# BitTorrent Tracker using Tornado
#
# @author: Sreejith K <sreejithemk@gmail.com>
# Created on 12th May 2011
# http://foobarnbaz.com
import logging
from optparse import OptionParser
import sys

import tornado.ioloop
import tornado.web
import tornado.httpserver

from bencode import bencode
from utils import *
from luna import Options


logger = logging.getLogger('tornado.access')
luna_opts = Options()
luna_tracker_interval = luna_opts.get('tracker_interval')
luna_tracker_min_interval = luna_opts.get('tracker_min_interval')
luna_tracker_maxpeers = luna_opts.get('tracker_maxpeers')


class TrackerStats(BaseHandler):
    """Shows the Tracker statistics on this page.
    """
    @tornado.web.asynchronous
    def get(self):
        self.send_error(404)


class AnnounceHandler(BaseHandler):
    """Track the torrents. Respond with the peer-list.
    """
    @tornado.web.asynchronous
    def get(self):
        failure_reason = ''
        warning_message = ''

        # get all the required parameters from the HTTP request.
        info_hash = self.get_argument('info_hash')
        try:
            info_hash = self.get_argument('info_hash')
        except:
            return self.send_error(MISSING_INFO_HASH)
        if len(info_hash) != INFO_HASH_LEN:
            return self.send_error(INVALID_INFO_HASH)
        try:
            peer_id = self.get_argument('peer_id')
        except:
            return self.send_error(MISSING_PEER_ID)
        if len(peer_id) != PEER_ID_LEN:
            return self.send_error(INVALID_PEER_ID)
        ip = self.request.remote_ip
        try:
            port = int(self.get_argument('port'))
        except:
            return self.send_error(MISSING_PORT)
        try:
            uploaded = int(self.get_argument('uploaded'))
        except:
            uploaded = 0
        try:
            downloaded = int(self.get_argument('downloaded'))
        except:
            downloaded = 0
        try:
            left = int(self.get_argument('left'))
        except:
            left = 0
        info_hash = str(info_hash)

        try:
            compact = int(self.get_argument('compact'))
        except:
            compact = 0
        try:
            event = self.get_argument('event')
        except:
            event = ''
        try:
            no_peer_id = int(self.get_argument('no_peer_id'))
        except:
            no_peer_id = 0
        try:
            numwant = int(self.get_argument('numwant'))
        except:
            numwant = DEFAULT_ALLOWED_PEERS
        if numwant > luna_tracker_maxpeers:
            # XXX: cannot request more than MAX_ALLOWED_PEERS.
            return self.send_error(INVALID_NUMWANT)
        try:
            key = self.get_argument('key')
        except:
            key = ''
        try:
            tracker_id = self.get_argument('trackerid')
        except:
            tracker_id = ''
            
        update_peers(info_hash, peer_id, ip, port, event, uploaded, downloaded, left)

        # generate response
        response = {}
        # Interval in seconds that the client should wait between sending
        #    regular requests to the tracker.
        response['interval'] = luna_tracker_interval
        # Minimum announce interval. If present clients must not re-announce
        #    more frequently than this.
        response['min interval'] = luna_tracker_min_interval
        
        res_complete, res_incomplete, res_peers = get_peers(info_hash, 
                                                            numwant,
                                                            compact,
                                                            no_peer_id,
                                                            luna_tracker_interval * 2)
        response['complete'] = res_complete
        response['incomplete'] = res_incomplete
        response['peers'] = res_peers
        response['tracker id'] = tracker_id
        if bool(failure_reason):
            response['failure reason'] = failure_reason
        if bool(warning_message):
            response['warning message'] = warning_message

        # send the bencoded response as text/plain document.
        self.set_header('Content-Type', 'text/plain')
        self.write(bencode(response))
        self.finish()


class ScrapeHandler(BaseHandler):
    """Returns the state of all torrents this tracker is managing.
    """
    @tornado.web.asynchronous
    def get(self):
        info_hashes = self.get_arguments('info_hash')
        response = {}
        for info_hash in info_hashes:
            info_hash = str(info_hash)
            response[info_hash] = {}
            
            res_complete, res_incomplete, _ = get_peers(info_hash, numwant, compact, no_peer_id, luna_tracker_interval * 2)
            response[info_hash]['complete'] = res_complete
            # FIXME: number of times clients have registered completion.
            response[info_hash]['downloaded'] = res_complete
            response[info_hash]['incomplete'] = res_incomplete
            # this is possible typo:
            # response[info_hash]['name'] = bdecode(info_hash).get(name, '')

        # send the bencoded response as text/plain document.
        self.set_header('content-type', 'text/plain')
        self.write(bencode(response))
        self.finish()


def run_app(port):
    """Start Tornado IOLoop for this application.
    """
    tracker = tornado.web.Application([
        (r"/announce.*", AnnounceHandler),
        (r"/scrape.*", ScrapeHandler),
        (r"/", TrackerStats),
    ])
    logging.info('Starting Pytt on port %d' % port)
    http_server = tornado.httpserver.HTTPServer(tracker)
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()


def start_tracker():
    """Start the Torrent Tracker.
    """
    # parse commandline options
    parser = OptionParser()
    parser.add_option('-p', '--port', help='Tracker Port', default=0)
    parser.add_option('-b', '--background', action='store_true',
                      default=False, help='Start in background')
    parser.add_option('-d', '--debug', action='store_true',
                      default=False, help='Debug mode')
    (options, args) = parser.parse_args()

    # setup directories
    #create_pytt_dirs()
    # setup logging
    setup_logging(options.debug)

    try:
        # start the torrent tracker
        run_app(int(options.port) or luna_opts.get('tracker_port'))
    except KeyboardInterrupt:
        logging.info('Tracker Stopped.')
        #close_db()
        close_mongo()
        sys.exit(0)
    except Exception as ex:
        logging.fatal('%s' % str(ex))
        #close_db()
        close_mongo()
        sys.exit(-1)


if __name__ == '__main__':
    start_tracker()
