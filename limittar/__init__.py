#!/usr/bin/env python3
#
#	limittar - Limiting the size of tar archives
#
#	Copyright (C) 2018 2sh <contact@2sh.me>
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys, os.path

import tarfile
import math

import queue
import threading


class SizeLimitReached(Exception):
	'''Size limit reached exception
	
	This exception is raised when the tar archive has reached its size limit
	and no more files can be added to it.
	'''
	pass

class Underrun(Exception):
	'''Underrun exception
	
	This exception signifies that the path queue became empty while adding
	multiple paths to the queue. This may occur when the size limit is reached
	and further paths are added to find files that fit within the remaining
	space.
	'''
	pass

def determine_tar_file_size(path):
	'''Determine the size of a file within a GNU tar archive
	
	Args:
		path: The file path. The path may be of type str which is encoded as
			UTF-8 or of type bytes in the encoding of the tar archive.
	
	Returns:
		The determined size of the file
	'''
	# 512 byte header
	size = 512
	
	try:
		path = path.encode()
	except:
		pass
	
	# GNU tar path string size workaround
	path_size = len(path)
	if path_size > 100:
		# @LongLink/@LongName header + path string fit within
		# blocks of 512 bytes
		size += 512 + 512 * int(math.ceil(path_size/512))
	
	# Not within the following if statement to raise OSError if not exist
	file_size = os.path.getsize(path)
	
	if os.path.isfile(path):
		# file data fit within blocks of 512 bytes
		size += 512 * int(math.ceil(file_size)/512)
	return size

def determine_tar_archive_size(tar_data_size, bufsize=20*512):
	'''Determine the size of a GNU tar archive given its data
	
	Args:
		tar_data_size: The sum of the sizes of the files to be added to the
			tar archive.
		bufsize: The blocksize of the tar archive.
	
	Returns:
		The determined size of the archive
	'''
	# The end of an archive is marked by two consecutive zero-filled records.
	return int(bufsize * math.ceil((tar_data_size + 512*2)/bufsize))

class LimitTar(threading.Thread):
	'''Size limitted tar archive
	
	Args:
		size_limit: The size limit of the tar archive in bytes.
		kwargs: The keyword arguments of tarfile.open() but fixed to the
			GNU tar format.
	'''
	def __init__(self, size_limit, **kwargs):
		self._size_limit = size_limit
		kwargs = kwargs.copy()
		self._bufsize = kwargs.setdefault("bufsize", 20*512)
		self._encoding = kwargs.setdefault("encoding", tarfile.ENCODING)
		kwargs["format"] = tarfile.GNU_FORMAT
		self._tar = tarfile.open(**kwargs)
		
		self._path_queue = queue.Queue()
		self._data_size = 0
		super().__init__()
	
	@property
	def size(self):
		return determine_tar_archive_size(self._data_size, self._bufsize)
	
	def run(self):
		while 1:
			path = self._path_queue.get()
			if not path:
				break
			self._tar.add(path, recursive=False)
	
	def add_path(self, path):
		'''Add a file to the tar archive.
		
		This method adds a file to the tar archive.
		
		Args:
			path: The file path.
		
		Raises:
			SizeLimitReached: Raised if it is determined that the file would
				cause the tar archive to exceed its size limit.
		'''
		tar_file_size = determine_tar_file_size(path.encode(self._encoding))
		
		predicted_size = self._data_size + tar_file_size
		archive_size = determine_tar_archive_size(
			predicted_size, self._bufsize)
		if self._size_limit and archive_size > self._size_limit:
			raise SizeLimitReached("This file would cause the tar archive to "
				"exceed its size limit")
		
		self._path_queue.put(path)
		self._data_size += tar_file_size
	
	def add_paths(self, paths,
			halt_on_size_limit_reached=False,
			halt_on_underrun=False,
			halt_on_os_error=False):
		'''Add multiple files to the tar archive.
		
		This method adds multiple files to the a processing queue to be added
		to the tar archive.
		
		If this method is halted, any remaining paths are yielded.
		By default if the size limit is reached, the queue underruns or
		an OS error occurs, this method yields the path of the current file and
		attempts to add the next file.
		
		Args:
			paths: The file paths. This can be any kind of iterable.
			halt_on_size_limit_reached: Halt if set and
				the size limit is reached.
			halt_on_underrun: Halt if set and
				the path processing queue becomes empty.
			halt_on_os_error: Halt if set and
				an OS error occurs.
		
		Yields:
			The paths of files which were not added to the tar archive
		'''
		halt = False
		for i, path in enumerate(paths):
			if not path:
				continue
			if not halt:
				if i > 10 and halt_on_underrun and self._path_queue.empty():
					print("Underrun. Halting", file=sys.stderr)
					exception = Underrun("An underrun occured while adding "
						"multiple paths")
					halt = True
				try:
					self.add_path(path)
				except SizeLimitReached as e:
					exception = e
					if halt_on_size_limit_reached:
						halt = True
				except OSError as e:
					exception = e
					print(exception, file=sys.stderr)
					if halt_on_os_error:
						halt = True
				else:
					continue
			yield path, exception
	
	def stop(self):
		'''Stop processing the path processing queue.'''
		self._path_queue.put(None)
	
	def close(self):
		'''Close the tar archive.
		
		This stops the path processing and if named, closes the tar archive.
		'''
		self.join()
		self._tar.close()

def _file_iter_lines_gen(input_file, delimiter, size):
	partial_line = ""
	while True:
		chars = input_file.read(size)
		if not chars:
			break
		partial_line += chars
		lines = partial_line.split(delimiter)
		partial_line = lines.pop()
		for line in lines:
			yield line + delimiter
	if partial_line:
		yield partial_line

def _file_iter_lines(input_file, delimiter="\n", size=8192):
	if delimiter == "\n":
		return input_file
	else:
		return _file_iter_lines_gen(input_file, delimiter, size)

class _FilelistOutFile:
	def __init__(self, path):
		self.path = path
		self.f = None
		try:
			open(self.path, "r").close()
		except:
			pass
		else:
			self.f = open(self.path, "w")
	
	def write(self, data):
		if self.path:
			if not self.f:
				self.f = open(self.path, "w")
			self.f.write(data)
		else:
			print(data, file=sys.stderr)
	
	def close(self):
		if self.f:
			self.f.close()

_metric_prefixes = {
	"K": 1,
	"M": 2,
	"G": 3,
	"T": 4,
	"P": 5,
	"E": 6,
	"Z": 7,
	"Y": 8,
}

def _to_byte_type(value):
	'''Convert a byte unit value with metric unit to an integer.
	
	This is used by this script for converting the input size limit.
	
	Args:
		The byte unit value
	
	Returns:
		The byte value as an integer
	'''
	value = value.upper()
	if not value:
		raise Exception("Size not specified.")
	if value[-1] == "B":
		value = value[:-1]
	if value[-1] == "I":
		if value[-2:-1] in _metric_prefixes:
			return int(float(value[:-2]) * 2**(_metric_prefixes[value[-2]]*10))
		else:
			raise Exception("Invalid binary prefix.")
	elif value[-1] in _metric_prefixes:
		return int(float(value[:-1]) * 1000**_metric_prefixes[value[-1]])
	else:
		return int(value)

def _main():
	import argparse
	
	parser = argparse.ArgumentParser(description="limittar")
	parser.add_argument("-i",
		dest="filelist_in",
		metavar="PATH",
		help="A list of all the individual files and folders to be encrypted. "
			"Takes input from STDIN by default.")
	parser.add_argument("-l",
		dest="filelist_out",
		metavar="PATH",
		help="File to which to write list of files that did not "
			"fit within the size limit or failed.")
	parser.add_argument("-o",
		dest="tar_out",
		metavar="PATH",
		help="Tar file output. Outputs to STDOUT by default.")
	parser.add_argument("-s",
		dest="size",
		type=_to_byte_type,
		help="The size of the destination storage.")
	parser.add_argument("-u",
		dest="no_underrun",
		action="store_true",
		help="Attempt to prevent a buffer underrun. If the buffer is empty, "
			"the output is halted and the paths of any remaining files "
			"are written to the out file list.")
	parser.add_argument("-0",
		dest="null_delimiter",
		action="store_true",
		help="Read and write null (\\0) delimited filelists.")
	
	args = parser.parse_args()
	
	if args.filelist_in:
		filelist_in = args.filelist_in
	else:
		filelist_in = sys.stdin.fileno()
	
	if args.null_delimiter:
		delimiter = "\0"
	else:
		delimiter = "\n"
	
	if args.tar_out:
		ltar = LimitTar(args.size, name=args.tar_out, mode="w")
	else:
		ltar = LimitTar(args.size, fileobj=sys.stdout.buffer, mode='w|')
	
	files_in = open(filelist_in, "r")
	files_in_reader = _file_iter_lines(files_in, delimiter)
	files_out = _FilelistOutFile(args.filelist_out)
	
	ltar.start()
	remaining = ltar.add_paths(
		(p.rstrip(delimiter) for p in files_in_reader),
		halt_on_underrun=args.no_underrun)
	for path, exception in remaining:
		files_out.write(path + delimiter)
	ltar.stop()
	files_out.close()
	print("Filelist written. Determined size: {}".format(ltar.size),
		file=sys.stderr)
	files_in.close()
	ltar.join()
	if args.tar_out:
		ltar.close()
