import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

long = []
short = []
lock = threading.Lock();

file = open("build/test.fifo", 'r')

def read_data():
    global long, short, lock
    while True:
            event = file.readline().split(',')
            lock.acquire()
            long.append(int(event[0]))
            short.append(int(event[1]))
            lock.release()


def update(frame):
    global long, short
    plt.cla()
    plt.ylim([1, 2.5])
    plt.xlabel("long")
    plt.ylabel("(long + short) / long")
    lock.acquire()
    plt.scatter(np.array(long), (np.array(long) + np.array(short)) / np.array(long), marker='x')
    lock.release()

t = threading.Thread(target=read_data)
t.start()
animation = FuncAnimation(plt.gcf(), update, interval=500, cache_frame_data=False)
plt.show()
