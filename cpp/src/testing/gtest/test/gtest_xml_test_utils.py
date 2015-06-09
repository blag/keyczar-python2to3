#!/usr/bin/env python
#
# Copyright 2006, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Unit test utilities for gtest_xml_output"""

__author__ = 'eefacm@gmail.com (Sean Mcafee)'

import re
import unittest

from xml.dom import minidom, Node

GTEST_OUTPUT_FLAG = "--gtest_output"
GTEST_DEFAULT_OUTPUT_FILE = "test_detail.xml"


class GTestXMLTestCase(unittest.TestCase):

    """
  Base class for tests of Google Test's XML output functionality.
  """

    def AssertEquivalentNodes(self, expected_node, actual_node):
        """
    Asserts that actual_node (a DOM node object) is equivalent to
    expected_node (another DOM node object), in that either both of
    them are CDATA nodes and have the same value, or both are DOM
    elements and actual_node meets all of the following conditions:

    *  It has the same tag name as expected_node.
    *  It has the same set of attributes as expected_node, each with
       the same value as the corresponding attribute of expected_node.
       An exception is any attribute named "time", which needs only be
       convertible to a floating-point number.
    *  It has an equivalent set of child nodes (including elements and
       CDATA sections) as expected_node.  Note that we ignore the
       order of the children as they are not guaranteed to be in any
       particular order.
    """

        if expected_node.nodeType == Node.CDATA_SECTION_NODE:
            self.assertEquals(Node.CDATA_SECTION_NODE, actual_node.nodeType)
            self.assertEquals(expected_node.nodeValue, actual_node.nodeValue)
            return

        self.assertEquals(Node.ELEMENT_NODE, actual_node.nodeType)
        self.assertEquals(Node.ELEMENT_NODE, expected_node.nodeType)
        self.assertEquals(expected_node.tagName, actual_node.tagName)

        expected_attributes = expected_node.attributes
        actual_attributes = actual_node.attributes
        self.assertEquals(expected_attributes.length, actual_attributes.length)
        for i in range(expected_attributes.length):
            expected_attr = expected_attributes.item(i)
            actual_attr = actual_attributes.get(expected_attr.name)
            self.assert_(actual_attr is not None)
            self.assertEquals(expected_attr.value, actual_attr.value)

        expected_children = self._GetChildren(expected_node)
        actual_children = self._GetChildren(actual_node)
        self.assertEquals(len(expected_children), len(actual_children))
        for child_id, child in expected_children.iteritems():
            self.assert_(child_id in actual_children,
                         '<%s> is not in <%s>' % (child_id, actual_children))
            self.AssertEquivalentNodes(child, actual_children[child_id])

    identifying_attribute = {
        "testsuite": "name",
        "testcase": "name",
        "failure": "message",
    }

    def _GetChildren(self, element):
        """
    Fetches all of the child nodes of element, a DOM Element object.
    Returns them as the values of a dictionary keyed by the IDs of the
    children.  For <testsuite> and <testcase> elements, the ID is the
    value of their "name" attribute; for <failure> elements, it is the
    value of the "message" attribute; for CDATA section node, it is
    "detail".  An exception is raised if any element other than the
    above four is encountered, if two child elements with the same
    identifying attributes are encountered, or if any other type of
    node is encountered, other than Text nodes containing only
    whitespace.
    """

        children = {}
        for child in element.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                self.assert_(child.tagName in self.identifying_attribute,
                             "Encountered unknown element <%s>" %
                             child.tagName)
                childID = child.getAttribute(
                    self.identifying_attribute[child.tagName])
                self.assert_(childID not in children)
                children[childID] = child
            elif child.nodeType == Node.TEXT_NODE:
                self.assert_(child.nodeValue.isspace())
            elif child.nodeType == Node.CDATA_SECTION_NODE:
                self.assert_("detail" not in children)
                children["detail"] = child
            else:
                self.fail("Encountered unexpected node type %d" %
                          child.nodeType)
        return children

    def NormalizeXml(self, element):
        """
    Normalizes Google Test's XML output to eliminate references to transient
    information that may change from run to run.

    *  The "time" attribute of <testsuite> and <testcase> elements is
       replaced with a single asterisk, if it contains only digit
       characters.
    *  The line number reported in the first line of the "message"
       attribute of <failure> elements is replaced with a single asterisk.
    *  The directory names in file paths are removed.
    *  The stack traces are removed.
    """

        if element.tagName in ("testsuite", "testcase"):
            time = element.getAttributeNode("time")
            time.value = re.sub(r"^\d+(\.\d+)?$", "*", time.value)
        elif element.tagName == "failure":
            for child in element.childNodes:
                if child.nodeType == Node.CDATA_SECTION_NODE:
                    # Removes the source line number.
                    cdata = re.sub(r"^.*/(.*:)\d+\n", "\\1*\n",
                                   child.nodeValue)
                    # Removes the actual stack trace.
                    child.nodeValue = re.sub(r"\nStack trace:\n(.|\n)*", "",
                                             cdata)
        for child in element.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                self.NormalizeXml(child)
