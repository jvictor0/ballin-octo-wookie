import json
from jsonrpc import ServerProxy, JsonRpc20, TransportTcpIp
from pprint import pprint
from lispparse import Lisp

class StanfordNLP:
    def __init__(self):
        self.server = ServerProxy(JsonRpc20(),
                                  TransportTcpIp(addr=("127.0.0.1",10003)))
    
    def parse(self, text):
        res = json.loads(self.server.parse(text))
        for s in res["sentences"]:
            s["parsetree"] = Lisp(s["parsetree"])
        return res



