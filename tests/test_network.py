from ming import create_datastore
import mock
import unittest

import os
import luna

class NetworkUtilsTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        cluster = luna.Cluster(mongo_db=self.db, create=True, path=self.path,
                               user='root')
        self.net = luna.Network(name='test', mongo_db=self.db, create=True,
                                NETWORK='172.16.1.0', PREFIX='24',
                                ns_hostname='controller', ns_ip='172.16.1.254')


    @classmethod
    def tearDownClass(self):
        self.bind.conn.drop_all()


    def test_ip_to_absnum_with_valid_ip(self):
        absnum = self.net.ip_to_absnum('10.0.0.1')
        self.assertEqual(absnum, 167772161)


    def test_ip_to_absnum_with_invalid_ip(self):
        self.assertRaises(RuntimeError, self.net.ip_to_absnum, '256.0.0.1')


    def test_absnum_to_ip_with_valid_absnum(self):
        ip = self.net.absnum_to_ip(167772161)
        self.assertEqual(ip, '10.0.0.1')


    def test_absnum_to_ip_with_invalid_absnum(self):
        self.assertRaises(RuntimeError, self.net.absnum_to_ip, 4294967296)


    def test_get_base_net_with_valid_input(self):
        base_net = self.net.get_base_net('10.0.0.1', '24')
        self.assertEqual(base_net, 167772160)


    def test_get_base_net_with_invalid_prefix(self):
        self.assertRaises(RuntimeError, self.net.get_base_net, '10.0.0.1', 33)


    def test_get_base_net_with_invalid_address(self):
        self.assertRaises(RuntimeError, self.net.get_base_net, '256.0.0.1', 2)


class NetworkCreateTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user='root')


    def tearDown(self):
        self.bind.conn.drop_all()


    def test_create_network_with_defaults(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='172.16.1.0', PREFIX='24')
        self.assertIsInstance(net, luna.Network)


class NetworkReadTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user='root')


    def tearDown(self):
        self.bind.conn.drop_all()


    def test_read_non_existing_network(self):
        self.assertRaises(RuntimeError, luna.Network, mongo_db=self.db)


    def test_read_network(self):
        luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='172.16.1.0', PREFIX='24')
        net = luna.Network(name='testnet', mongo_db=self.db)
        self.assertIsInstance(net, luna.Network)


if __name__ == '__main__':
    unittest.main()
