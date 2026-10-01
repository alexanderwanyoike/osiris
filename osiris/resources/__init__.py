"""Configuration, as files.

Everything the installed system reads - a .zshrc, a fastfetch config, a GRUB
theme - lives here as a real file of the format it will finally have, not as a
triple-quoted string inside a Python module. Syntax highlighting works, diffs
are legible, and a typo in a JSON config is a JSON error rather than a silently
malformed line in a heredoc.
"""
