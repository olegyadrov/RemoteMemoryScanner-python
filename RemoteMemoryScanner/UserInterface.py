from enum import Enum
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from SearchEngine import *

class UserInterface():
    def __init__(self, search_engine):
        self.search_engine = search_engine
        self.search_engine.pidChanged.connect(self.onPidChanged)
        self.initMainWindow()
        self.initOpenProcessDialog()
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
        self.search_engine.scanHistory.updated.connect(self.onScanHistoryUpdated)
        self.search_engine.addressMonitor.updated.connect(self.updateAddressesTable)
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
        self.open_process_dialog.pushButtonRefresh.clicked.connect(self.search_engine.processList.refresh)
        self.open_process_dialog.checkBoxFilterByName.toggled.connect(self.refreshProcessList)
        self.search_engine.processList.updated.connect(self.refreshProcessList)
    def onShowOpenProcessActionTriggered(self):
        self.search_engine.processList.refresh()
        self.open_process_dialog.show()
    def onHideOpenProcessActionTriggered(self):
        self.open_process_dialog.close()
    def refreshProcessList(self):
        self.clearTableWidget(self.open_process_dialog.tableWidgetProcesses)
        for process in self.search_engine.processList.list:
            pid = self.search_engine.processList.list[process]["pid"]
            name = self.search_engine.processList.list[process]["name-long"]
            path = self.search_engine.processList.list[process]["path-user"]
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
            self.search_engine.setPid(int(selectedPid))
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
        if self.search_engine.pid >= 0:
            processName = self.search_engine.processList.list[self.search_engine.pid]["name-long"] + " (" + str(self.search_engine.pid) + ")"
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
        self.search_engine.scanHistory.newScan(self.main_window.checkBoxMappedModulesOption.isChecked(), searchCondition, valueType, value)
    def onNextScanButtonClicked(self):
        searchCondition = self.selectedSearchCondition()
        value = int(self.main_window.lineEditValue.text()) # todo: add validation
        self.search_engine.scanHistory.nextScan(searchCondition, value)
    def onUndoLastScanButtonClicked(self):
        self.search_engine.scanHistory.undoLastScan()
    def onDisplayIfLessThanValueChanged(self):
        iterationCount = len(self.search_engine.scanHistory.iterations)
        if iterationCount == 0:
            return
        lastIteration = self.search_engine.scanHistory.iterations[-1]
        addressCount = len(lastIteration.addresses)
        displayIfLessThan = self.main_window.spinBoxDisplayIfLessThan.value()
        if self.main_window.tableWidgetSearchResults.rowCount() == 0 and addressCount < displayIfLessThan:
            self.updateSearchResultsTable()
        elif addressCount >= displayIfLessThan:
            self.clearTableWidget(self.main_window.tableWidgetSearchResults)
    def updateSearchResultsTable(self):
        self.clearTableWidget(self.main_window.tableWidgetSearchResults)
        iterationCount = len(self.search_engine.scanHistory.iterations)
        if iterationCount == 0:
            return
        lastIteration = self.search_engine.scanHistory.iterations[-1]
        addressCount = len(lastIteration.addresses)
        displayIfLessThan = self.main_window.spinBoxDisplayIfLessThan.value()
        typeSize = TypeSize(self.search_engine.scanHistory.type)
        if addressCount < displayIfLessThan:
            addressIndex = 0
            while addressIndex < addressCount:
                valueBytes = VmmPy_MemRead(self.search_engine.pid, lastIteration.addresses[addressIndex], typeSize)
                value = None
                if self.search_engine.scanHistory.type == ValueType.IntegerType:
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
        iterationCount = len(self.search_engine.scanHistory.iterations)
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
        lastIteration = self.search_engine.scanHistory.iterations[-1]
        addressCount = len(lastIteration.addresses)
        self.main_window.labelFound.setText("Found: " + str(addressCount))
        self.updateSearchResultsTable()
    def onRefreshFoundValuesButtonClicked(self):
        self.updateSearchResultsTable() # todo: just sync values, do not clear & refill
    def onFoundAddressDoubleClicked(self, tableWidgetItem):
        monitoredValue = MonitoredValue()
        monitoredValue.type = self.search_engine.scanHistory.type
        addressIndex = tableWidgetItem.row()
        lastIteration = self.search_engine.scanHistory.iterations[-1]
        monitoredValue.address = lastIteration.addresses[addressIndex]
        self.search_engine.addressMonitor.addValue(monitoredValue)
    def updateAddressesTable(self):
        self.clearTableWidget(self.main_window.tableWidgetAddresses)
        addressCount = len(self.search_engine.addressMonitor.list)
        addressIndex = 0
        self.main_window.tableWidgetAddresses.insertingData = True
        while addressIndex < addressCount:
            monitoredValue = self.search_engine.addressMonitor.list[addressIndex]
            valueBytes = VmmPy_MemRead(self.search_engine.pid, monitoredValue.address, TypeSize(monitoredValue.type))
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
            monitoredValue = self.search_engine.addressMonitor.list[row]
            address = monitoredValue.address
            size = TypeSize(monitoredValue.type)
            newValueAsString = self.main_window.tableWidgetAddresses.item(row, column).text()
            newValueBytes = None
            if monitoredValue.type == ValueType.IntegerType:
                newValueBytes = (int(newValueAsString)).to_bytes(size, byteorder="little", signed=True)
            VmmPy_MemWrite(self.search_engine.pid, address, newValueBytes)
