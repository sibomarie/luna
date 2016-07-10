import luna
net1 = luna.Network(name = 'cluster')
net1.resolve_used_ips()
print '==========='
net1 = luna.Network(name = 'ipmi')
net1.resolve_used_ips()
