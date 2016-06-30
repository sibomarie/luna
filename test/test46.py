import tornado.template as template
loader = template.Loader("/opt/luna/templates")
z = {'serial_num': 20160629, 'master_hostname': 'master', 'master_ip': '10.30.255.254', 'hosts': {'node001': '10.30.0.1', 'node002': '10.30.0.2'}}

print loader.load("templ_zone.cfg").generate(z=z)

