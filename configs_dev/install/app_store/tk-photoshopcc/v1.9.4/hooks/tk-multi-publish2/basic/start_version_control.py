# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopStartVersionControlPlugin(HookBaseClass):
    """
    Simple plugin to insert a version number into the photoshop document path if
    one does not exist.
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(self.disk_location, os.pardir, "icons", "version_up.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Begin file versioning"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        Adds a version number to the filename.<br><br>

        Once a version number exists in the file, the publishing will
        automatically bump the version number. For example,
        <code>filename.ext</code> will be saved to
        <code>filename.v001.ext</code>.<br><br>

        If the session has not been saved, validation will fail and a button
        will be provided in the logging output to save the file.<br><br>

        If a file already exists on disk with a version number, validation will
        fail and the logging output will include button to save the file to a
        different name.<br><br>
        """

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["photoshop.document"]

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        return {}

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        document = item.properties.get("document")
        if not document:
            self.logger.warn("Could not determine the document for item")
            return {"accepted": False}

        path = _document_path(document)

        if path:
            version_number = self._get_version_number(path, item)
            if version_number is not None:
                self.logger.info(
                    "Photoshop '%s' plugin rejected document: %s..."
                    % (self.name, document.name)
                )
                self.logger.info("  There is already a version number in the file...")
                self.logger.info("  Document file path: %s" % (path,))
                return {"accepted": False}
        else:
            # the session has not been saved before (no path determined).
            # provide a save button. the session will need to be saved before
            # validation will succeed.
            self.logger.warn(
                "Photoshop document'%s' has not been saved." % (document.name),
                extra=_get_save_as_action(document),
            )

        self.logger.info(
            "Photoshop '%s' plugin accepted the document %s."
            % (self.name, document.name),
            extra=_get_version_docs_action(),
        )

        # accept the plugin, but don't force the user to add a version number
        # (leave it unchecked)
        return {"accepted": True, "checked": False}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent
        document = item.properties["document"]
        path = _document_path(document)

        if not path:
            # the session still requires saving. provide a save button.
            # validation fails
            error_msg = "The Photoshop document '%s' has not been saved." % (
                document.name,
            )
            self.logger.error(error_msg, extra=_get_save_as_action(document))
            raise Exception(error_msg)

        # NOTE: If the plugin is attached to an item, that means no version
        # number could be found in the path. If that's the case, the work file
        # template won't be much use here as it likely has a version number
        # field defined within it. Simply use the path info hook to inject a
        # version number into the current file path

        # get the path to a versioned copy of the file.
        version_path = publisher.util.get_version_path(path, "v001")
        if os.path.exists(version_path):
            error_msg = (
                "A file already exists with a version number. Please "
                "choose another name."
            )
            self.logger.error(error_msg, extra=_get_save_as_action(document))
            raise Exception(error_msg)

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent
        engine = publisher.engine
        document = item.properties["document"]
        path = _document_path(document)

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        # ensure the session is saved in its current state
        engine.save(document)

        # get the path to a versioned copy of the file.
        version_path = publisher.util.get_version_path(path, "v001")

        with engine.context_changes_disabled():

            # remember the active document so that we can restore it.
            previous_active_document = engine.adobe.get_active_document()

            # make the document being processed the active document
            engine.adobe.app.activeDocument = document

            # save to the new version path
            engine.save_to_path(document, version_path)
            self.logger.info(
                "A version number has been added to the Photoshop document..."
            )
            self.logger.info("  Photoshop document path: %s" % (version_path,))

            # restore the active document
            engine.adobe.app.activeDocument = previous_active_document

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass

    def _get_version_number(self, path, item):
        """
        Try to extract and return a version number for the supplied path.

        :param path: The path to the current session

        :return: The version number as an `int` if it can be determined, else
            None.

        NOTE: This method will use the work template provided by the
        session collector, if configured, to determine the version number. If
        not configured, the version number will be extracted using the zero
        config path_info hook.
        """

        publisher = self.parent
        version_number = None

        work_template = item.properties.get("work_template")
        if work_template:
            if work_template.validate(path):
                self.logger.debug("Using work template to determine version number.")
                work_fields = work_template.get_fields(path)
                if "version" in work_fields:
                    version_number = work_fields.get("version")
            else:
                self.logger.debug("Work template did not match path")
        else:
            self.logger.debug("Work template unavailable for version extraction.")

        if version_number is None:
            self.logger.debug("Using path info hook to determine version number.")
            version_number = publisher.util.get_version_number(path)

        return version_number


def _get_save_as_action(document):
    """
    Simple helper for returning a log action dict for saving the document
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = lambda: engine.save_as(document)

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current document",
            "callback": callback,
        }
    }


def _get_version_docs_action():
    """
    Simple helper for returning a log action to show version docs
    """
    return {
        "action_open_url": {
            "label": "Version Docs",
            "tooltip": "Show docs for version formats",
            "url": "https://help.autodesk.com/view/SGSUB/ENU/?guid=SG_Supervisor_Artist_sa_integrations_sa_integrations_user_guide_html",
        }
    }


def _document_path(document):
    """
    Returns the path on disk to the supplied document. May be ``None`` if the
    document has not been saved.
    """

    try:
        path = document.fullName.fsName
    except Exception:
        path = None

    return path
