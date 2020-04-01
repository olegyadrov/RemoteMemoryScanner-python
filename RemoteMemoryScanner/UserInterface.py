from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from SearchEngine import *

class UserInterface():
    def __init__(self, search_engine):
        self.search_engine = search_engine
        self.search_engine.pid_changed.connect(self.on_pid_changed)
        self.init_main_window()
        self.init_open_process_dialog()
    def clear_table_widget(self, table_widget):
        while table_widget.rowCount() > 0:
            table_widget.removeRow(0)
    def init_main_window(self):
        ui_loader = QUiLoader()
        ui_file = QFile("RemoteMemoryScanner/MainWindow.ui")
        ui_file.open(QFile.ReadOnly)
        self.main_window = ui_loader.load(ui_file)
        self.main_window.tableWidgetSearchResults.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetSearchResults.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetSearchResults.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetSearchResults.itemDoubleClicked.connect(self.on_found_address_double_clicked)
        self.main_window.tableWidgetAddresses.insertingData = False # quick hack; todo: get rid of this and use QTableView instead of QTableWidget
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        self.main_window.tableWidgetAddresses.horizontalHeaderItem(3).setTextAlignment(Qt.AlignLeft)
        for value_type in ValueType:
            self.main_window.comboBoxValueType.addItem(ValueTypeAsHumanReadableString(value_type))
        self.main_window.comboBoxValueType.setCurrentIndex(ValueType.FOUR_BYTES)
        for search_condition in SearchCondition:
            self.main_window.comboBoxScanType.addItem(SearchConditionAsHumanReadableString(search_condition))
        self.main_window.actionOpenProcess.triggered.connect(self.on_show_open_process_action_triggered)
        self.main_window.pushButtonFirstScan.clicked.connect(self.on_first_scan_button_clicked)
        self.main_window.pushButtonNextScan.clicked.connect(self.on_next_scan_button_clicked)
        self.main_window.pushButtonUndoScan.clicked.connect(self.on_undo_last_scan_button_clicked)
        self.main_window.spinBoxDisplayIfLessThan.valueChanged.connect(self.on_display_if_less_than_value_changed)
        self.main_window.pushButtonRefreshFoundValues.clicked.connect(self.on_refresh_found_values_button_clicked)
        self.main_window.tableWidgetAddresses.cellChanged.connect(self.on_monitored_value_changed)
        self.search_engine.scan_history.updated.connect(self.on_scan_history_updated)
        self.search_engine.address_monitor.updated.connect(self.update_addresses_table)
    def init_open_process_dialog(self):
        ui_loader = QUiLoader()
        ui_file = QFile("RemoteMemoryScanner/OpenProcessDialog.ui")
        ui_file.open(QFile.ReadOnly)
        self.open_process_dialog = ui_loader.load(ui_file)
        self.open_process_dialog.tableWidgetProcesses.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.open_process_dialog.tableWidgetProcesses.horizontalHeaderItem(1).setTextAlignment(Qt.AlignLeft)
        self.open_process_dialog.tableWidgetProcesses.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft)
        self.open_process_dialog.tableWidgetProcesses.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.open_process_dialog.tableWidgetProcesses.setSelectionMode(QAbstractItemView.SingleSelection)
        self.open_process_dialog.pushButtonCancel.clicked.connect(self.on_hide_open_process_action_triggered)
        self.open_process_dialog.pushButtonOpen.clicked.connect(self.on_open_process_button_clicked)
        self.open_process_dialog.pushButtonRefresh.clicked.connect(self.search_engine.process_list.refresh)
        self.open_process_dialog.checkBoxFilterByName.toggled.connect(self.refresh_process_list)
        self.search_engine.process_list.updated.connect(self.refresh_process_list)
    def on_show_open_process_action_triggered(self):
        self.search_engine.process_list.refresh()
        self.open_process_dialog.show()
    def on_hide_open_process_action_triggered(self):
        self.open_process_dialog.close()
    def refresh_process_list(self):
        self.clear_table_widget(self.open_process_dialog.tableWidgetProcesses)
        for process in self.search_engine.process_list.list:
            pid = self.search_engine.process_list.list[process]["pid"]
            name = self.search_engine.process_list.list[process]["name-long"]
            path = self.search_engine.process_list.list[process]["path-user"]
            name_filter = self.open_process_dialog.lineEditFilter.text()
            if self.open_process_dialog.checkBoxFilterByName.isChecked() and name_filter not in name:
                continue
            row_index = self.open_process_dialog.tableWidgetProcesses.rowCount()
            self.open_process_dialog.tableWidgetProcesses.insertRow(row_index)
            pid_item = QTableWidgetItem(str(pid))
            pid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            path_item = QTableWidgetItem(path)
            path_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.open_process_dialog.tableWidgetProcesses.setItem(row_index, 0, pid_item)
            self.open_process_dialog.tableWidgetProcesses.setItem(row_index, 1, name_item)
            self.open_process_dialog.tableWidgetProcesses.setItem(row_index, 2, path_item)
            self.open_process_dialog.tableWidgetProcesses.resizeColumnsToContents()
    def on_open_process_button_clicked(self):
        if len(self.open_process_dialog.tableWidgetProcesses.selectedItems()) > 0:
            selected_row_index = self.open_process_dialog.tableWidgetProcesses.selectedItems()[0].row()
            selected_pid = self.open_process_dialog.tableWidgetProcesses.item(selected_row_index, 0).text()
            self.search_engine.set_pid(int(selected_pid))
            self.open_process_dialog.close()
        else:
            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Warning)
            message_box.setWindowTitle("Error")
            message_box.setText("Select a process from the list")
            message_box.setStandardButtons(QMessageBox.Ok)
            message_box.exec()
    def on_pid_changed(self):
        process_name = "No Process Selected"
        controls_enabled = False
        if self.search_engine.pid >= 0:
            process_name = self.search_engine.process_list.list[self.search_engine.pid]["name-long"] + " (" + str(self.search_engine.pid) + ")"
            controls_enabled = True
        self.main_window.labelSelectedProcess.setText(process_name)
        self.main_window.pushButtonFirstScan.setEnabled(controls_enabled)
        self.main_window.labelValue.setEnabled(controls_enabled)
        self.main_window.lineEditValue.setEnabled(controls_enabled)
        self.main_window.lineEditValue.setText("")
        self.main_window.labelScanType.setEnabled(controls_enabled)
        self.main_window.comboBoxScanType.setEnabled(controls_enabled)
        self.main_window.comboBoxScanType.setCurrentIndex(0)
        self.main_window.labelValueType.setEnabled(controls_enabled)
        self.main_window.comboBoxValueType.setEnabled(controls_enabled)
        self.main_window.comboBoxValueType.setCurrentIndex(ValueType.FOUR_BYTES)
        self.main_window.groupBoxMemoryScanOptions.setEnabled(controls_enabled)
        self.clear_table_widget(self.main_window.tableWidgetSearchResults)
        self.clear_table_widget(self.main_window.tableWidgetAddresses)
        self.main_window.labelFound.setText("Found: 0")
    def on_first_scan_button_clicked(self):
        search_condition = SearchCondition(self.main_window.comboBoxScanType.currentIndex())
        value_type = ValueType(self.main_window.comboBoxValueType.currentIndex())
        value = int(self.main_window.lineEditValue.text()) # todo: add validation
        self.search_engine.scan_history.new_scan(self.main_window.checkBoxMappedModulesOption.isChecked(), search_condition, value_type, value)
    def on_next_scan_button_clicked(self):
        search_condition = SearchCondition(self.main_window.comboBoxScanType.currentIndex())
        value = int(self.main_window.lineEditValue.text()) # todo: add validation
        self.search_engine.scan_history.next_scan(search_condition, value)
    def on_undo_last_scan_button_clicked(self):
        self.search_engine.scan_history.undo_last_scan()
    def on_display_if_less_than_value_changed(self):
        iteration_count = len(self.search_engine.scan_history.iterations)
        if iteration_count == 0:
            return
        last_iteration = self.search_engine.scan_history.iterations[-1]
        address_count = len(last_iteration.addresses)
        display_if_less_than = self.main_window.spinBoxDisplayIfLessThan.value()
        if self.main_window.tableWidgetSearchResults.rowCount() == 0 and address_count < display_if_less_than:
            self.update_search_results_table()
        elif address_count >= display_if_less_than:
            self.clear_table_widget(self.main_window.tableWidgetSearchResults)
    def update_search_results_table(self):
        self.clear_table_widget(self.main_window.tableWidgetSearchResults)
        iteration_count = len(self.search_engine.scan_history.iterations)
        if iteration_count == 0:
            return
        last_iteration = self.search_engine.scan_history.iterations[-1]
        address_count = len(last_iteration.addresses)
        display_if_less_than = self.main_window.spinBoxDisplayIfLessThan.value()
        type_size = TypeSize(self.search_engine.scan_history.type)
        if address_count < display_if_less_than:
            address_index = 0
            while address_index < address_count:
                value_bytes = VmmPy_MemRead(self.search_engine.pid, last_iteration.addresses[address_index], type_size)
                value = ConvertBytesToValue(value_bytes, self.search_engine.scan_history.type)
                self.main_window.tableWidgetSearchResults.insertRow(address_index)
                address_item = QTableWidgetItem(hex(last_iteration.addresses[address_index]))
                address_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                value_item = QTableWidgetItem(str(value))
                value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                previous_value_item = QTableWidgetItem(str(last_iteration.absolute_value))
                previous_value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.main_window.tableWidgetSearchResults.setItem(address_index, 0, address_item)
                self.main_window.tableWidgetSearchResults.setItem(address_index, 1, value_item)
                self.main_window.tableWidgetSearchResults.setItem(address_index, 2, previous_value_item)
                self.main_window.tableWidgetSearchResults.resizeColumnsToContents()
                address_index += 1
    def on_scan_history_updated(self):
        iteration_count = len(self.search_engine.scan_history.iterations)
        self.main_window.labelIteration.setText("Iteration: " + str(iteration_count))
        self.main_window.pushButtonFirstScan.setEnabled(iteration_count == 0)
        self.main_window.pushButtonNextScan.setEnabled(iteration_count > 0)
        self.main_window.pushButtonUndoScan.setEnabled(iteration_count > 0)
        self.main_window.labelValueType.setEnabled(iteration_count == 0)
        self.main_window.comboBoxValueType.setEnabled(iteration_count == 0)
        self.clear_table_widget(self.main_window.tableWidgetSearchResults)
        if iteration_count == 0:
            self.main_window.labelFound.setText("Found: 0")
            return
        last_iteration = self.search_engine.scan_history.iterations[-1]
        address_count = len(last_iteration.addresses)
        self.main_window.labelFound.setText("Found: " + str(address_count))
        self.update_search_results_table()
    def on_refresh_found_values_button_clicked(self):
        self.update_search_results_table() # todo: just sync values, do not clear & refill
    def on_found_address_double_clicked(self, table_widget_item):
        monitored_value = MonitoredValue()
        monitored_value.type = self.search_engine.scan_history.type
        address_index = table_widget_item.row()
        last_iteration = self.search_engine.scan_history.iterations[-1]
        monitored_value.address = last_iteration.addresses[address_index]
        self.search_engine.address_monitor.add_value(monitored_value)
    def update_addresses_table(self):
        self.clear_table_widget(self.main_window.tableWidgetAddresses)
        address_count = len(self.search_engine.address_monitor.list)
        address_index = 0
        self.main_window.tableWidgetAddresses.insertingData = True
        while address_index < address_count:
            monitored_value = self.search_engine.address_monitor.list[address_index]
            value_bytes = VmmPy_MemRead(self.search_engine.pid, monitored_value.address, TypeSize(monitored_value.type))
            value = ConvertBytesToValue(value_bytes, monitored_value.type)
            self.main_window.tableWidgetAddresses.insertRow(address_index)
            description_item = QTableWidgetItem(monitored_value.description)
            description_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            address_item = QTableWidgetItem(hex(monitored_value.address))
            address_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            type_item = QTableWidgetItem(ValueTypeAsHumanReadableString(monitored_value.type))
            type_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            value_item= QTableWidgetItem(str(value))
            value_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.main_window.tableWidgetAddresses.setItem(address_index, 0, description_item)
            self.main_window.tableWidgetAddresses.setItem(address_index, 1, address_item)
            self.main_window.tableWidgetAddresses.setItem(address_index, 2, type_item)
            self.main_window.tableWidgetAddresses.setItem(address_index, 3, value_item)
            self.main_window.tableWidgetAddresses.resizeColumnsToContents()
            address_index += 1
        self.main_window.tableWidgetAddresses.insertingData = False
    def on_monitored_value_changed(self, row, column):
        if self.main_window.tableWidgetAddresses.insertingData == True:
            return
        if column == 3:
            monitored_value = self.search_engine.address_monitor.list[row]
            address = monitored_value.address
            size = TypeSize(monitored_value.type)
            new_value_as_string = self.main_window.tableWidgetAddresses.item(row, column).text()
            new_value_bytes = ConvertValueToBytes(int(new_value_as_string), monitored_value.type)
            VmmPy_MemWrite(self.search_engine.pid, address, new_value_bytes)
