from flask import Flask, request, jsonify
import socket
import multiprocessing
import time
import uuid
import os

app = Flask(__name__)

API_KEY = "ronak_secure_key_here"

ACTIVE_TEST = None
COMPLETED_TESTS = {}

running_flag = False

CPU_CORES = os.cpu_count()
MAX_WORKERS = min(max(CPU_CORES * 8, 16), 40)


def udp_sender(ip, port, packet_size, duration, delay):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.setsockopt(socket.SOL_SOCKET,
                    socket.SO_SNDBUF,
                    4 * 1024 * 1024)

    packet = b"x" * packet_size

    end_time = time.time() + duration

    while time.time() < end_time:

        sock.sendto(packet, (ip, port))

        if delay > 0:
            time.sleep(delay)

    sock.close()


def run_test(task_id,
             ip,
             port,
             duration,
             packet_size,
             workers,
             delay):

    global ACTIVE_TEST
    global running_flag

    running_flag = True

    processes = []

    for _ in range(workers):

        p = multiprocessing.Process(
            target=udp_sender,
            args=(ip,
                  port,
                  packet_size,
                  duration,
                  delay)
        )

        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    COMPLETED_TESTS[task_id] = {

        "ip": ip,
        "port": port,
        "workers": workers,
        "packet_size": packet_size,
        "duration": duration,
        "status": "completed"
    }

    ACTIVE_TEST = None
    running_flag = False


@app.route("/")
def dashboard():

    return jsonify({

        "service": "Adaptive Network Test API",

        "cpu_cores": CPU_CORES,

        "recommended_workers": MAX_WORKERS,

        "test_running": running_flag

    })


@app.route("/test")
def start_test():

    global ACTIVE_TEST
    global running_flag

    key = request.args.get("key")

    ip = request.args.get("ip")

    port = request.args.get("port", type=int)

    duration = request.args.get("time", default=60, type=int)

    packet_size = request.args.get("size", default=1024, type=int)

    workers = request.args.get("workers",
                               default=MAX_WORKERS,
                               type=int)

    delay = request.args.get("delay",
                             default=0,
                             type=float)

    if key != API_KEY:

        return jsonify({

            "status": False,

            "message": "Unauthorized"

        })

    if running_flag:

        return jsonify({

            "status": False,

            "message": "Another test already running"

        })

    if workers > 40:
        workers = 40

    try:

        socket.inet_aton(ip)

    except:

        return jsonify({

            "status": False,

            "message": "Invalid IP"

        })

    task_id = str(uuid.uuid4())

    ACTIVE_TEST = task_id

    multiprocessing.Process(

        target=run_test,

        args=(task_id,
              ip,
              port,
              duration,
              packet_size,
              workers,
              delay)

    ).start()

    return jsonify({

        "status": True,

        "task_id": task_id,

        "workers": workers,

        "duration": duration

    })


@app.route("/status")
def status():

    task_id = request.args.get("task_id")

    if ACTIVE_TEST == task_id:

        return jsonify({

            "status": "running"

        })

    if task_id in COMPLETED_TESTS:

        return jsonify(COMPLETED_TESTS[task_id])

    return jsonify({

        "status": "not_found"

    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000)
