import luna
import pymongo

#client = pymongo.MongoClient()
#client.drop_database('luna')


#opt = luna.Options(create = True)
#ifcfg1 = luna.IfCfg(name = 'internal1', create=True, NETWORK = '192.168.1.0', PREFIX = 24, NETMASK = '255.255.255.0' )
#ifcfg2 = luna.IfCfg(name = 'internal2', create=True, NETWORK = '192.168.2.0', PREFIX = 24, NETMASK = '255.255.255.0' )
#ifcfg3 = luna.IfCfg(name = 'internal3', create=True, NETWORK = '192.168.3.0', PREFIX = 24, NETMASK = '255.255.255.0' )
#ipmi = luna.IfCfg(name = 'ipmi', create=True, NETWORK = '10.10.0.0', PREFIX = 16 )
#bmc = luna.BMCSetup(name = 'base', create = True)
#osimage = luna.OsImage(create=True, name='compute1', path='/os/compute-image', kernver='3.10.0-327.3.1.el7.x86_64')
#osimage = luna.OsImage(create=True, name='compute2', path='/os/compute-image-2', kernver='3.10.0-327.3.1.el7.x86_64')
group = luna.Group(name='compute-group')
print group.osimage('compute1')
print group.nice_json
print group.osimage('compute2')
print group.nice_json
