import luna
net = luna.Network('test01')
#print net.reserve_ip(1,50)
#print net.reserve_ip(51,100)
#print net.release_ip(50)
#print net.release_ip(45, 49)
print net.release_ip(1, 46)
print net.release_ip(51, 100)
