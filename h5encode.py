import numpy as np
import h5py
from sys import argv, stdin


def main():
    chunksize = 10000
    file = h5py.File(argv[1], 'w')
    event_type = np.dtype([("long", np.uint32), ("short", np.uint32), ("timestamp", np.uint64), ("channel", np.uint8)])
    events = file.create_dataset("events", shape=(chunksize,), maxshape=(None,), dtype=event_type, chunks=True)

    chunk_count = 1
    count = 0

    line = ""

    print('starting write')
    while True:
        line = input()
        l, s, t, c = map(lambda x: int(x), line.split(','))

        if count >= chunksize * chunk_count:
            print(f"wrote {chunksize * chunk_count} events")
            chunk_count += 1
            events.resize((chunksize * chunk_count,))

        #events[count] = {"long": l, "short": s, "timestamp": t, "channel": c}
        events[count] = (l, s, t, c)
        count += 1

    file.close()


if __name__ == "__main__":
    main()
