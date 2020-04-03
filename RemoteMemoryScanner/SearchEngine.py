from enum import *
from vmmpy import *

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
    BIGGER_THAN = 1
    SMALLER_THAN = 2
    VALUE_BETWEEN = 3

def SearchConditionAsHumanReadableString(search_condition):
    switcher = {
        SearchCondition.EXACT_VALUE: "Exact Value",
        SearchCondition.BIGGER_THAN: "Bigger than...",
        SearchCondition.SMALLER_THAN: "Smaller than...",
        SearchCondition.VALUE_BETWEEN: "Value between..."
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

def CheckValue(search_condition, search_value, value):
    if search_condition == SearchCondition.EXACT_VALUE:
        return (value == search_value)
    elif search_condition == SearchCondition.BIGGER_THAN:
        return (value > search_value)
    elif search_condition == SearchCondition.SMALLER_THAN:
        return (value < search_value)
    elif search_condition == SearchCondition.VALUE_BETWEEN:
        return (value > search_value["from"] and value < search_value["to"])

class ProcessList():
    def __init__(self):
        self.callback_updated = None
        self.list = []
    def refresh(self):
        self.list = VmmPy_ProcessListInformation()
        if callable(self.callback_updated):
            self.callback_updated()

class ScanIteration():
    def __init__(self):
        self.search_condition = None
        self.search_value = 0
        self.absolute_search_value = 0
        self.found_addresses = []

class ScanHistory():
    MAX_READ_SIZE = 16777216 # VMMPYC_MemRead limitation (16 mb)
    def __init__(self, search_engine):
        self.callback_updated = None
        self.search_engine = search_engine
        self.include_mapped_modules = False
        self.value_type = None
        self.iterations = []
    def new_scan(self, include_mapped_modules, search_condition, value_type, value):
        self.include_mapped_modules = include_mapped_modules
        self.value_type = value_type
        self.iterations = []
        self.next_scan(search_condition, value)
    def undo_last_scan(self):
        if len(self.iterations) > 0:
            del self.iterations[-1]
            if callable(self.callback_updated):
                self.callback_updated()
    def next_scan(self, search_condition, value):
        type_size = TypeSize(self.value_type)
        scan_iteration = ScanIteration()
        scan_iteration.search_value = value
        if search_condition == SearchCondition.EXACT_VALUE or \
            search_condition == SearchCondition.BIGGER_THAN or \
            search_condition == SearchCondition.SMALLER_THAN or \
            search_condition == SearchCondition.VALUE_BETWEEN:
            scan_iteration.absolute_search_value = value
        if len(self.iterations) > 0: # second or the following scan
            last_iteration = self.iterations[-1]
            for address in last_iteration.found_addresses:
                test_bytes = VmmPy_MemRead(self.search_engine.pid, address, type_size)
                test_value = ConvertBytesToValue(test_bytes, self.value_type)
                if CheckValue(search_condition, scan_iteration.absolute_search_value, test_value):
                    scan_iteration.found_addresses.append(address)
        else: # first scan
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
                        test_value = ConvertBytesToValue(test_bytes, self.value_type)
                        if CheckValue(search_condition, scan_iteration.absolute_search_value, test_value):
                            scan_iteration.found_addresses.append(read_address + offset)
                        offset += 1
                    read_address = read_address + read_size - type_size + 1
                    if read_size != self.MAX_READ_SIZE:
                        break
                    else:
                        read_size = min([self.MAX_READ_SIZE, end_address - read_address])
        self.iterations.append(scan_iteration)
        if callable(self.callback_updated):
            self.callback_updated()

class MonitoredValue():
    def __init__(self):
        self.address = 0
        self.value_type = None
        self.description = ""

class AddressMonitor():
    def __init__(self):
        self.callback_updated = None
        self.list = []
    def add_value(self, value):
        if not isinstance(value, MonitoredValue):
            return
        self.list.append(value)
        if callable(self.callback_updated):
            self.callback_updated()
    def remove_value_at_index(self, index):
        if index >= 0 and index < len(self.list):
            del self.list[index]
            if callable(self.callback_updated):
                self.callback_updated()

class SearchEngine():
    def __init__(self):
        VmmPy_Initialize(['-device', 'fpga'])
        self.callback_pid_changed = None
        self.pid = -1
        self.process_list = ProcessList()
        self.scan_history = ScanHistory(self)
        self.address_monitor = AddressMonitor()
    def __del__(self):
        VmmPy_Close()
    def set_pid(self, pid):
        self.pid = pid
        if callable(self.callback_pid_changed):
            self.callback_pid_changed()
