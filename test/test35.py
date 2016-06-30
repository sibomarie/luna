import luna
group = luna.Group('compute-group')
print group.get_human_ip('eth0',8)
print group.get_num_ip('eth0','192.168.1.13')
