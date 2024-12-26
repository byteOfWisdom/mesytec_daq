import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from sys import stdin

long = []
short = []
lock = threading.Lock();

file = stdin

def read_data():
    global long, short, lock
    while True:
            event = file.readline().split(',')
            if len(event) == 1:
                continue
            lock.acquire()
            long.append(int(event[0]))
            short.append(int(event[1]))
            lock.release()


def update(frame):
    global long, short
    plt.clf()
    plt.xlabel("long")
    plt.ylabel("(long - short) / long")
    lock.acquire()

    along = np.array(long)
    ashort = np.array(short)
    lock.release()
    plt.hist2d(along, (along - ashort) / along, (100, 50), [[0, 40000], [-0.2, 0.45]])

t = threading.Thread(target=read_data)
t.start()
animation = FuncAnimation(plt.gcf(), update, interval=500, cache_frame_data=False)
plt.show()
