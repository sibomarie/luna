from Luna import Luna
from bson import ObjectId
luna = Luna('luna')
print 1
print luna.dump_obj('group', 'compute', resolverefs=False)

