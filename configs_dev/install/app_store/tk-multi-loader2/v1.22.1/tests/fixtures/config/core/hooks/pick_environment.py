# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

"""
Hook which chooses an environment file to use based on the current context.
This file is almost always overridden by a standard config.
"""

import os
from sgtk import Hook


class PickEnvironment(Hook):
    def execute(self, context, **kwargs):
        """ """
        return os.environ.get("LOADER2_API_TEST", "api_test")
