=========
ego.conf
=========

---------------------------------------------
Ego global configuration file
---------------------------------------------

:Author: Daniel Robbins <drobbins@funtoo.org>
:Version: ##VERSION##
:Manual section: 5
:Manual group: Funtoo Linux Core System

SYNOPSIS
--------

  */etc/ego.conf*

DESCRIPTION
-----------

The data in */etc/ego.conf* is used by *ego(8)* for configuration of kits and other settings relevant to ego commands.
The configuration file format is similar to Microsoft Windows .INI files and is parsed by the Python ConfigParser
module.

Sections are delimited with the literal format ``[SECTIONNAME]``. Currently, the following sections are supported:
*global*, *kits*. Values in each section are defined using the format ``KEY = VALUE``, one per line.

Global Section
==============

The *global* section supports the following configuration variables: *install_path*, *kits_path*, *meta_repo_path*,
*sync_user*.

**install_path**

For developers, this allows one to specify an alternate location where ego is installed. This defaults to
``/usr/share/ego``.

**kits_path**

Use this setting to specify the path to the kits directory used by meta-repo. When set to a relative path, this path
will be relative to *meta_repo_path*, but it can also be set to an absolute path, in which case it will be interpreted
as-is. The default settings for *kits_path* is "kits".

**kits_depth**

This setting specifies the default depth to use when cloning a kit. The default is 2, which is the minimum functioning
default when using Funtoo kits directly. If using a time-delayed version of meta-repo, this can be set to a custom
value or set to 0, which will cause the kits to be cloned with complete history.

Note that in ego 2.4.0 and greater, when git-depth data is detected in meta-repo, this depth data will be used instead,
and this setting has no effect unless set to 0, which will enable full history.

**meta_repo_path**

This setting defines the directory that will house meta-repo once cloned, and also where ego and Portage will look for
meta-repo. The default value for *meta_repo_path* is ``/var/git/meta-repo``.

**repos_conf_path**

This setting specifies the directory which will be used to store generated repos.conf entries. By default, ego will
generate repos.conf configuration files (and ensure they are updated) after an ``ego sync`` operation. To differentiate
ego-generated repos.conf configuration files from user-provided files, all ego-generated files will have the prefix
``ego-``. Also note that ego will take care of cleaning up (deleting) any ``ego-`` prefixed repos.conf entries that
no longer exist in meta-repo.

**sync_user**

This setting was deprecated as of ego 2.8.0 and is no longer used.
This setting defined the user and group that are used to perform the sync operation, and thus the user and group which
will end up owning the meta-repo files. Now, the sync process can run as root or a regular user. When running as root,
ego sync will read the group and user ownership of meta-repo and use this user and group to perform sync operations.

**sync_base_url**

This setting defines the base URL to use for cloning of kits as well as meta-repo. Default value is
``https://github.com/funtoo/{repo}``. The ``{repo}`` value is replaced with the name of the kit or with the literal
value ``meta-repo``. Note that this setting only takes effect upon first clone, and if changed, you should remove
eta-repo and kits and perform an initial ``ego sync`` to reinitialize the repositories. Also note that this
setting can be overridden by using the ``EGO_SYNC_BASE_URL`` environment variable, which will take precedence over
the configuration file setting/default if found.

Kits Section
============

The *kits* section is used to specify non-default branches to use for Funtoo Linux kits. By default, ``ego`` will use
the *default* kit defined by Funtoo Linux BDFL. This information is stored in the ``metadata/kit-info.json`` in the
meta-repo directory. Users who would prefer to use alternate branches can override these selections as follows::

  [kits]

  xorg-kit = 1.19-prime
  python-kit = 3.6-prime

After changing default kit values, be sure to run ``ego sync`` to update meta-repo to point to the correct kits. Also
be sure to run ``epro update`` to regenerate your profile information (in some cases, this can be done manually by
``ego sync``).

To *omit* a kit from your meta-repo, you can set the branch to ``skip``. On next sync, this kit will not by synced
nor will it be configured in your ``/etc/portage/repos.conf`` or ``/etc/portage/make.profile/parent``.

Omitting Kits
~~~~~~~~~~~~~

If you want to instruct ``ego sync`` to avoid syncing and enabling a particular kit, you can use the skip option,
which is used as follows::

  [kits]

  xorg-kit = skip

It will then not be synced/updated over the network, and your ``/etc/portage`` kits configuration will be set up
to not include this kit, even if it happens to exist in ``/var/git/meta-repo/kits`` due to previously being
enabled.

