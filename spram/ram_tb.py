import cocotb
from cocotb_bus.scoreboard import Scoreboard
from cocotb_bus.bus import Bus
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor
from array import array
import random
from cocotb.regression import TestFactory
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge,ReadOnly
from cocotb_coverage.coverage import *
from cocotb_coverage.crv import *

covered_rw = []
covered_addr = []
covered_data = []

RAM_Coverage = coverage_section (
    CoverPoint("top.rw", vname="rw", bins = [False, True]),
    CoverPoint("top.addr", vname="addr", bins = list(range(0,64))),
    CoverPoint("top.din", vname="din", bins = list(range(0,256))),
    CoverPoint("top.dout", vname="dout", bins = list(range(0,256))),
    CoverCross("top.write_addr", items = ["top.rw", "top.addr"],ign_bins = [(False, None)]),
    CoverCross("top.read_addr", items = ["top.rw", "top.addr"],ign_bins = [(True, None)]),
    CoverCross("top.write_data", items = ["top.rw", "top.din"],ign_bins = [(False, None)]),
    CoverCross("top.read_data", items = ["top.rw", "top.din"],ign_bins = [(True, None)])

)

@RAM_Coverage
def sample(rw, addr, din, dout):
    covered_rw.append(rw)
    covered_rw.append(addr)
    covered_rw.append(din)
     


class RamMasterDriver(BusDriver):
    _signals = ["we", "data", "addr", "q"]

    def __init__(self, entity, name, clock, **kwargs):
        BusDriver.__init__(self, entity, name, clock, **kwargs)
        self.bus.we.setimmediatevalue(0)
        self.bus.data.setimmediatevalue(0)
        self.bus.addr.setimmediatevalue(0)

    async def _wait_ready(self):
        await ReadOnly()

    async def _driver_send(self, pkt, sync: bool = True):
        clkedge = RisingEdge(self.clock)
        await clkedge
        self.bus.addr <= pkt['addr']
        self.bus.data <= pkt['data']
        self.bus.we   <= pkt['rw']
class RamMasterMonitor(BusMonitor):
    _signals = ["we", "data", "addr", "q"]

    def __init__(self, entity, name, clock, **kwargs):
        BusMonitor.__init__(self, entity,name, clock, **kwargs)
        self.pre_we = 0
        self.pre_addr = 0
        
    async def _monitor_recv(self):
        clkedge = RisingEdge(self.clock)
        rdonly  = ReadOnly()

        while True:
            await clkedge
            await rdonly

            if self.in_reset:
                continue
            sample(self.bus.we.value, self.bus.addr.value, self.bus.data.value, self.bus.q.value)
            self._recv({'rw': self.pre_we, 'addr': self.pre_addr, 'data': self.bus.q.value})
            self.pre_we = self.bus.we.value
            self.pre_addr = self.bus.addr.value

            # self._recv({'rw':self.bus.we.value, 'addr':self.bus.addr.value, 'data':self.bus.q.value})
            # print("addr: %x, data: %x"%(self.bus.addr.value, self.bus.q.value))
class RefModel:
    def __init__(self):
        self.arr = array('B')
        for i in range(0,64):
            self.arr.append(0)
    def write(self, addr, data):
        self.arr[addr] = data
        return self.arr[addr]
    def read(self, addr):
        return self.arr[addr]
    def op(self, rw, addr, data):
        if(rw):
            return self.write(addr, data)
        else:
            return self.read(addr)

   
class RamGen(Randomized):
    def __init__(self):
        Randomized.__init__(self)
        self.rw   = 0
        self.addr = 0
        self.din  = 0

        self.add_rand("rw", [0, 1])
        self.add_rand("addr", list(range(0, 64)))
        self.add_rand("din", list(range(0, 256)))

        self.add_constraint(lambda addr: addr not in covered_addr)
        self.add_constraint(lambda din: din  not in covered_data)

    #def post_randomize(self):
    #    self.din = [np.random.randint(256)]


class RamTB(object):

    def __init__(self, dut):
        self.dut = dut
        self.refmodel = RefModel()
        self.data_in = RamMasterDriver(dut, None, dut.clk)
        self.data_in_rec = RamMasterMonitor(dut, None, dut.clk, callback=self.model)
       
        self.expected_output = []
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.data_in_rec, self.expected_output)
      
    def model(self, trans):
        data1 = self.refmodel.op(trans['rw'], trans['addr'], trans['data'])
        self.expected_output.append({'rw': trans['rw'], 'addr': trans['addr'], 'data': data1})
        # print("Expect: rw: %d, addr:%d, data: %d"%(trans['rw'], trans['addr'], data1))
    async def init_dut(self):
        for i in range(0, 64):
            self.dut.ram[i] <= 0

async def ram_test(dut):
    log = cocotb.logging.getLogger("cocotb.test")
    cocotb.fork(Clock(dut.clk, 10, units='ns').start())
    tb = RamTB(dut)

    await tb.init_dut()
    test = RamGen()
    for _ in range(10000):
        test.randomize()
        await tb.data_in._driver_send({'addr':test.addr,'data':test.din,'rw':test.rw})
   
    coverage_db.report_coverage(log.info, bins=False)
    coverage_db.export_to_xml(filename="coverage_ram.xml")
    coverage_db.export_to_yaml(filename="coverage_ram.yaml")
    raise tb.scoreboard.result

ram_factory = TestFactory(ram_test)
ram_factory.generate_tests()


