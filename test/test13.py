from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.delete_obj('nodes',['node001', 'node003', 'node005'])
