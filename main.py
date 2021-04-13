# -*- coding: utf-8 -*-
# @Time    : 2021/3/29 20:07
# @Author  : LTstrange

from Network_API import app, blockchain
from utils import get_host_ip

if __name__ == '__main__':
    ip = get_host_ip()
    port = 5000
    blockchain.get_host(ip, port)
    app.run(host=ip, port=port, debug=True)

