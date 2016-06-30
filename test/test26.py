from luna import BMCSetup, Options
#Options(create = True)
b = BMCSetup(name = 'base', create = True)
print b.get('userid')
