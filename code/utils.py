import time


def getCurrentTimeString():
    time.sleep(0.002)
    return str(round(time.time() * 1000))
