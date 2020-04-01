$memprocfs_location = "D:\Projects\MemProcFS_files_and_binaries_v3.2-20200316"
New-Item -ItemType Directory -Path "$memprocfs_location\RemoteMemoryScanner" -force
Copy-Item ".\RemoteMemoryScanner.py" -Destination "$memprocfs_location" -force
Copy-Item ".\RemoteMemoryScanner\MainWindow.ui" -Destination "$memprocfs_location\RemoteMemoryScanner\MainWindow.ui" -force
Copy-Item ".\RemoteMemoryScanner\OpenProcessDialog.ui" -Destination "$memprocfs_location\RemoteMemoryScanner\OpenProcessDialog.ui" -force
Copy-Item ".\RemoteMemoryScanner\SearchEngine.py" -Destination "$memprocfs_location\RemoteMemoryScanner\SearchEngine.py" -force
Copy-Item ".\RemoteMemoryScanner\UserInterface.py" -Destination "$memprocfs_location\RemoteMemoryScanner\UserInterface.py" -force
python "$memprocfs_location\RemoteMemoryScanner.py"
