from tornado import web
from tornado import httpserver
from tornado import gen
from tornado import ioloop
from tornado.concurrent import Future

import signal

import simplejson as json
import sys
from public import Ingest, Generate, Reset, GetSymbols
import threading
import Queue
import logging

logger = logging.getLogger(__name__)

work_queue = Queue.Queue()
stopping = threading.Event()

signal.signal(signal.SIGINT, lambda *a: stopping.set())

class Work(object):
    def __init__(self, target, args):
        self.target = target
        self.args = args
        self.future = Future()

    def execute(self):
        try:
            out = self.target(*self.args)
            self.future.set_result(out)
        except Exception:
            self.future.set_exc_info(sys.exc_info())

class Worker(threading.Thread):
    def run(self):
        while not stopping.is_set():
            try:
                work = work_queue.get(timeout=0.1)
                work.execute()
            except Queue.Empty:
                pass

def _check_closed():
    if stopping.is_set():
        ioloop.IOLoop.instance().stop()

def _tornado_logger(handler):
    exc_info = False
    if handler.get_status() < 400:
        log_method = logger.info
    elif handler.get_status() < 500:
        log_method = logger.warning
    else:
        exc_info = sys.exc_info() or False
        log_method = logger.error

    request_time = 1000.0 * handler.request.request_time()
    log_method("%d %s %.2fms", handler.get_status(), handler._request_summary(), request_time, exc_info=exc_info)

class BaseHandler(web.RequestHandler):
    def _params(self):
        """ Decode a params dictionary from the request body. """
        body = self.request.body.strip()
        if not body:
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise JSONDecodeError(str(e))

    def _respond_success(self, data):
        self._finish(200, data)

    def _respond_error(self, error):
        status_code = 500
        data = {
            "error": str(error),
            "error_type": error.__class__.__name__
        }

        self._finish(status_code, data)

    def _finish(self, status_code, data):
        self.set_status(status_code)
        self._write_json(data)
        self.finish()

    def _write_json(self, data):
        data = json.dumps(data)
        self.write(data + "\n")

class IngestHandler(BaseHandler):
    @gen.coroutine
    def post(self, user_id):
        try:
            params = self._params()
            text = params["text"].encode("utf8")

            w = Work(Ingest, (user_id, text))
            work_queue.put(w)

            out = yield w.future
            if out["success"]:
                self._respond_success(out)
            else:
                print(out["error"])
                raise Exception("Ingest error")

        except Exception as err:
            self._respond_error(err)

class GenerateHandler(BaseHandler):
    @gen.coroutine
    def post(self, user_id):
        try:
            params = self._params()
            symbols = params["metadata"]

            w = Work(Generate, (user_id, symbols))
            work_queue.put(w)

            out = yield w.future
            if out["success"]:
                self._respond_success(out)
            else:
                print(out["error"])
                raise Exception("Generate error")
        except Exception as err:
            self._respond_error(err)

class SymbolsHandler(BaseHandler):
    @gen.coroutine
    def post(self, user_id):
        try:
            params = self._params()
            text = params["text"].encode("utf-8")

            w = Work(GetSymbols, (text, ))
            work_queue.put(w)

            out = yield w.future
            if out["success"]:
                self._respond_success(out)
            else:
                print(out["error"])
                raise Exception("GetSymbols error")
        except Exception as err:
            self._respond_error(err)

class ResetHandler(BaseHandler):
    @gen.coroutine
    def post(self, user_id):
        try:
            self._respond_success(Reset(user_id))

            w = Work(Reset, (user_id, ))
            work_queue.put(w)

            out = yield w.future
            if out["success"]:
                self._respond_success(out)
            else:
                print(out["error"])
                raise Exception("Reset error")
        except Exception as err:
            self._respond_error(err)

app = web.Application(
    handlers=[
        (r"/ingest/(?P<user_id>.*)/?", IngestHandler),
        (r"/generate/(?P<user_id>.*)/?", GenerateHandler),
        (r"/symbols/?", SymbolsHandler),
        (r"/reset/(?P<user_id>.*)/?", ResetHandler),
        ],
    compress_response=True,
    log_function=_tornado_logger
)

if __name__ == "__main__":
    workers = [Worker() for _ in range(5)]
    [w.start() for w in workers]

    loop = ioloop.IOLoop.instance()

    server = httpserver.HTTPServer(request_callback=app, io_loop=loop)
    server.listen(address="0.0.0.0", port=5000)

    cb = ioloop.PeriodicCallback(_check_closed, 1000, io_loop=loop)
    cb.start()

    loop.start()

    [w.join() for w in workers]
