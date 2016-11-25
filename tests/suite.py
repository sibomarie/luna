import unittest
import test_cluster as cluster
import test_network as network

loader = unittest.TestLoader()
suite  = unittest.TestSuite()

suite.addTests(loader.loadTestsFromModule(cluster))
suite.addTests(loader.loadTestsFromModule(network))

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
