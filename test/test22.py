import luna
#opt = luna.Options(create=True)
#opt = luna.Options()
#osimage = luna.OsImage(create=True, name='compute', path='/os/compute-image/', kernver='3.10.0-327.3.1.el7.x86_64')
osimage = luna.OsImage(name='compute')
"""
try:
    osimage = luna.OsImage(create=True, name='compute1', path='/os/compute-image', kernver='3.10.0-327.3.1.el7.x86_64')
except:
    pass
try:
    osimage = luna.OsImage(create=True, name='compute2', path='/os/compute-image///', kernver='3.10.0-327.3.1.el7.x86_64')
except:
    pass
try:
    osimage = luna.OsImage(create=True, name='compute3', path='../os/compute-image///', kernver='3.10.0-327.3.1.el7.x86_64')
except:
    pass
print opt
print osimage
print '==========================='
print opt.nice_json
print '==========================='
print osimage.nice_json
print '==========================='
print osimage.delete()
print opt.delete()
"""
print dir(osimage)
#osimage.path = '/os/jkl'
#osimage.kernopts = 'kjhkjhkjhkjhkjhkjhk'
