"""Verify completed remote builds before handing them to publication.

``publish_completed_build`` checks artifact and SQL lineage;
``pipeline`` checks the export against registration and constructs the request.
These modules are synchronous helpers, not a scheduler.
"""
