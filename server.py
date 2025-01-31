import socket
import threading
from utils import encrypt, decrypt
import re
import numpy as np
import time
from collections import defaultdict


PRICE_TICK_DIGITS = 2
PRICE_TICK = 0.01
PRICE_MAX = 1000
LEGAL_SYMBOLS = ['AAA','BBB']
class Order:
    def __init__(self, id, side, symbol, volume):
        self.id = id
        self.side = side
        self.symbol = symbol
        self.volume = volume
        self.otime = str(time.time_ns())
    
class LimitOrder(Order):
    def __init__(self, id, side, symbol, price, volume):
        super().__init__(id, side, symbol, volume)
        self.price = price

class TimedLimitOrder(LimitOrder):
    def __init__(self, id, side, symbol, price, volume, timeout):
        super().__init__(id, side, symbol, price, volume)
        self.timeout = timeout

class MarketOrder(Order):
    def __init__(self, id, side, symbol, volume):
        super().__init__(id, side, symbol, volume)

class LastingMarketOrder(MarketOrder):
    def __init__(self, id, side, symbol, volume):
        super().__init__(id, side, symbol, volume)
        self.is_instant = False

class InstantMarketOrder(MarketOrder):
    def __init__(self, id, side, symbol, volume):
        super().__init__(id, side, symbol, volume)
        self.is_instant = True

class Orderbook:
    def __init__(self):
        self.bids = defaultdict(list)
        self.asks = defaultdict(list)
        self.bv = defaultdict(int)
        self.av = defaultdict(int)
        self.bestb = 0
        self.besta = PRICE_MAX
        self.lim_orders = {}
        self.mkt_order = None

    def append(self, order:Order):
        if isinstance(order, MarketOrder):
            self.mkt_order = order
            return
        if isinstance(order, LimitOrder):
            order.price = round(order.price, PRICE_TICK_DIGITS)
            self.lim_orders[order.otime] = order.price
            if order.side == 'a':
                self.asks[order.price].append(order)
                self.av[order.price] += order.volume
                if order.price < self.besta:
                    self.besta = order.price
            else:
                self.bids[order.price].append(order)
                self.bv[order.price] += order.volume
                if order.price > self.bestb:
                    self.bestb = order.price

    def cancel(self, otime:str):
        pass


class Server:
    def __init__(self, legal_clients, host='127.0.0.1', port=12345):
        self.odbs = {s:Orderbook() for s in LEGAL_SYMBOLS}
        self.clients = {}
        self.legal_clients = legal_clients
        self.host, self.port = host, port
        self.last_message = None
        self.new_message = None
        


    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"listening at {self.host}:{self.port} ...")
            engine = threading.Thread(target=self.engine, args=())
            engine.start()
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.start()
    
    def handle_client(self, conn:socket.socket, addr):
        is_monitor = False
        id = None
        with conn:
            print(f"connected to {addr}")
            while True:
                if is_monitor:
                    # if time.time_ns() > self.last_time:
                    #     conn.sendall(encrypt(str(self.odb)).encode())
                    #     self.last_time = time.time_ns()
                    if self.last_message != self.new_message:
                        conn.sendall(encrypt(str(self.new_message)).encode())
                        self.last_message = self.new_message
                    continue
                data = conn.recv(1024)
                if not data:
                    continue
                datastr = decrypt(data.decode())
                print(datastr)
                ret = None
                if (match:=re.match(r'monitor', datastr)):
                    is_monitor = True
                    continue
                if (match:=re.match(r'login@([a-zA-Z0-9]+):([a-zA-Z0-9]+)', datastr)):
                    id = match.group(1)
                    passwd = match.group(2)
                    if (id, passwd) not in self.legal_clients:
                        break
                    ckey = abs(hash(f'{id}{passwd}')+np.random.randint(100000))
                    self.clients[id] = str(ckey)
                    ret = ckey
                elif (match:=re.match(r'([a-zA-Z0-9]+)&([0-9]+)order@([ab]):([A-Z]+):(\d+(?:\.\d+)?):([0-9]+)', datastr)):
                    id, ckey, side, symbol, price, volume = (match.group(i) for i in range(1, 7))
                    try:
                        if self.clients[id] != ckey:
                            break
                    except KeyError:
                        break
                    # TODO: Add into odb
                    lorder = LimitOrder(id, side, symbol, float(price), int(volume))
                    self.odbs[symbol].append(lorder)
                    ret = lorder.otime
                elif (match:=re.match(r'([a-zA-Z0-9]+)&([0-9]+)order@([ab]):([A-Z]+):(\d+(?:\.\d+)?):([0-9]+):([0-9]+)', datastr)):
                    id, ckey, side, symbol, price, volume, timeout = (match.group(i) for i in range(1, 8))
                    try:
                        if self.clients[id] != ckey:
                            break
                    except KeyError:
                        break
                    # TODO: Add into odb
                    tlorder = TimedLimitOrder(id, side, symbol, float(price), int(volume), int(timeout))
                    self.odbs[symbol].append(tlorder)
                    ret = tlorder.otime
                elif (match:=re.match(r'([a-zA-Z0-9]+)&([0-9]+)order@([ab]):([LI]):([A-Z]+):([0-9]+)', datastr)):
                    id, ckey, side, tp, symbol, volume = (match.group(i) for i in range(1, 7))
                    try:
                        if self.clients[id] != ckey:
                            break
                    except KeyError:
                        break
                    # TODO: Add into odb
                    if tp == 'L':
                        morder = LastingMarketOrder(id, side, symbol, int(volume))
                    else:
                        morder = InstantMarketOrder(id, side, symbol, int(volume))
                    self.odbs[symbol].append(morder)
                    ret = morder.otime

                if ret:
                    conn.sendall(encrypt(str(ret)).encode())
                else:
                    conn.sendall(encrypt(str("Illegal request")).encode())
                


    def engine(self):
        def report(order, price, volume):
            self.new_message = f"{order} traded at {price} for {volume}"
            return
        last_time = time.time_ns()
        while True:
            lock = threading.Lock()
            with lock:
                for odb_ in self.odbs.values():
                    if odb_.mkt_order:
                        order = odb_.mkt_order
                        if order.is_instant:
                            if order.side == 'b':
                                while odb_.asks[odb_.besta]:
                                    if order.volume < odb_.asks[odb_.besta][0].volume:
                                        odb_.asks[odb_.besta][0].volume -= order.volume
                                        odb_.av[odb_.besta] -= order.volume
                                        # report partial trade of LO & full trade of MO
                                        # report(order.otime, odb_.besta, order.volume)
                                        break
                                    order.volume -= odb_.asks[odb_.besta][0].volume
                                    traded = odb_.asks[odb_.besta].pop(0)
                                    odb_.lim_orders.pop(traded.otime)
                                    odb_.av[odb_.besta] -= traded.volume
                                    # report full trade of LO
                                    if order.volume == 0:
                                        # report full trade of MO
                                        break
                                if order.volume > 0:
                                    # report partial trade of MO
                                    pass
                                while len(odb_.asks[odb_.besta]) <= 0 and odb_.besta < PRICE_MAX:
                                    odb_.besta = round(odb_.besta + PRICE_TICK, PRICE_TICK_DIGITS)
                            else:
                                while odb_.bids[odb_.bestb]:
                                    if order.volume < odb_.bids[odb_.bestb][0].volume:
                                        odb_.bids[odb_.bestb][0].volume -= order.volume
                                        odb_.bv[odb_.besta] -= order.volume
                                        # report partial trade of LO & full trade of MO
                                        break
                                    order.volume -= odb_.bids[odb_.bestb][0].volume
                                    traded = odb_.bids[odb_.bestb].pop(0)
                                    odb_.lim_orders.pop(traded.otime)
                                    odb_.bv[odb_.bestb] -= traded.volume
                                    # report full trade of LO
                                    if order.volume == 0:
                                        # report full trade of MO
                                        break
                                if order.volume > 0:
                                    # report partial trade of MO
                                    pass
                                while len(odb_.bids[odb_.bestb]) <= 0 and odb_.bestb > 0:
                                    odb_.bestb = round(odb_.bestb - PRICE_TICK, PRICE_TICK_DIGITS)
                        else:
                            raise NotImplementedError("Lasting MO not implemented")
                        odb_.mkt_order = None
                    while odb_.besta <= odb_.bestb:
                        frontier_a, frontier_b = odb_.asks[odb_.besta][0], odb_.bids[odb_.bestb][0]
                        traded_p = frontier_a.price if frontier_a.otime < frontier_b.otime else frontier_b.price
                        if frontier_a.volume > frontier_b.volume:
                            odb_.asks[odb_.besta][0].volume -= frontier_b.volume
                            odb_.av[odb_.besta] -= frontier_b.volume
                            odb_.bv[odb_.bestb] -= frontier_b.volume
                            odb_.bids[odb_.bestb].pop(0)
                            # report
                        elif frontier_a.volume < frontier_b.volume:
                            odb_.bids[odb_.bestb][0].volume -= frontier_a.volume
                            odb_.av[odb_.besta] -= frontier_a.volume
                            odb_.bv[odb_.bestb] -= frontier_a.volume
                            odb_.asks[odb_.besta].pop(0)
                            # report
                        else:
                            odb_.av[odb_.besta] -= frontier_a.volume
                            odb_.bv[odb_.bestb] -= frontier_a.volume
                            odb_.asks[odb_.besta].pop(0)
                            odb_.bids[odb_.bestb].pop(0)
                            # report
                        while len(odb_.bids[odb_.bestb]) <= 0 and odb_.bestb > 0:
                            odb_.bestb = round(odb_.bestb - PRICE_TICK, PRICE_TICK_DIGITS)
                        while len(odb_.asks[odb_.besta]) <= 0 and odb_.besta < PRICE_MAX:
                            odb_.besta = round(odb_.besta + PRICE_TICK, PRICE_TICK_DIGITS)
                if time.time_ns() - last_time > 1e9:
                    for symbol in self.odbs.keys():
                        print(f'{symbol}:{self.odbs[symbol].bestb if self.odbs[symbol].bestb > 0 else None} -|- {self.odbs[symbol].besta if self.odbs[symbol].besta < PRICE_MAX else None}')
                    last_time = time.time_ns()

