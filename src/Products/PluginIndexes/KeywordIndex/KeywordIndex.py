##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import sys
from logging import getLogger

from BTrees.OOBTree import difference
from BTrees.OOBTree import OOSet
from App.special_dtml import DTMLFile
from zope.interface import implementer

from Products.PluginIndexes.unindex import UnIndex
from Products.PluginIndexes.util import safe_callable
from Products.PluginIndexes.interfaces import (
    IIndexingMissingValue,
)

_marker = []
LOG = getLogger('Zope.KeywordIndex')

try:
    basestring
except NameError:
    # Python 3 compatibility
    basestring = (bytes, str)


@implementer(IIndexingMissingValue)
class KeywordIndex(UnIndex):
    """Like an UnIndex only it indexes sequences of items.

    Searches match any keyword.

    This should have an _apply_index that returns a relevance score
    """
    meta_type = "KeywordIndex"
    query_options = ('query', 'range', 'not', 'operator')

    manage_options = (
        {'label': 'Settings', 'action': 'manage_main'},
        {'label': 'Browse', 'action': 'manage_browse'},
    )

    def _index_object(self, documentId, obj, threshold=None, attr=''):
        """ index an object 'obj' with integer id 'i'

        Ideally, we've been passed a sequence of some sort that we
        can iterate over. If however, we haven't, we should do something
        useful with the results. In the case of a string, this means
        indexing the entire string as a keyword."""

        # First we need to see if there's anything interesting to look at
        # self.id is the name of the index, which is also the name of the
        # attribute we're interested in.  If the attribute is callable,
        # we'll do so.

        newKeywords = self._get_object_keywords(obj, attr)
        if newKeywords is None:
            return self._not_indexed.insert(documentId)

        oldKeywords = self._unindex.get(documentId, None)

        if oldKeywords is None:
            # we've got a new document, let's not futz around.
            try:
                for kw in newKeywords:
                    self.insertForwardIndexEntry(kw, documentId)
                self._unindex[documentId] = list(newKeywords)
            except TypeError:
                return 0
        else:
            # we have an existing entry for this document, and we need
            # to figure out if any of the keywords have actually changed
            if type(oldKeywords) is not OOSet:
                oldKeywords = OOSet(oldKeywords)
            newKeywords = OOSet(newKeywords)
            fdiff = difference(oldKeywords, newKeywords)
            rdiff = difference(newKeywords, oldKeywords)
            if fdiff or rdiff:
                # if we've got forward or reverse changes
                self._unindex[documentId] = list(newKeywords)
                if fdiff:
                    self.unindex_objectKeywords(documentId, fdiff)
                if rdiff:
                    for kw in rdiff:
                        self.insertForwardIndexEntry(kw, documentId)
        return 1

    def _get_object_keywords(self, obj, attr):
        newKeywords = getattr(obj, attr, None)
        if safe_callable(newKeywords):
            try:
                newKeywords = newKeywords()
            except (AttributeError, TypeError):
                return None
        if newKeywords is None:
            return None
        if not newKeywords:
            return ()
        elif isinstance(newKeywords, basestring):
            return (newKeywords,)
        else:
            try:
                # unique
                newKeywords = set(newKeywords)
            except TypeError:
                # Not a sequence
                return (newKeywords,)
            else:
                return tuple(newKeywords)

    def unindex_objectKeywords(self, documentId, keywords):
        """ carefully unindex the object with integer id 'documentId'"""

        if keywords is not None:
            for kw in keywords:
                self.removeForwardIndexEntry(kw, documentId)

    def unindex_object(self, documentId):
        """ carefully unindex the object with integer id 'documentId'"""

        keywords = self._unindex.get(documentId, _marker)

        if keywords is _marker:
            try:
                self._not_indexed.remove(documentId)
                self._increment_counter()
            except KeyError:
                LOG.debug('%s: Attempt to unindex nonexistent '
                          'document with id %s' %
                          (self.__class__.__name__, documentId),
                          exc_info=True)
            return None

        self._increment_counter()

        if keywords is None:
            self._not_indexed.remove(documentId)
            return

        self.unindex_objectKeywords(documentId, keywords)

        try:
            del self._unindex[documentId]
        except KeyError:
            LOG.debug('%s: Attempt to unindex nonexistent '
                      'document with id %s' %
                      (self.__class__.__name__, documentId),
                      exc_info=True)

    manage = manage_main = DTMLFile('dtml/manageKeywordIndex', globals())
    manage_main._setName('manage_main')
    manage_browse = DTMLFile('../dtml/browseIndex', globals())


manage_addKeywordIndexForm = DTMLFile('dtml/addKeywordIndex', globals())


def manage_addKeywordIndex(self, id, extra=None,
                           REQUEST=None, RESPONSE=None, URL3=None):
    """Add a keyword index"""
    return self.manage_addIndex(id, 'KeywordIndex', extra=extra,
                                REQUEST=REQUEST, RESPONSE=RESPONSE, URL1=URL3)
