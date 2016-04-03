import sys
import os

import win32file
import win32con

from enum import IntEnum

#
# Part of Project 1. See csvMonitor.py for details.
#
# This class watches a Windows folder and reports any write actions on files within.
# Adapted from http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html

class FolderWatchDog:
	
	class ACTIONS(IntEnum):
		CREATED = 1
		DELETED = 2
		UPDATED = 3
		RENAME_FROM = 4
		RENAME_TO = 5
		
	FILE_LIST_DIRECTORY = 0x0001
	CHANGE_ACTION_BUFFER_SIZE = 1024 * 1024
	
	def open(self, targetFolder):
		self.targetFolder = targetFolder
	
		self.hDir = win32file.CreateFile (
			self.targetFolder,
			self.FILE_LIST_DIRECTORY,
			win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
			None,
			win32con.OPEN_EXISTING,
			win32con.FILE_FLAG_BACKUP_SEMANTICS,
			None
		)
	
	def getFolderWriteActions(self):
	
		results = win32file.ReadDirectoryChangesW (
			self.hDir,									# File handle for the directory
			self.CHANGE_ACTION_BUFFER_SIZE,				# Results buffer size
			False,										# Just monitor this folder, not subfolders
			win32con.FILE_NOTIFY_CHANGE_FILE_NAME |     # Notify on these conditions (although many are ignored by Windows anyway apparently!)
			win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
			win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
			win32con.FILE_NOTIFY_CHANGE_SIZE |
			win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
			win32con.FILE_NOTIFY_CHANGE_SECURITY,
			None										# Not using overlapped objects
		)
		
		return(results)

	def close(self):
		win32file.CloseHandle(self.hDir)
		