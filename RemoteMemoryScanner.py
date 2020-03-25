import sys
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from vmmpy import *
sys.path.append("RemoteMemoryScanner")
from SearchEngine import *
from UserInterface import *

if __name__ == "__main__":
    app = QApplication(sys.argv)
    search_engine = SearchEngine()
    user_interface = UserInterface(search_engine)
    user_interface.main_window.show()
    sys.exit(app.exec_())
