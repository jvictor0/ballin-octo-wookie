import argparse
import multiprocessing
import signal

class Wrapper(multiprocessing.Process):
    def __init__(self, port):
        self.port = port
        super(Wrapper, self).__init__()

    def run(self):
        import sys
        from corenlp import StanfordCoreNLP
        import jsonrpc

        sys.__stdin__ = sys.__stdout__

        server = jsonrpc.Server(jsonrpc.JsonRpc20(),
                 jsonrpc.TransportTcpIp(addr=("0.0.0.0", int(self.port))))

        nlp = StanfordCoreNLP()
        server.register_function(nlp.parse)
        server.register_function(nlp.parse_file)
        print "registering parse_file"
        server.register_function(lambda *a, **k: 'pong', 'ping')

        try:
            server.serve()
        except KeyboardInterrupt:
            print("%d exiting" % self.port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--number", type=int, required=True, help="the number of corenlp processes to manage")
    parser.add_argument("-p", "--port", type=int, default=10000, help="the port number to start at")
    options = parser.parse_args()

    processes = []

    for i in range(options.number):
        port = options.port + i
        wrapper = Wrapper(port)
        print("starting corenlp on port %d" % port)
        wrapper.start()
        processes.append(wrapper)

    signal.signal(signal.SIGINT, lambda *a: None)
    [proc.join() for proc in processes]
