from ming import create_datastore
import unittest

import os
import luna

class ClusterReadTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def tearDown(self):
        self.bind.conn.drop_all()


    def test_read_non_existing_cluster(self):
        self.assertRaises(RuntimeError, luna.Cluster, mongo_db=self.db)


    def test_cluster_read(self):
        luna.Cluster(mongo_db=self.db, create=True, path=self.path, user='root')
        cluster = luna.Cluster(mongo_db=self.db)
        self.assertIsInstance(cluster, luna.Cluster)


class ClusterCreateTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def tearDown(self):
        self.bind.conn.drop_all()


    def test_init_cluster_with_defaults(self):
        cluster = luna.Cluster(mongo_db=self.db, create=True, path=self.path, user='root')
        self.assertIsInstance(cluster, luna.Cluster)


if __name__ == '__main__':
    unittest.main()
