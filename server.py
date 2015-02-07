from flask import Flask, request
from flask.json import jsonify

from public import Ingest, Generate, Reset
import threading
from collections import deque

app = Flask(__name__)
app.debug = True

ingest_queue = deque()
stopping = threading.Event()

class Worker(threading.Thread):
    def run(self):
        while not stopping.is_set():
            if ingest_queue:
                work = ingest_queue.pop()
                out = Ingest(**work)
                if not out["success"]:
                    print("lol ingest error")
                    print(out["error"])

@app.route("/ingest/<user_id>", methods=["POST"])
def ingest(user_id):
    ingest_queue.append({
        "user": user_id,
        "text": request.form["text"].encode("utf-8")
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
