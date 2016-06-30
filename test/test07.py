from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.find_obj('nodes', 'node005')
print 2
print luna.del_array_elem('nodes', ['node005', 'node006'], 'nodes1', [ 'a1', 'a3', 'a4' ] )
