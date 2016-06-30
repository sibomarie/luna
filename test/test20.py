from Luna import Luna
from bson import ObjectId
luna = Luna('luna')
print 1
print luna.create_cluster('node',3, 'enp0s8')
print 2
print luna.create_osimage('centos7', '/os/compute-image', '3.10.0-327.3.1.el7.x86_64', '')
print 3
print luna.create_ifcfg('internal', '10.10.0.0', 16, 9000)
print 4
print luna.create_ifcfg('ipmi', '10.11.0.0', 16, 1500)
print 5
print luna.create_bmcsettings('bmc',3,'ADMIN','ADMIN',1,2)
print 6
print luna.create_group('compute','centos7','bmc', ['eno0', 'ipmi'], ['internal', 'ipmi'])
print 7
print luna.create_node('compute')
print 8
print luna.create_node('compute', 'node002')
print 9
luna.dump_obj('node', 'node002')
