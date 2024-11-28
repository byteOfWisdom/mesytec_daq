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
    plt.clf()
    plt.xlabel("long")
    plt.ylabel("(long + short) / long")
    lock.acquire()

    along = np.array(long)
    ashort = np.array(short)
    lock.release()
    #bins = np.histogram2d(along, (along - ashort) / along, [100, 20])
    #plt.scatter(np.array(long), (np.array(long) + np.array(short)) / np.array(long), marker='x')
    plt.hist2d(along, (along - ashort) / along, (100, 50), [[0, 40000], [-0.2, 0.45]])

t = threading.Thread(target=read_data)
t.start()
animation = FuncAnimation(plt.gcf(), update, interval=500, cache_frame_data=False)
plt.show()
