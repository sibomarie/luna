def _calc_prefix_mask(prefix, netmask):
    import struct, socket
    try:
        prefix = int(prefix)
    except:
        prefix = 0
    if prefix in range(1,32):
        print prefix
        prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return (prefix, socket.inet_ntoa(struct.pack('>L', (prefix_num))))
    prefix = 0
    try:
        mask_num = struct.unpack('>L', (socket.inet_aton(netmask)))[0]
    except socket.error:
        return (None, None)
    b = 32
    for i in reversed(range(0,31)):
        if (mask_num & 1<<i) == 0:
            b = i
            break
    prefix = 31-b
    prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
    return (prefix, socket.inet_ntoa(struct.pack('>L', (prefix_num))))

print _calc_prefix_mask('ssss','255.255.255.1')


