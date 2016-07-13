import luna
cl = luna.Cluster()
print cl.makedhcp('test01', '10.50.0.1', '10.50.0.10')
print cl.makedhcp('cluster', '10.30.100.1', '10.30.100.10')
