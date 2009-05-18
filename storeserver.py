#!/usr/bin/env python
# encoding: utf-8
"""
storeserver.py

Created by Adam T. Lindsay on 2009-05-18.

The MIT License

Copyright (c) 2009 Adam T. Lindsay.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import sys
sys.path.append('gen-py')
from collections import defaultdict

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from locator.ttypes import Location
#from locator import Locator
import location
from diststore import Store

DEFAULTPORT = 9900

class StoreHandler(location.LocatorHandler):
    def __init__(self, peer=None, port=9900):
        location.LocatorHandler.__init__(self, peer, port)
        self.store = defaultdict(str)
    
    def get(self, key):
        """
        Parameters:
         - key
        """
        dest = self.get_node(key)
        if dest == self.here:
            return self.store[key]
        else:
            location.remote_call(location.str2loc(dest), 'get', key)
    
    def put(self, key, value):
        """
        Parameters:
         - key
         - value
        """
        dest = self.get_node(key)
        if dest == self.here:
            self.store[key] = value
            return
        else:
            location.remote_call(location.str2loc(dest), 'put', key, value)
    

#
def main(inputargs):
    handler = StoreHandler(**inputargs)
    processor = Store.Processor(handler)
    transport = TSocket.TServerSocket(handler.port)
    tfactory = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()
    server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)
    
    # refactor to LocatorHandler.local_join() ?
    if handler.peer:
        nodes = location.remote_call(handler.peer, 'join', handler.location)
        if nodes:
            handler.ring.extend(map(location.loc2str, nodes))
        print 'Joining the network...'
    else:
        handler.ring.append(handler.here)
        print 'Initiating the network...'
    
    print 'Starting the server at %s...' % (handler.here)
    try:
        server.serve()
    
    finally:
        # refactor to LocatorHandler.cleanup()
        handler.ring.remove(handler.here)
        for node in location.select_peers(handler.ring.nodes):
            location.remote_call(location.str2loc(node), 'remove', handler.location, [handler.location])
    print 'done.'

if __name__ == '__main__':
    inputargs = {}
    try:
        inputargs['port'] = int(sys.argv[-1])
        inputargs['peer'] = location.str2loc(sys.argv[-2])
    except:
        pass
    if 'port' not in inputargs:
        loc = location.ping_until_not_found(Location('localhost', DEFAULTPORT))
        inputargs['port'] = loc.port
    if 'peer' not in inputargs and inputargs['port'] != DEFAULTPORT:
        try:
            loc = location.ping_until_found(Location('localhost', DEFAULTPORT))
            inputargs['peer'] = loc
        except location.NodeNotFound:
            print 'No peer autodiscovered.'
    main(inputargs)

