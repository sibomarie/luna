from Luna import Luna
from bson import ObjectId
luna = Luna()
print 1
print luna.create_obj('nodes', ['node005', 'node006'], {})
print 2
print luna.change_obj('nodes', ['node005', 'node006'], {'aaa': None})
