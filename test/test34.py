import luna
ifcfg = luna.IfCfg('internal3')
print ifcfg.get_human_ip(80000)
print ifcfg.get_num_ip('192.168.3.13')
