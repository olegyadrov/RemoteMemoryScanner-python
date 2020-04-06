# RemoteMemoryScanner

Memory scanner tool compatible with [PCILeech-FPGA](https://github.com/ufrisk/pcileech) devices.

The goal is to provide functionality similar to [Cheat Engine](https://github.com/cheat-engine/cheat-engine).

At this point it is nothing more than a proof-of-concept, it is slow (scan & analysis are done in the main thread) and lacking functionality (only integer numbers are currently supported).

![screenshot](https://user-images.githubusercontent.com/6189747/78515297-2dfcc380-776a-11ea-83ac-5c81bb775284.png)

## Dependencies:
  * [MemProcFS](https://github.com/ufrisk/MemProcFS):
```
https://github.com/ufrisk/MemProcFS/releases/latest
```
  * [PySide 2](https://doc.qt.io/qtforpython/):
```
pip install pyside2
```

## How to use:
Put the files into MemProcFS folder next to vmmpy.py, then run
```
python RemoteMemoryScanner.py
```

## Note for developers:
  * If you are planning on modifying the source code, you can use provided "deploy.ps1" PowerShell script.
  * Only the user interface is dependent on Qt (PySide2). The search engine is being developed in a way so it can be used independently with any other Python script.
  
