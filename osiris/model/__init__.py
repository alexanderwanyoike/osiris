"""The domain, with no idea that an operating system exists.

Nothing in here imports `os`, `subprocess`, or any other part of Osiris above
`platform`. That is enforced by .importlinter, not by good intentions: a model
that can reach the filesystem stops being testable the moment somebody is in a
hurry.
"""
