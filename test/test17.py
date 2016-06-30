from Luna import Luna
from bson import ObjectId
luna = Luna('luna')
print 1
print luna.create_cluster('node',3, 'enp0s8')
print 2
print luna.create_osimage('centos7', '/os/compute-image', '3.10.0-327.3.1.el7.x86_64', '')
