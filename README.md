# LimitTar
This application/library is for limiting the size of a tar archive for spanning
data directly across multiple Blu-Ray/DVD discs, flash drives or as files on
online storage with file size limits. It tries to fit as many files as possible
into a tar archive without creating partial files. This means each tar archive
can be restored independently without joining.

This application was mainly developed to be used with
[aes-pipe](https://github.com/2sh/aes-pipe) for space efficient data
encryption using pipes to remove the need for temporarily storing the
potentially large archives and encrypted data.

## Requirements
* Python 3.4+

## Installation
From the Python Package Index:
```
pip install limittar
```

Or download and run:
```
python3 setup.py install
```

## Command-Line Usage
Use the ```-h``` argument for help:
```
limittar -h
```

### Spanning files in tar archives across multiple USB storage devices
```
find /path/photos/ -print0 > files

limittar -0 -i files -l remaining1 -s 16g > /dev/sdX
limittar -0 -i remaining1 -l remaining2 -s 20g > /dev/sdX
cat remaining2 | limittar -0 -l remaining3 -s 16g > /dev/sdX
...
```
