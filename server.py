from flask import Flask, request
from flask.json import jsonify

from public import Ingest, Generate, Reset, GetSymbols
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
    data = request.get_json(force=True)
    ingest_queue.append({
        "user": user_id,
        "text": data["text"].encode("utf-8")
    })
    return jsonify(success=True)

@app.route("/generate/<user_id>", methods=["POST"])
def generate(user_id):
    data = request.get_json(force=True)
    return jsonify(Generate(user_id, data["metadata"]))

@app.route("/symbols", methods=["POST"])
def symbols():
    data = request.get_json(force=True)
    return jsonify(GetSymbols(data["text"]))

@app.route("/reset/<user_id>", methods=["GET", "POST"])
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
