import sys
import time
from PyQt5 import QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg
import threading
import queue
from sys import argv

stop = False
start_time = time.time()


class App(QtWidgets.QMainWindow):
    def __init__(self, recv, title, x_label, y_label):
        super(App, self).__init__()

        #### Create Gui Elements ###########
        self.mainbox = QtWidgets.QWidget()
        self.setCentralWidget(self.mainbox)
        self.mainbox.setLayout(QtWidgets.QVBoxLayout())

        self.canvas = pg.GraphicsLayoutWidget()
        self.mainbox.layout().addWidget(self.canvas)

        #  line plot
        self.plot = self.canvas.addPlot()
        self.plot.setLabel('bottom', x_label)
        self.plot.setLabel('left', y_label)
        self.plot_items = [self.plot.plot()]
        self.channels = 1 # the number of generated channels. might grow
        self.setWindowTitle(title)

        self.recv = recv
        self.x_data = np.array([])
        self.y_data = [[]]

        self.max_len = 200

        #### Start  #####################
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._update)
        self.timer.start()


    def _update(self):
        getting_data = True
        got_new_data = False

        while getting_data:
            try:
                new_x, new_y = self.recv.get(False)
                self.x_data = np.append(self.x_data, new_x)
                while self.channels < len(new_y):
                    self.channels += 1
                    self.plot_items.append(self.plot.plot())
                    self.y_data.append([]) # add the new list for the channel

                for i in range(self.channels):
                    self.y_data[i].append(new_y[i])

                if len(self.x_data) > self.max_len:
                    self.x_data = self.x_data[-self.max_len:]
                    for i in range(self.channels):
                        self.y_data[i] = self.y_data[i][-self.max_len:]
                got_new_data = True

            except queue.Empty:
                getting_data = False

        if got_new_data:
            for i in range(self.channels):
                self.plot_items[i].setData(x=self.x_data, y=np.array(self.y_data[i]))
            self.plot.autoRange()


def parse_stdin(channel):
    global stop
    x = 0
    while not stop:
        line = input()
        y = list(map(float, line.split()))
        channel.put((x, y))
        x = time.time() - start_time


if __name__ == '__main__':
    titel = argv[1] if len(argv) > 1 else "display"
    x_label = argv[2] if len(argv) > 2 else "x"
    y_label = argv[3] if len(argv) > 3 else "y"

    app = QtWidgets.QApplication([])
    channel = queue.SimpleQueue()
    thisapp = App(channel, titel, x_label, y_label)
    threading.Thread(target=lambda: parse_stdin(channel)).start()
    thisapp.show()
    done = app.exec_()
    stop = True
    sys.exit()
