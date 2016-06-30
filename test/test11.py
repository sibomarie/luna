from Luna import Luna
from bson import ObjectId
luna = Luna('luna',['cluster','nodes'])
print 1
print luna.create_osimage('/os/compute-image','3.10.0-327.3.1.el7.x86_64','')
print 2
print luna.create_osimage('/os/compute-image','1111','')
