from config import *
import pymongo
import logging
import inspect
import sys
import os
from bson.objectid import ObjectId
from bson.dbref import DBRef

from options import Options

class OsImage(Options):
    def __init__(self, name = None, create = False, path = None, kernver = None, kernopts = None):
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        options = Options()
        self._collection_name = 'osimage'
        mongo_doc = self._check_name(name, create)
        if kernopts == None:
            kernopts = ''
        if type(kernopts) is not str:
            self._logger.error("Kernel options should be 'str' type")
            raise RuntimeError
        if create:
            path = os.path.abspath(path)
            path_suspected_doc = self._mongo_collection.find_one({'path': path})
            if path_suspected_doc and path_suspected_doc['path'] == path:
                self._logger.error("Cannot create 'osimage' with the same 'path' as name='{}' has".format(path_suspected_doc['name']))
                raise RuntimeError
            try:
                os_image_kernvers = self.get_package_ver(path,'kernel')
                req_kernver = os_image_kernvers.index(kernver)
            except:
                self._logger.error("Kernel version '{}' not in list {} from {}. Kernel Version or osimage path are incorrect?".format(kernver, os_image_kernvers, path))
                raise RuntimeError
            mongo_doc = {'name': name, 'path': path, 'kernver': kernver, 'kernopts': kernopts}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self.link(options)
        self._keylist = ['path', 'kernver', 'kernopts']


    def get_package_ver(self, path, package):
        import rpm
        rpm.addMacro("_dbpath", path + '/var/lib/rpm')
        ts = rpm.TransactionSet()
        package_vers = list()
        mi = ts.dbMatch( 'name', package )
        for h in mi:
            ver = "%s-%s.%s" % (h['VERSION'], h['RELEASE'], h['ARCH'])
            package_vers.extend([ver])
        return package_vers

