from enum import Enum
from vmmpy import *
from PySide2.QtCore import *

MaxReadSize = 16777216 # VMMPYC_MemRead limitation (16 mb)

class ValueType(Enum):
    IntegerType = 0

def TypeSize(valueType):
    switcher = {
        ValueType.IntegerType: 4
    }
    return switcher.get(valueType, 0)

def ValueTypeToString(valueType):
    switcher = {
        ValueType.IntegerType: "Integer"
    }
    return switcher.get(valueType, "Unknown")

class SearchCondition(Enum):
    ExactValue = 0

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
        self.searchCondition = SearchCondition.ExactValue
        self.searchValue = 0
        self.absoluteValue = 0
        self.addresses = []

class ScanHistory(QObject):
    updated = Signal()
    def __init__(self, search_engine):
        super().__init__()
        self.search_engine = search_engine
        self.includeMappedModules = False
        self.type = ValueType.IntegerType
        self.iterations = []
    def newScan(self, includeMappedModules, searchCondition, valueType, value):
        self.includeMappedModules = includeMappedModules
        self.type = valueType
        self.iterations = []
        self.nextScan(searchCondition, value)
    def undoLastScan(self):
        if len(self.iterations) > 0:
            del self.iterations[-1]
            self.updated.emit()
    def nextScan(self, searchCondition, value):
        typeSize = TypeSize(self.type)
        scanIteration = ScanIteration()
        scanIteration.searchValue = value
        scanIteration.absoluteValue = value
        if len(self.iterations) > 0:
            lastIteration = self.iterations[-1]
            #scanIteration.absoluteValue += lastIteration.searchValue
            for address in lastIteration.addresses:
                testBytes = VmmPy_MemRead(self.search_engine.pid, address, typeSize)
                testNumber = int.from_bytes(testBytes, byteorder="little", signed=True)
                if searchCondition == SearchCondition.ExactValue and testNumber == scanIteration.absoluteValue:
                    scanIteration.addresses.append(address)
        else:
            pteMap = VmmPy_ProcessGetPteMap(self.search_engine.pid, True)
            for memoryRegion in pteMap:
                if memoryRegion["tag"] and not self.includeMappedModules:
                    continue
                memoryRegionSize = memoryRegion["size"]
                baseAddress = memoryRegion["va"]
                endAddress = baseAddress + memoryRegionSize
                readAddress = baseAddress
                readSize = min([MaxReadSize, endAddress - readAddress])
                while True:
                    memoryBuffer = VmmPy_MemRead(self.search_engine.pid, readAddress, readSize)
                    offset = 0
                    while offset < memoryRegionSize - typeSize:
                        testBytes = memoryBuffer[offset:offset+typeSize]
                        testNumber = int.from_bytes(testBytes, byteorder="little", signed=True)
                        if searchCondition == SearchCondition.ExactValue and testNumber == scanIteration.absoluteValue:
                            scanIteration.addresses.append(readAddress + offset)
                        offset += 1
                    # todo: make debug output optional
                    # if readSize == MaxReadSize:
                    #    print("Done scanning " + hex(readAddress) + " - " + hex(readAddress + readSize) + " subinterval")
                    readAddress = readAddress + readSize - typeSize + 1
                    if readSize != MaxReadSize:
                        break
                    else:
                        readSize = min([MaxReadSize, endAddress - readAddress])
                # print("Done scanning " + hex(baseAddress) + " - " + hex(endAddress) + " interval")
        self.iterations.append(scanIteration)
        self.updated.emit()

class MonitoredValue():
    def __init__(self):
        self.address = 0
        self.type = ValueType.IntegerType
        self.description = ""

class AddressMonitor(QObject):
    updated = Signal()
    def __init__(self):
        super().__init__()
        self.list = []
        self.updateInterval = 1000
    def addValue(self, value):
        if not isinstance(value, MonitoredValue):
            return
        self.list.append(value)
        self.updated.emit()
    def removeValueAtIndex(self, index):
        if index >= 0 and index < len(self.list):
            del self.list[index]
            self.updated.emit()

class SearchEngine(QObject):
    pidChanged = Signal()
    def __init__(self):
        super().__init__()
        VmmPy_Initialize(['-device', 'fpga'])
        self.pid = -1
        self.processList = ProcessList()
        self.scanHistory = ScanHistory(self)
        self.addressMonitor = AddressMonitor()
    def __del__(self):
        VmmPy_Close()
    def setPid(self, pid):
        self.pid = pid
        self.pidChanged.emit()
