===================
Trigger Development
===================

The Trigger developement team is currently a one-man operation lead by `Jathan McCollum
<http://about.me/jathanism>`_, aka ``jathanism``.

Contributing
============

There are several ways to get involved with Trigger:

* **Use Trigger and send us feedback!** This is the best and easiest to improve
  the project -- let us know how you currently use Trigger and how you want to
  use it. (Please search the `ticket tracker
  <https://github.com/aol/trigger/issues>`_ first, though, when submitting
  feature ideas.)
* **Report bugs.** If you use Trigger and think you've found a bug, check on
  the `ticket tracker <https://github.com/aol/trigger/issues>`_ to see if
  anyone's reported it yet, and if not -- file a bug! If you can, please try to
  make sure you can replicate the problem, and provide us with the info we need
  to reproduce it ourselves (what version of Trigger you're using, what
  platform you're on, and what exactly you were doing when the bug cropped up.)
* **Submit patches or new features.** Make a `Github <https://github.com>`_
  account, `create a fork <http://help.github.com/fork-a-repo/>`_ of `the main
  Trigger repository <https://github.com/aol/trigger>`_, and `submit a pull
  request <http://help.github.com/send-pull-requests/>`_.

All contributors will receive proper attribution for their work. We want to give credit where it is due!

Communication
-------------

If an issue ticket exists for a given issue, **please** keep all communication
in that ticket's comments. Otherwise, please use whatever avenue of
communication works best for you!

Style
-----

Trigger tries very diligently to honor `PEP-8`_, especially (but not limited
to!) the following:

* Keep all lines under 80 characters. This goes for the ReST documentation as
  well as code itself.

  * Exceptions are made for situations where breaking a long string (such as a
    string being ``print``-ed from source code, or an especially long URL link
    in documentation) would be kind of a pain.

* Typical Python 4-space (soft-tab) indents. No tabs! No 8 space indents! (No
  2- or 3-space indents, for that matter!)
* ``CamelCase`` class names, but ``lowercase_underscore_separated`` everything
  else.

.. _PEP-8: http://www.python.org/dev/peps/pep-0008/

Branching/Repository Layout
===========================

While Trigger's development methodology isn't set in stone yet, the following
items detail how we currently organize the Git repository and expect to perform
merges and so forth. This will be chiefly of interest to those who wish to
follow a specific Git branch instead of released versions, or to any
contributors.

* Completed feature work is merged into the ``master`` branch, and once enough
  new features are done, a new release branch is created and optionally used to
  create prerelease versions for testing -- or simply released as-is.
* While we try our best not to commit broken code or change APIs without
  warning, as with many other open-source projects we can only have a guarantee
  of stability in the release branches. Only follow ``master`` (or, even worse,
  feature branches!) if you're willing to deal with a little pain.
* Bugfixes are to be performed on release branches and then merged into
  ``master`` so that ``master`` is always up-to-date (or nearly so; while it's
  not mandatory to merge after every bugfix, doing so at least daily is a good
  idea.)

Releases
========

We use `semantic versioning <http://semver.org>`_. Version numbers should follow this format:: 

    {Major version}.{Minor version}.{Revision number}.{Build number (optional)}

Major
-----

Major releases update the first number, e.g. going from 0.9 to 1.0, and
indicate that the software has reached some very large milestone.

For example, the 1.0 release signified a commitment to a medium to long term
API and some significant backwards incompatible (compared to the 0.9 series)
features. Version 2.0 might indicate a rewrite using a new underlying network
technology or an overhaul to be more object-oriented.

Major releases will often be backwards-incompatible with the previous line of
development, though this is not a requirement, just a usual happenstance.
Users should expect to have to make at least some changes to their fabfiles
when switching between major versions.

Minor
-----

Minor releases, such as moving from 1.0 to 1.1, typically mean that one or more
new, large features has been added. They are also sometimes used to mark off
the fact that a lot of bug fixes or small feature modifications have occurred
since the previous minor release. (And, naturally, some of them will involve
both at the same time.)

These releases are guaranteed to be backwards-compatible with all other
releases containing the same major version number, so a fabfile that works
with 1.0 should also work fine with 1.1 or even 1.9.

Bugfix/tertiary
---------------

The third and final part of version numbers, such as the '3' in 1.0.3,
generally indicate a release containing one or more bugfixes, although minor
feature modifications may (rarely) occur.

This third number is sometimes omitted for the first major or minor release in
a series, e.g. 1.2 or 2.0, and in these cases it can be considered an implicit
zero (e.g. 2.0.0).
