from config import *
import pymongo
import logging
import inspect
import sys
import os
from bson.objectid import ObjectId
from bson.dbref import DBRef
from luna.base import Base
from luna.options import Options

class OsImage(Base):
    """
    Class for operating with osimages records
    """
    def __init__(self, name = None, create = False, id = None, path = '', kernver = '', kernopts = ''):
        """
        create  - shoulld be True if we need create osimage
        path    - path to / of the image/ can be ralative, if needed (will be converted to absolute)
        kernver - kernel version (will be checked on creation)
        kernopt - kernel options
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'osimage'
        mongo_doc = self._check_name(name, create, id)
        if type(kernopts) is not str:
            self._logger.error("Kernel options should be 'str' type")
            raise RuntimeError
        self._keylist = {'path': type(''), 'kernver': type(''), 'kernopts': type('')}
        if create:
            options = Options()
            path = os.path.abspath(path)
            path_suspected_doc = self._mongo_collection.find_one({'path': path})
            if path_suspected_doc and path_suspected_doc['path'] == path:
                self._logger.error("Cannot create 'osimage' with the same 'path' as name='{}' has".format(path_suspected_doc['name']))
                raise RuntimeError
            if not self._check_kernel(path, kernver):
                raise RuntimeError
            mongo_doc = {'name': name, 'path': path, 'kernver': kernver, 'kernopts': kernopts}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(options)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)


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

    def __getattr__(self, key):
        try:
            self._keylist[key]
        except:
            raise AttributeError()
        return self.get(key)

    def __setattr__(self, key, value):
        if key == 'path':
            kernver = self.kernver
            if not self._check_kernel(value, kernver):
                return None
        elif key == 'kernver':
            path = self.path
            if not self._check_kernel(path, value):
                return None
        try:
            self._keylist[key]
            self.set(key, value)
        except:
            self.__dict__[key] = value

    def _check_kernel(self, path, kernver):
        import os
        os_image_kernvers = None
        req_kernver = None
        if not os.path.isdir(path):
            self._logger.error("{} is not valid dir".format(path))
            return None
        try:
            os_image_kernvers = self.get_package_ver(path,'kernel')
            req_kernver = os_image_kernvers.index(kernver)
        except:
            if os_image_kernvers == []:
                self._logger.error("No kernel package installed in {}".format(path))
                return None
            self._logger.error("Kernel version '{}' not in list {} from {}. Kernel Version or osimage path are incorrect?".format(kernver, os_image_kernvers, path))
            return None
        return True


    """
    @property
    def path(self):
        return self.get('path')

    @path.setter
    def path(self, value):
        self.set('path', value)
    """
