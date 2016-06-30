from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.get_package_ver('/os/compute-image','kernel')
print 2
print luna.get_package_ver('','kernel')
