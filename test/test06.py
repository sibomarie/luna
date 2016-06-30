from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.find_obj('nodes', 'node005')
print 2
print luna.add_array_elem('nodes', ['node005', 'node006'], 'nodes1', ['a1', 'a2', 'a3'] )
print 3
print luna.change_obj('nodes',['node001', 'node003'], {'zzz': 6})
