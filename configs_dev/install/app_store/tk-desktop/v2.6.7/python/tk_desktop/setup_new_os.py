# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk.platform.qt import QtGui
from sgtk.platform.qt import QtCore


from .ui import setup_new_os


class SetupNewOS(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.ui = setup_new_os.Ui_SetupNewOS()
        self.ui.setupUi(self)
        self.ui.button.clicked.connect(self.launch_docs)
        self._parent = parent

        filter = ResizeEventFilter(self._parent)
        filter.resized.connect(self._on_parent_resized)
        self._parent.installEventFilter(filter)

        self.setVisible(False)

    def launch_docs(self):
        url = "https://developer.shotgridsoftware.com/1b9c259a/?title=Launch+App#Multiple%20Operating%20Systems"
        QtGui.QDesktopServices.openUrl(url)

    def _on_parent_resized(self):
        """
        Special slot hooked up to the event filter.
        When associated widget is resized this slot is being called.
        """
        # resize overlay
        self.resize(self._parent.size())


class ResizeEventFilter(QtCore.QObject):
    """
    Event filter which emits a resized signal whenever
    the monitored widget resizes. This is so that the overlay wrapper
    class can be informed whenever the Widget gets a resize event.
    """

    resized = QtCore.Signal()

    def eventFilter(self, obj, event):
        # peek at the message
        if event.type() == QtCore.QEvent.Resize:
            # re-broadcast any resize events
            self.resized.emit()
        # pass it on!
        return False
