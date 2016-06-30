from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.create_cluster('node',3, 'enp0s8')
