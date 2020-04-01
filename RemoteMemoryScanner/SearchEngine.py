from enum import *
from vmmpy import *
from PySide2.QtCore import *

class ValueType(IntEnum):
    ONE_BYTE = 0
    TWO_BYTES = 1
    FOUR_BYTES = 2
    EIGHT_BYTES = 3

def TypeSize(value_type):
    switcher = {
        ValueType.ONE_BYTE: 1,
        ValueType.TWO_BYTES: 2,
        ValueType.FOUR_BYTES: 4,
        ValueType.EIGHT_BYTES: 8
    }
    return switcher.get(value_type, 0)

def ValueTypeAsHumanReadableString(value_type):
    switcher = {
        ValueType.ONE_BYTE: "Byte",
        ValueType.TWO_BYTES: "2 Bytes",
        ValueType.FOUR_BYTES: "4 Bytes",
        ValueType.EIGHT_BYTES: "8 Bytes"
    }
    return switcher.get(value_type, "Unknown")

class SearchCondition(IntEnum):
    EXACT_VALUE = 0

def SearchConditionAsHumanReadableString(search_condition):
    switcher = {
        SearchCondition.EXACT_VALUE: "Exact Value"
    }
    return switcher.get(search_condition, "Unknown")

def ConvertBytesToValue(bytes, value_type):
    return_value = None
    if value_type == ValueType.ONE_BYTE or \
        value_type == ValueType.TWO_BYTES or \
        value_type == ValueType.FOUR_BYTES or \
        value_type == ValueType.EIGHT_BYTES:
        return_value = int.from_bytes(bytes, byteorder="little", signed=True)
    return return_value

def ConvertValueToBytes(value, value_type):
    return_value = None
    if value_type == ValueType.ONE_BYTE or \
        value_type == ValueType.TWO_BYTES or \
        value_type == ValueType.FOUR_BYTES or \
        value_type == ValueType.EIGHT_BYTES:
        return_value = (value.to_bytes(TypeSize(value_type), byteorder="little", signed=True))
    return return_value

class ProcessList(QObject):
    updated = Signal()
    def __init__(self):
        super().__init__()
        self.list = []
    def refresh(self):
        self.list = VmmPy_ProcessListInformation()
        self.updated.emit()

class ScanIteration():
    def __init__(self):
        self.search_condition = None
        self.search_value = 0
        self.absolute_value = 0
        self.addresses = []

class ScanHistory(QObject):
    MAX_READ_SIZE = 16777216 # VMMPYC_MemRead limitation (16 mb)
    updated = Signal()
    def __init__(self, search_engine):
        super().__init__()
        self.search_engine = search_engine
        self.include_mapped_modules = False
        self.type = None
        self.iterations = []
    def new_scan(self, include_mapped_modules, search_condition, value_type, value):
        self.include_mapped_modules = include_mapped_modules
        self.type = value_type
        self.iterations = []
        self.next_scan(search_condition, value)
    def undo_last_scan(self):
        if len(self.iterations) > 0:
            del self.iterations[-1]
            self.updated.emit()
    def next_scan(self, search_condition, value):
        type_size = TypeSize(self.type)
        scan_iteration = ScanIteration()
        scan_iteration.search_value = value
        scan_iteration.absolute_value = value
        if len(self.iterations) > 0:
            last_iteration = self.iterations[-1]
            #scan_iteration.absolute_value += last_iteration.search_value
            for address in last_iteration.addresses:
                test_bytes = VmmPy_MemRead(self.search_engine.pid, address, type_size)
                test_number = ConvertBytesToValue(test_bytes, self.type)
                if search_condition == SearchCondition.EXACT_VALUE and test_number == scan_iteration.absolute_value:
                    scan_iteration.addresses.append(address)
        else:
            pte_map = VmmPy_ProcessGetPteMap(self.search_engine.pid, True)
            for memory_region in pte_map:
                if memory_region["tag"] and not self.include_mapped_modules:
                    continue
                memory_region_size = memory_region["size"]
                base_address = memory_region["va"]
                end_address = base_address + memory_region_size
                read_address = base_address
                read_size = min([self.MAX_READ_SIZE, end_address - read_address])
                while True:
                    memoryBuffer = VmmPy_MemRead(self.search_engine.pid, read_address, read_size)
                    offset = 0
                    while offset < memory_region_size - type_size:
                        test_bytes = memoryBuffer[offset:offset+type_size]
                        test_number = ConvertBytesToValue(test_bytes, self.type)
                        if search_condition == SearchCondition.EXACT_VALUE and test_number == scan_iteration.absolute_value:
                            scan_iteration.addresses.append(read_address + offset)
                        offset += 1
                    read_address = read_address + read_size - type_size + 1
                    if read_size != self.MAX_READ_SIZE:
                        break
                    else:
                        read_size = min([self.MAX_READ_SIZE, end_address - read_address])
        self.iterations.append(scan_iteration)
        self.updated.emit()

class MonitoredValue():
    def __init__(self):
        self.address = 0
        self.type = None
        self.description = ""

class AddressMonitor(QObject):
    updated = Signal()
    def __init__(self):
        super().__init__()
        self.list = []
    def add_value(self, value):
        if not isinstance(value, MonitoredValue):
            return
        self.list.append(value)
        self.updated.emit()
    def remove_value_at_index(self, index):
        if index >= 0 and index < len(self.list):
            del self.list[index]
            self.updated.emit()

class SearchEngine(QObject):
    pid_changed = Signal()
    def __init__(self):
        super().__init__()
        VmmPy_Initialize(['-device', 'fpga'])
        self.pid = -1
        self.process_list = ProcessList()
        self.scan_history = ScanHistory(self)
        self.address_monitor = AddressMonitor()
    def __del__(self):
        VmmPy_Close()
    def set_pid(self, pid):
        self.pid = pid
        self.pid_changed.emit()
