from flask import Flask, request
from flask.json import jsonify
app = Flask(__name__)

from public import Ingest, Generate, Reset
import threading
from collections import deque

injest_queue = deque()
stopping = threading.Event()

class Worker(threading.Thread):
    def run(self):
        while not stopping.is_set():
            work = injest_queue.pop()
            out = Ingest(**work)
            if not out["success"]:
                print("lol injest error")
                print(out["error"])

@app.route("/ingest/<user_id>")
def ingest(user_id):
    injest_queue.appendLeft({
        "user": user_id,
        "text": request.form["text"]
    })
    return jsonify(success=True)

@app.route("/generate/<user_id>")
def generate(user_id):
    return jsonify(Generate(user_id))

@app.route("/reset/<user_id>")
def reset(user_id):
    return jsonify(Reset(user_id))

if __name__ == "__main__":
    worker = Worker()
    worker.start()

    try:
        app.run()
    except KeyboardInterrupt:
        print("exiting")
        stopping.set()
        worker.join()
        print("done.")
