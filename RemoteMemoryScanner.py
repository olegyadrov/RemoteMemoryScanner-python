import sys
from enum import Enum
from vmmpy import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *

MaxReadSize = 16777216 # trying to read more than 16 mb gives the following error:
                       # RuntimeError: VMMPYC_MemRead: Read larger than maximum supported (0x01000000) bytes requested.

                    # readAddress = baseAddress
                    # memoryBuffer = VmmPy_MemRead(searchEngine.pid, readAddress, memoryRegionSize)
                    # offset = 0
                    # while offset < memoryRegionSize - typeSize:
                    #     testBytes = memoryBuffer[offset:offset+typeSize]
                    #     testNumber = int.from_bytes(testBytes, byteorder="little", signed=True)
                    #     if searchCondition == SearchCondition.ExactValue and testNumber == scanIteration.absoluteValue:
                    #         scanIteration.addresses.append(readAddress + offset)
                    #     offset += 1

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
    def __init__(self):
        super().__init__()
        self.type = ValueType.IntegerType
        self.iterations = []
    def newScan(self, searchCondition, valueType, value):
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
                testBytes = VmmPy_MemRead(searchEngine.pid, address, typeSize)
                testNumber = int.from_bytes(testBytes, byteorder="little", signed=True)
                if searchCondition == SearchCondition.ExactValue and testNumber == scanIteration.absoluteValue:
                    scanIteration.addresses.append(address)
        else:
            pteMap = VmmPy_ProcessGetPteMap(searchEngine.pid, True)
            includeMappedModules = ui.main_window.checkBoxMappedModulesOption.isChecked()
            for memoryRegion in pteMap:
                if memoryRegion["tag"] and not includeMappedModules:
                    continue
                memoryRegionSize = memoryRegion["size"]
                baseAddress = memoryRegion["va"]
                endAddress = baseAddress + memoryRegionSize
                readAddress = baseAddress
                readSize = min([MaxReadSize, endAddress - readAddress])
                while True:
                    memoryBuffer = VmmPy_MemRead(searchEngine.pid, readAddress, readSize)
                    offset = 0
                    while offset < memoryRegionSize - typeSize:
                        testBytes = memoryBuffer[offset:offset+typeSize]
                        testNumber = int.from_bytes(testBytes, byteorder="little", signed=True)
                        if searchCondition == SearchCondition.ExactValue and testNumber == scanIteration.absoluteValue:
                            scanIteration.addresses.append(readAddress + offset)
                        offset += 1
                    if readSize == MaxReadSize:
                        print("Done scanning " + hex(readAddress) + " - " + hex(readAddress + readSize) + " subinterval")
                    readAddress = readAddress + readSize - typeSize + 1
                    if readSize != MaxReadSize:
                        break
                    else:
                        readSize = min([MaxReadSize, endAddress - readAddress])
                print("Done scanning " + hex(baseAddress) + " - " + hex(endAddress) + " interval")
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
        self.scanHistory = ScanHistory()
        self.addressMonitor = AddressMonitor()
    def __del__(self):
        VmmPy_Close()
    def setPid(self, pid):
        self.pid = pid
        self.pidChanged.emit()

class UserInterface():
    def __init__(self):
        searchEngine.pidChanged.connect(self.onPidChanged)
        self.initMainWindow()
        self.initOpenProcessDialog()
        self.searchResultsUpdateTimer = QTimer()
    def clearTableWidget(self, tableWidget):
        while tableWidget.rowCount() > 0:
            tableWidget.removeRow(0)
    def selectedSearchCondition(self):
        switcher = {
            0: SearchCondition.ExactValue
        }
        return switcher.get(self.main_window.comboBoxScanType, SearchCondition.ExactValue)
    def selectedValueType(self):
        switcher = {
            0: ValueType.IntegerType
        }
        return switcher.get(self.main_window.comboBoxValueType, ValueType.IntegerType)
    def initMainWindow(self):
        ui_loader = QUiLoader()
        ui_file = QFile("RemoteMemoryScanner/MainWindow.ui")
        ui_file.open(QFile.ReadOnly)
        self.main_window = ui_loader.load(ui_file)
        self.main_window.tableWidgetSearchResults.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetSearchResults.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetSearchResults.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetSearchResults.itemDoubleClicked.connect(self.onFoundAddressDoubleClicked)
        self.main_window.tableWidgetAddresses.insertingData = False # quick hack; todo: get rid of this and use QTableView instead of QTableWidget
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(3).setTextAlignment(Qt.AlignLeft)
        self.main_window.actionOpenProcess.triggered.connect(self.onShowOpenProcessActionTriggered)
        self.main_window.pushButtonFirstScan.clicked.connect(self.onFirstScanButtonClicked)
        self.main_window.pushButtonNextScan.clicked.connect(self.onNextScanButtonClicked)
        self.main_window.pushButtonUndoScan.clicked.connect(self.onUndoLastScanButtonClicked)
        self.main_window.spinBoxDisplayIfLessThan.valueChanged.connect(self.onDisplayIfLessThanValueChanged)
        self.main_window.pushButtonRefreshFoundValues.clicked.connect(self.onRefreshFoundValuesButtonClicked)
        self.main_window.tableWidgetAddresses.cellChanged.connect(self.onMonitoredValueChanged)
        searchEngine.scanHistory.updated.connect(self.onScanHistoryUpdated)
        searchEngine.addressMonitor.updated.connect(self.updateAddressesTable)
    def initOpenProcessDialog(self):
        ui_loader = QUiLoader()
        ui_file = QFile("RemoteMemoryScanner/OpenProcessDialog.ui")
        ui_file.open(QFile.ReadOnly)
        self.open_process_dialog = ui_loader.load(ui_file)
        self.open_process_dialog.tableWidgetProcesses.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.open_process_dialog.tableWidgetProcesses.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        self.open_process_dialog.tableWidgetProcesses.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        self.open_process_dialog.tableWidgetProcesses.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.open_process_dialog.tableWidgetProcesses.setSelectionMode(QAbstractItemView.SingleSelection)
        self.open_process_dialog.pushButtonCancel.clicked.connect(self.onHideOpenProcessActionTriggered)
        self.open_process_dialog.pushButtonOpen.clicked.connect(self.onOpenProcessButtonClicked)
        self.open_process_dialog.pushButtonRefresh.clicked.connect(searchEngine.processList.refresh)
        self.open_process_dialog.checkBoxFilterByName.toggled.connect(self.refreshProcessList)
        searchEngine.processList.updated.connect(self.refreshProcessList)
    def onShowOpenProcessActionTriggered(self):
        searchEngine.processList.refresh()
        self.open_process_dialog.show()
    def onHideOpenProcessActionTriggered(self):
        self.open_process_dialog.close()
    def refreshProcessList(self):
        self.clearTableWidget(self.open_process_dialog.tableWidgetProcesses)
        for process in searchEngine.processList.list:
            pid = searchEngine.processList.list[process]["pid"]
            name = searchEngine.processList.list[process]["name-long"]
            path = searchEngine.processList.list[process]["path-user"]
            nameFilter = self.open_process_dialog.lineEditFilter.text()
            if self.open_process_dialog.checkBoxFilterByName.isChecked() and not nameFilter in name:
                continue
            rowIndex = self.open_process_dialog.tableWidgetProcesses.rowCount()
            self.open_process_dialog.tableWidgetProcesses.insertRow(rowIndex)
            pidItem = QTableWidgetItem(str(pid))
            pidItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            nameItem = QTableWidgetItem(name)
            nameItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            pathItem = QTableWidgetItem(path)
            pathItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.open_process_dialog.tableWidgetProcesses.setItem(rowIndex, 0, pidItem)
            self.open_process_dialog.tableWidgetProcesses.setItem(rowIndex, 1, nameItem)
            self.open_process_dialog.tableWidgetProcesses.setItem(rowIndex, 2, pathItem)
            self.open_process_dialog.tableWidgetProcesses.resizeColumnsToContents()
    def onOpenProcessButtonClicked(self):
        if len(self.open_process_dialog.tableWidgetProcesses.selectedItems()) > 0:
            selectedRowIndex = self.open_process_dialog.tableWidgetProcesses.selectedItems()[0].row()
            selectedPid = self.open_process_dialog.tableWidgetProcesses.item(selectedRowIndex, 0).text()
            searchEngine.setPid(int(selectedPid))
            self.open_process_dialog.close()
        else:
            messageBox = QMessageBox()
            messageBox.setIcon(QMessageBox.Warning)
            messageBox.setWindowTitle("Error")
            messageBox.setText("Select a process from the list")
            messageBox.setStandardButtons(QMessageBox.Ok)
            messageBox.exec()
    def onPidChanged(self):
        processName = "No Process Selected"
        controlsEnabled = False
        if searchEngine.pid >= 0:
            processName = searchEngine.processList.list[searchEngine.pid]["name-long"] + " (" + str(searchEngine.pid) + ")"
            controlsEnabled = True
        self.main_window.labelSelectedProcess.setText(processName)
        self.main_window.pushButtonFirstScan.setEnabled(controlsEnabled)
        self.main_window.labelValue.setEnabled(controlsEnabled)
        self.main_window.lineEditValue.setEnabled(controlsEnabled)
        self.main_window.lineEditValue.setText("")
        self.main_window.labelScanType.setEnabled(controlsEnabled)
        self.main_window.comboBoxScanType.setEnabled(controlsEnabled)
        self.main_window.comboBoxScanType.setCurrentIndex(0)
        self.main_window.labelValueType.setEnabled(controlsEnabled)
        self.main_window.comboBoxValueType.setEnabled(controlsEnabled)
        self.main_window.comboBoxValueType.setCurrentIndex(0)
        self.main_window.groupBoxMemoryScanOptions.setEnabled(controlsEnabled)
        self.clearTableWidget(self.main_window.tableWidgetSearchResults)
        self.clearTableWidget(self.main_window.tableWidgetAddresses)
        self.main_window.labelFound.setText("Found: 0")
    def onFirstScanButtonClicked(self):
        searchCondition = self.selectedSearchCondition()
        valueType = self.selectedValueType()
        value = int(self.main_window.lineEditValue.text()) # todo: add validation
        searchEngine.scanHistory.newScan(searchCondition, valueType, value)
    def onNextScanButtonClicked(self):
        searchCondition = self.selectedSearchCondition()
        value = int(self.main_window.lineEditValue.text()) # todo: add validation
        searchEngine.scanHistory.nextScan(searchCondition, value)
    def onUndoLastScanButtonClicked(self):
        searchEngine.scanHistory.undoLastScan()
    def onDisplayIfLessThanValueChanged(self):
        iterationCount = len(searchEngine.scanHistory.iterations)
        if iterationCount == 0:
            return
        lastIteration = searchEngine.scanHistory.iterations[-1]
        addressCount = len(lastIteration.addresses)
        displayIfLessThan = self.main_window.spinBoxDisplayIfLessThan.value()
        if self.main_window.tableWidgetSearchResults.rowCount() == 0 and addressCount < displayIfLessThan:
            self.updateSearchResultsTable()
        elif addressCount >= displayIfLessThan:
            self.clearTableWidget(self.main_window.tableWidgetSearchResults)
    def updateSearchResultsTable(self):
        self.clearTableWidget(self.main_window.tableWidgetSearchResults)
        iterationCount = len(searchEngine.scanHistory.iterations)
        if iterationCount == 0:
            return
        lastIteration = searchEngine.scanHistory.iterations[-1]
        addressCount = len(lastIteration.addresses)
        displayIfLessThan = self.main_window.spinBoxDisplayIfLessThan.value()
        typeSize = TypeSize(searchEngine.scanHistory.type)
        if addressCount < displayIfLessThan:
            addressIndex = 0
            while addressIndex < addressCount:
                valueBytes = VmmPy_MemRead(searchEngine.pid, lastIteration.addresses[addressIndex], typeSize)
                value = None
                if searchEngine.scanHistory.type == ValueType.IntegerType:
                    value = int.from_bytes(valueBytes, byteorder="little", signed=True)
                self.main_window.tableWidgetSearchResults.insertRow(addressIndex)
                addressItem = QTableWidgetItem(hex(lastIteration.addresses[addressIndex]))
                addressItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                valueItem = QTableWidgetItem(str(value))
                valueItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                previousValueItem = QTableWidgetItem(str(lastIteration.absoluteValue))
                previousValueItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.main_window.tableWidgetSearchResults.setItem(addressIndex, 0, addressItem)
                self.main_window.tableWidgetSearchResults.setItem(addressIndex, 1, valueItem)
                self.main_window.tableWidgetSearchResults.setItem(addressIndex, 2, previousValueItem)
                self.main_window.tableWidgetSearchResults.resizeColumnsToContents()
                addressIndex += 1
    def onScanHistoryUpdated(self):
        iterationCount = len(searchEngine.scanHistory.iterations)
        self.main_window.labelIteration.setText("Iteration: " + str(iterationCount))
        self.main_window.pushButtonFirstScan.setEnabled(iterationCount == 0)
        self.main_window.pushButtonNextScan.setEnabled(iterationCount > 0)
        self.main_window.pushButtonUndoScan.setEnabled(iterationCount > 0)
        self.main_window.labelValueType.setEnabled(iterationCount == 0)
        self.main_window.comboBoxValueType.setEnabled(iterationCount == 0)
        self.clearTableWidget(self.main_window.tableWidgetSearchResults)
        if iterationCount == 0:
            self.main_window.labelFound.setText("Found: 0")
            return
        lastIteration = searchEngine.scanHistory.iterations[-1]
        addressCount = len(lastIteration.addresses)
        self.main_window.labelFound.setText("Found: " + str(addressCount))
        self.updateSearchResultsTable()
    def onRefreshFoundValuesButtonClicked(self):
        self.updateSearchResultsTable() # todo: just sync values, do not clear & refill
    def onFoundAddressDoubleClicked(self, tableWidgetItem):
        monitoredValue = MonitoredValue()
        monitoredValue.type = searchEngine.scanHistory.type
        addressIndex = tableWidgetItem.row()
        lastIteration = searchEngine.scanHistory.iterations[-1]
        monitoredValue.address = lastIteration.addresses[addressIndex]
        searchEngine.addressMonitor.addValue(monitoredValue)
    def updateAddressesTable(self):
        self.clearTableWidget(self.main_window.tableWidgetAddresses)
        addressCount = len(searchEngine.addressMonitor.list)
        addressIndex = 0
        self.main_window.tableWidgetAddresses.insertingData = True
        while addressIndex < addressCount:
            monitoredValue = searchEngine.addressMonitor.list[addressIndex]
            valueBytes = VmmPy_MemRead(searchEngine.pid, monitoredValue.address, TypeSize(monitoredValue.type))
            value = None
            if monitoredValue.type == ValueType.IntegerType:
                value = int.from_bytes(valueBytes, byteorder="little", signed=True)
            self.main_window.tableWidgetAddresses.insertRow(addressIndex)
            descriptionItem = QTableWidgetItem(monitoredValue.description)
            descriptionItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            addressItem = QTableWidgetItem(hex(monitoredValue.address))
            addressItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            typeItem = QTableWidgetItem(ValueTypeToString(monitoredValue.type))
            typeItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            valueItem= QTableWidgetItem(str(value))
            valueItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.main_window.tableWidgetAddresses.setItem(addressIndex, 0, descriptionItem)
            self.main_window.tableWidgetAddresses.setItem(addressIndex, 1, addressItem)
            self.main_window.tableWidgetAddresses.setItem(addressIndex, 2, typeItem)
            self.main_window.tableWidgetAddresses.setItem(addressIndex, 3, valueItem)
            self.main_window.tableWidgetAddresses.resizeColumnsToContents()
            addressIndex += 1
        self.main_window.tableWidgetAddresses.insertingData = False
    def onMonitoredValueChanged(self, row, column):
        if self.main_window.tableWidgetAddresses.insertingData == True:
            return
        if column == 3:
            monitoredValue = searchEngine.addressMonitor.list[row]
            address = monitoredValue.address
            size = TypeSize(monitoredValue.type)
            newValueAsString = self.main_window.tableWidgetAddresses.item(row, column).text()
            newValueBytes = None
            if monitoredValue.type == ValueType.IntegerType:
                newValueBytes = (int(newValueAsString)).to_bytes(size, byteorder="little", signed=True)
            VmmPy_MemWrite(searchEngine.pid, address, newValueBytes)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    searchEngine = SearchEngine()
    ui = UserInterface()
    ui.main_window.show()
    sys.exit(app.exec_())
