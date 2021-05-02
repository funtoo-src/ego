#!/usr/bin/python3

import os
import sys
from ego.module import EgoModule
from ego.output import Output, mesg

import funtoo.boot.helper
import funtoo.boot.extensions

from funtoo.boot.config import BootConfigFile
from funtoo.core.config import ConfigFileError
from funtoo.boot.extension import ExtensionError, BootLoaderMenu


class Module(EgoModule):
	@property
	def boot_config_file(self):
		outpath = os.path.join(self.config.root_path, "etc/boot.conf")
		if self.config.root_path != "/":
			Output.warning("Using boot configuration file %s." % outpath)
		return outpath

	def get_boot_config(self):
		cfgfile = self.boot_config_file
		try:
			config = BootConfigFile(cfgfile)
			if not config.fileExists():
				Output.error("Master configuration file %s does not exist." % cfgfile)
			return config
		except ConfigFileError as e:
			Output.fatal("Error reading %s: %s." % (cfgfile, str(e)))

	def setup(self):

		self.boot_config = self.get_boot_config()

		self._ext = None
		self.ext_name = None
		self.ext_module = None

	def cleanup(self, success, quiet=False):
		""" prints accumulated errors and warnings and exits appropriately """
		print()
		if self._ext is not None:
			# unmounts any non-/boot filesystems we may have mounted for scanning.
			# /boot unmounting is handled via another process.
			if self.config.root_path == "/":
				self._ext.resolver.unmount_if_necessary()
		warnings = False
		for msgtype, msg in self.msgs:
			if msgtype == "warn":
				warnings = True
			if not quiet:
				mesg(msgtype, msg)
		if not success or "error" in map(lambda x: x[0], self.msgs):
			mesg("fatal", "Did not complete successfully.")
			print()
			sys.exit(1)
		else:
			outstr = "Completed successfully"
			if warnings:
				outstr += " with warnings."
			else:
				outstr += "."
			mesg("norm", outstr)
			print()
			sys.exit(0)

	def update(self, boot_menu: BootLoaderMenu, check=False, quiet=False, cleanup=True, boot_options=None):
		"""
		Perform traditional boot-update action of updating boot-loader configuration based on /etc/boot.conf.
		:return:
		"""

		if boot_options is None:
			boot_options = {}

		for invalid in self.boot_config.validate():
			self.msgs.append(["warn", 'invalid config setting "{iv}"; ignored.'.format(iv=invalid)])

		if check is True:
			self.msgs.append(["norm", "Configuration file {cf} checked.".format(cf=self.boot_config_file)])
			self.cleanup(True)

		if os.geteuid() != 0:
			Output.fatal("Updating boot configuration requires root privileges.")

		extension = self.get_extension(boot_options)
		mesg("norm", "Generating config for {gen}...".format(gen=self.ext_name))
		print()

		# Before loading extension, we want to auto-mount boot if it isn't
		# already mounted:

		imountedit = False
		fstabinfo = None

		if self.config.root_path == "/":
			fstabinfo = funtoo.boot.helper.fstabInfo("/")

			if fstabinfo.hasEntry("/boot"):
				if not os.path.ismount("/boot"):
					mesg("debug", "Mounting filesystem /boot...")
					os.system("mount /boot")
					imountedit = True
			else:
				mesg("info", "No /etc/fstab entry for /boot; not mounting.")

		# regenerate config:
		try:
			success = extension.regenerate(boot_menu)
			if success and boot_menu.success and not quiet:
				boot_menu.show()

			# If we mounted /boot, we should unmount it:
			if imountedit:
				mesg("debug", "Unmounting /boot")
				os.system("umount /boot")

			if cleanup:
				self.cleanup(boot_menu.success)
			return boot_menu
		except ExtensionError as e:
			self.msgs.append(["fatal", e])
			if cleanup:
				self.cleanup(False)
				return None

	def get_extension(self, boot_options):
		if self._ext is None:
			success = True
			self.ext_name = self.boot_config["boot/generate"]
			if self.ext_name == "":
				success = False
				self.msgs.append(["fatal", "boot/generate does not specify a valid boot loader to generate a config for."])
			if self.ext_name not in funtoo.boot.extensions.__all__:
				success = False
				self.msgs.append(
					["fatal", 'extension for boot loader "%s" (specified in boot/generate) not found.' % self.ext_name]
				)
			if not success:
				self.cleanup(False)
			# Dynamically import the proper extension module (ie. grub.py,
			# grub-legacy.py, lilo.py):
			extname = "funtoo.boot.extensions.{gen}".format(gen=self.ext_name)
			__import__(extname)
			self.ext_module = sys.modules[extname]
			self._ext = self.ext_module.getExtension(self.boot_config, self.config, boot_options, self)
		return self._ext

	def handle_show_action(self):
		"""Perform boot-update --show action -- show a specific boot.conf configuration setting."""
		print(self.boot_config[self.options.show])

	def handle_show_defaults_action(self):
		"""Perform boot-update --show-defaults action."""
		print("# These are the default settings that can be overridden by")
		print("# the /etc/boot.conf file.")
		print("")
		for line in self.boot_config.parent.dump():
			if not line.startswith("#"):
				sys.stdout.write(line)

	def microcode_action(self):
		from funtoo.boot.resolver import Resolver

		resolver = Resolver(self.boot_config, self.config, self.boot_options, self)
		success = resolver.microcode_regenerate()
		self.cleanup(success=success)

	def set_default_action(self):
		"""Perform the boot-update --set-default action to set a default kernel."""
		if os.geteuid() != 0:
			Output.fatal("Updating the default kernel requires root privileges.")
		# Record default selection in /etc/boot.d...
		found = self.boot_config.idmapper.set_default_kname(sys.argv[2])
		if found:
			# That was successful. Now regenerate our config...
			boot_menu = self.update_action(quiet=True)
			ext = self.get_extension()
			if hasattr(ext, "_set_default"):
				# our extension has a built-in method to set a default boot setting -- use it, to keep it in sync.
				# (Generally, only benefit of doing this is to overwrite an existing setting that may have been set
				# by the user using grub-reboot since last boot-update was run.)
				ext._set_default(boot_menu)
			self.msgs.append(["info", "%s set to default kernel." % sys.argv[2]])
		else:
			self.msgs.append(["error", "Could not find specified kernel image."])
		self.cleanup(success=found)

	def success_action(self):
		if os.geteuid() != 0:
			Output.fatal("This action requires root privileges.")
		# Update our record of the last kernel booted:
		self.boot_config.idmapper.update_last_id()

		# If a kernel is waiting to be promoted to default, then do it:
		promoted, kname = self.boot_config.idmapper.promote_kernel()
		if promoted:
			boot_menu = BootLoaderMenu(self.get_extension(), self.boot_config)
			self.update(boot_menu, quiet=True, cleanup=False)
			if boot_menu.has_kname(kname):
				self.msgs.append(["info", "Boot success -- %s promoted to default kernel." % kname])
			else:
				self.msgs.append(["warn", "Could not find the kernel %s to promote." % kname])
			self.cleanup(boot_menu.success)
		else:
			self.msgs.append(["warn", "Unable to find a kernel to promote."])
			self.cleanup(False)

	def attempt_action(self):
		if self.options.identifier != "default":
			boot_menu = BootLoaderMenu(
				self.get_extension(self.boot_options), self.boot_config, user_specified_attempt_identifier=self.options.identifier
			)
			self.update(boot_menu, quiet=False, cleanup=True)
		else:
			self.boot_config.idmapper.remove_promote_setting()
			self.msgs.append(["info", "Any attempted kernel setting has been wiped -- default will be used."])
			return self.update_action()

	@property
	def boot_options(self):
		return {"device-shift": self.options.device_shift}

	def update_action(self, check=False, quiet=False) -> BootLoaderMenu:
		boot_menu = BootLoaderMenu(self.get_extension(self.boot_options), self.boot_config)
		self.update(boot_menu, quiet=quiet, cleanup=True, check=check, boot_options=self.boot_options)
		return boot_menu

	def show_action(self):
		if "defaults" in self.options.sub_action:
			self.handle_show_defaults_action()
		else:
			print(self.options.sub_action)
			print("ARGH!")

	def add_arguments(self, parser):
		parser.add_argument(
			"--show-defaults", "--showdefaults", action="store_true", help="Show default settings for /etc/boot.conf."
		)
		parser.add_argument("--show", default=None, metavar="sect/val", help="Echo a specific configuration setting.")
		parser.add_argument(
			"--set-default",
			default=None,
			metavar="path-to-kernel-img",
			help="Set a default kernel image to boot using /etc/boot.d.",
		)
		parser.add_argument(
			"--check", action="store_true", help="Check the validity of the %s file." % self.boot_config_file
		)
		parser.add_argument(
			"--device-shift",
			default=None,
			metavar="sda,sdb",
			help="Modify disk references FROM,TO -- for generating configs for temp. mounted disks.",
		)
		subparsers = parser.add_subparsers(title="actions", dest="action")
		update_parser = subparsers.add_parser("update", help="Update boot loader configuration based on /etc/boot.conf.")
		update_parser.set_defaults(handler=self.update_action)
		success_parser = subparsers.add_parser("success", help="Record a successful boot.")
		success_parser.set_defaults(handler=self.success_action)
		attempt_parser = subparsers.add_parser(
			"attempt", help="Attempt to boot a new kernel without actually changing default."
		)
		attempt_parser.set_defaults(handler=self.attempt_action)
		attempt_parser.add_argument("identifier")
		microcode_parser = subparsers.add_parser(
			"microcode", help="Regenerate microcode without actually (re)generating boot loader files.."
		)
		microcode_parser.set_defaults(handler=self.microcode_action)

	def handle(self):
		handler = getattr(self.options, "handler", None)
		if handler is not None:
			# an action was specified:
			handler()
		else:
			# no action -- just an option. Call the right one:
			if self.options.show_defaults:
				self.handle_show_defaults_action()
			elif self.options.show is not None:
				self.handle_show_action()
			elif self.options.set_default is not None:
				self.set_default_action()
			elif self.options.check:
				self.update_action(check=True)
			else:
				self.update_action()


# vim: ts=4 sw=4 noet
