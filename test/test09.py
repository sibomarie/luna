from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.find_obj('nodes', 'node005')
print 2
print luna.unlink_objects('nodes', 'node005', 'nodes', 'node003')
