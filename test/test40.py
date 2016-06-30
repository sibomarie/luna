import libtorrent
lf = libtorrent.torrent_info('/opt/luna/torrents/d23fab08-a9f8-47b2-af2d-7cef4ff75cea.torrent')
flags = 1093
t_session = libtorrent.session()
t_session.listen_on(7052, 7100)
parm_dict = {"save_path": "./", 'flags': flags, 'ti': lf}
torr = t_session.async_add_torrent(parm_dict)
rt = t_session.find_torrent(lf.info_hash())

