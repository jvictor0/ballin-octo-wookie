import simplejson as json
from jsonrpc import ServerProxy, JsonRpc20, TransportTcpIp, RPCTransportError, RPCError
from pprint import pprint
from lispparse import Lisp
import sys
import random

class StanfordNLP:
    def __init__(self):
        self.servers = []

        # find servers!
        for i in range(100):
            potential = self.get_server("127.1", 10000 + i)
            try:
                potential.ping()
                self.servers.append(potential)
            except RPCTransportError:
                break

        print("Found %d corenlp servers" % len(self.servers))
        if not self.servers:
            sys.exit(1)

    def get_server(self, host, port):
        return ServerProxy(JsonRpc20(),
               TransportTcpIp(addr=(host, port)))
    
    def parse(self, text):
        last_e = None
        for _ in range(5):
            server = random.choice(self.servers)
            try:
                res = server.parse(text)
                break
            except RPCError as e:
                last_e = e
        else:
            raise last_e

        if isinstance(res, basestring):
            res = json.loads(out)
        for s in res["sentences"]:
            s["parsetree"] = Lisp(s["parsetree"])
        return res


