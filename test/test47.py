#!/usr/bin/env python
import luna
od = luna.OtherDev(name = "testdev01", create = True, network = 'ipmi', ip = '10.31.0.10')
#od = luna.OtherDev(name = "testdev01", create = True)
#od = luna.OtherDev(name = "testdev01")
print od.get_ip('ipmi')
od.set_ip('ipmi', '10.31.0.20')
print od.get_ip('ipmi')
od.set_ip('ipmi')
od.set_ip('ipmi', '10.31.0.30')
print od.get_ip('ipmi')
#od.del_net('ipmi')
#od.delete()
