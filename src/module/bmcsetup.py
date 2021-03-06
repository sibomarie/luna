'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

from config import *
import logging
import inspect
from bson.dbref import DBRef
from luna.base import Base
from luna.cluster import Cluster

class BMCSetup(Base):
    """
    Class for operating with bmcsetup records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None,
            userid = 3, user = 'ladmin', password = 'ladmin', netchannel = 1, mgmtchannel = 1):
        """
        userid      - default user id
        user        - username
        password    - pasword
        netchannel  - network channel
        mgmtchannel - management channel
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'bmcsetup'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = {'userid': type(0), 'user': type(''), 'password': type(''), 'netchannel': type(0), 'mgmtchannel': type(0)}
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            passed_vars = inspect.currentframe().f_locals
            for key in self._keylist:
                if type(passed_vars[key]) is not self._keylist[key]:
                    self._logger.error("Argument '{}' should be '{}'".format(key, self._keylist[key]))
                    raise RuntimeError
            mongo_doc = {'name': name, 'userid': userid, 'user': user,
                    'password': password, 'netchannel': netchannel,
                    'mgmtchannel': mgmtchannel}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)
