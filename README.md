# LimitTar
This application is for limiting the size of a tar archive for spanning data
directly across multiple Blu-Ray/DVD discs, flash drives or as files on
online storage with file size limits. It tries to fit as many files as possible
into a tar archive without creating partial files. This means each tar archive
can be restored independently without joining.

This application was mainly developed to be used with
[aes-pipe.py](https://github.com/2sh/aes-pipe.py) for space efficient data
encryption using pipes to remove the need for temporarily storing the
potentially large archives and encrypted data.

Use the ```-h``` argument for help:
```
python3 limittar.py -h
```

## Requirements
* Python 3.4+

## Usage Examples

### Spanning files in tar archives across multiple USB storage devices
```
find /path/photos/ -print0 > files

python3 limittar.py -0 -i files -l remaining1 -s 16g > /dev/sdX
python3 limittar.py -0 -i remaining1 -l remaining2 -s 20g > /dev/sdX
...
```
