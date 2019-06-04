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
    missing,
    IIndexingEmptyValue,
    empty,
)

_marker = []
LOG = getLogger('Zope.KeywordIndex')

try:
    basestring
except NameError:
    # Python 3 compatibility
    basestring = (bytes, str)


@implementer(IIndexingMissingValue, IIndexingEmptyValue)
class KeywordIndex(UnIndex):
    """Like an UnIndex only it indexes sequences of items.

    Searches match any keyword.

    This should have an _apply_index that returns a relevance score
    """
    meta_type = 'KeywordIndex'
    query_options = ('query', 'range', 'not', 'operator')
    special_values = {TypeError: missing,
                      AttributeError: missing,
                      None: missing,
                      (): empty}

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
        oldKeywords = self._unindex.get(documentId, _marker)

        if oldKeywords is _marker:
            # we've got a new document, let's not futz around.
            if newKeywords in (missing, empty):
                self.insertSpecialIndexEntry(newKeywords, documentId)
            else:
                newKeywords = self.index_objectKeywords(documentId,
                                                        newKeywords)
                # TODO: What do we do if none of the keywords
                # is indexable?
                if not newKeywords:
                    return 0

        else:
            # we have an existing entry for this document, and we need
            # to figure out if any of the keywords have actually changed
            if oldKeywords in (missing, empty):
                self.removeSpecialIndexEntry(oldKeywords, documentId)
                oldSet = OOSet()
            else:
                if not isinstance(oldKeywords, OOSet):
                    oldKeywords = OOSet(oldKeywords)
                oldSet = oldKeywords

            if newKeywords in (missing, empty):
                self.insertSpecialIndexEntry(newKeywords, documentId)
                newSet = OOSet()
            else:
                newSet = newKeywords = OOSet(newKeywords)

            fdiff = difference(oldSet, newSet)
            rdiff = difference(newSet, oldSet)
            if fdiff or rdiff:
                # if we've got forward or reverse changes
                if fdiff:
                    self.unindex_objectKeywords(documentId, fdiff)
                if rdiff:
                    newKeywords = self.index_objectKeywords(documentId,
                                                            rdiff)
                    # TODO: What do we do if none of the keywords
                    # is indexable?
                    if not newKeywords:
                        return 0

        self._unindex[documentId] = newKeywords

        return 1

    def _get_object_keywords(self, obj, attr):
        newKeywords = getattr(obj, attr, None)

        def _getSpecialValueFor(datum):
            try:
                special_value = self.special_values[datum]
            except TypeError:
                raise KeyError(datum)

            if self.providesSpecialIndex(special_value):
                return special_value
            raise KeyError(datum)

        if safe_callable(newKeywords):
            try:
                newKeywords = newKeywords()
            except (AttributeError, TypeError):
                LOG.debug('%(context)s: Cannot determine datum for attribute '
                          '%(attr)s of object %(obj)r', dict(
                              context=self.__class__.__name__,
                              attr=attr,
                              obj=obj),
                          exc_info=True)

                newKeywords = sys.exc_info()[0]
                try:
                    return _getSpecialValueFor(newKeywords)
                except KeyError:
                    return _marker

        try:
            return _getSpecialValueFor(newKeywords)
        except KeyError:
            pass

        # normalize datum
        if isinstance(newKeywords, basestring):
            newKeywords = (newKeywords,)
        else:
            try:
                # unique
                newKeywords = set(newKeywords)
            except TypeError:
                # Not a sequence
                newKeywords = (newKeywords,)
            else:
                newKeywords = tuple(newKeywords)

        try:
            return _getSpecialValueFor(newKeywords)
        except KeyError:
            return newKeywords

    def index_objectKeywords(self, documentId, keywords):
        """ carefully index the object with integer id 'documentId'"""

        indexed_keys = OOSet()
        for kw in keywords:
            try:
                self.insertForwardIndexEntry(kw, documentId)
                indexed_keys.insert(kw)
            except TypeError:
                # key is not valid for this Btree so we have to
                # log and ignore keyword not indexable
                LOG.error('%(context)s: Unable to insert forward '
                          'index entry for document with id '
                          '%(doc_id)s and keyword %(kw)r '
                          'for index %{index}r.', dict(
                              context=self.__class__.__name__,
                              kw=kw,
                              doc_id=documentId,
                              index=self.id))
        return indexed_keys

    def unindex_objectKeywords(self, documentId, keywords):
        """ carefully unindex the object with integer id 'documentId'"""

        if keywords is not None:
            for kw in keywords:
                self.removeForwardIndexEntry(kw, documentId)

    def unindex_object(self, documentId):
        """ carefully unindex the object with integer id 'documentId'"""

        keywords = self._unindex.get(documentId, _marker)

        if keywords is _marker:
            return

        self._increment_counter()

        if keywords in (missing, empty):
            try:
                if not self.removeSpecialIndexEntry(keywords, documentId):
                    raise KeyError
                del self._unindex[documentId]

            except KeyError:
                LOG.debug('%(context)s: Attempt to unindex nonexistent '
                          'document with id %(doc_id)s', dict(
                              context=self.__class__.__name__,
                              doc_id=documentId),
                          exc_info=True)

            return None

        self.unindex_objectKeywords(documentId, keywords)
        try:
            del self._unindex[documentId]
        except KeyError:
            LOG.debug('%(context)s: Attempt to unindex nonexistent '
                      'document with id %(doc_id)s', dict(
                          context=self.__class__.__name__,
                          doc_id=documentId),
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
