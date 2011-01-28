##############################################################################
#
# Copyright (c) 2011 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from App.special_dtml import DTMLFile
from BTrees.IOBTree import IOBTree
from BTrees.Length import Length
from BTrees.OIBTree import OIBTree

from Products.PluginIndexes.common.UnIndex import UnIndex

_marker = []


class UUIDIndex(UnIndex):
    """Index for uuid fields with an unique value per key.

    The internal structure is:

    self._index = {datum:documentId]}
    self._unindex = {documentId:datum}

    For each datum only one documentId can exist.
    """

    meta_type= " UUIDIndex"

    manage_options= (
        {'label': 'Settings', 'action': 'manage_main'},
        {'label': 'Browse', 'action': 'manage_browse'},
    )

    query_options = ["query", "range"]

    manage = manage_main = DTMLFile('dtml/manageUUIDIndex', globals())
    manage_main._setName('manage_main')
    manage_browse = DTMLFile('../dtml/browseIndex', globals())

    def clear(self):
        self._length = Length()
        self._index = OIBTree()
        self._unindex = IOBTree()

    def numObjects(self):
        """Return the number of indexed objects. Since we have a 1:1 mapping
        from documents to values, we can reuse the stored length.
        """
        return self.indexSize()

    def insertForwardIndexEntry(self, entry, documentId):
        """Take the entry provided and put it in the correct place
        in the forward index.
        """
        if entry is None:
            return

        old_docid = self._index.get(entry, _marker)
        if old_docid is _marker:
            self._index[entry] = documentId
            self._length.change(1)
        elif old_docid != documentId:
            raise ValueError("A different document with value '%s' already "
                "exists in the index.'")

    def removeForwardIndexEntry(self, entry, documentId):
        """Take the entry provided and remove any reference to documentId
        in its entry in the index.
        """
        old_docid = self._index.get(entry, _marker)
        if old_docid is not _marker:
            del self._index[entry]
            self._length.change(-1)

manage_addUUIDIndexForm = DTMLFile('dtml/addUUIDIndex', globals())


def manage_addUUIDIndex(self, id, extra=None,
                REQUEST=None, RESPONSE=None, URL3=None):
    """Add an uuid index"""
    return self.manage_addIndex(id, 'UUIDIndex', extra=extra, \
             REQUEST=REQUEST, RESPONSE=RESPONSE, URL1=URL3)