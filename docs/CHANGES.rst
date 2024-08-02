Changelog
=========

0.7.0 - 2024-08-02
------------------

- Provide subclasses of existing commmands that allow credentials be
  provided for accessing private workspaces.

0.6.0 - 2023-10-17
------------------

- Ensure that Dulwich methods return values match closer with the
  cli command class counterpart.
- Cleaned up support code in testing to ensure the defaults are not
  interfered with.

0.5.0 - 2023-10-06
------------------

- Dulwich is now registered first.
- Have the registration by name show all available implementations.

0.4.0 - 2023-06-16
------------------

- Updated Dulwich support to use official release.
- Ensure that the workspace workflows will return the error code for the
  external tools and not just assume stderr output are errors.

0.3 - 2016-09-08
----------------

- Support the use of a custom fork of Dulwich for Git access.

0.2 - 2014-07-14
----------------

- Renaming to the standard top-level namespace for this group of
  packages.

0.1 - 2013-12-18
----------------

- Initial release.
- Core support for basic incremental workflow management using both git
  and mercurial.
