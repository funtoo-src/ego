#!/usr/bin/python3

import sys
from ego.module import EgoModule
from ego.output import Color, Output


class Module(EgoModule):

	valid_sections = ["kits", "profiles", "global"]

	def noop(self):
		self.parser.print_usage()

	def handle_get_action(self):
		print(self.options.action)
		val = self.config.get_setting(self.options.section[0], self.options.key[0], default="")
		print(val)

	def handle_set_action(self):
		section = self.options.section[0]
		key = self.options.key[0]
		value = self.options.value[0]

		if section not in self.valid_sections:
			Output.fatal("Section should be one of: " + repr(self.valid_sections))

		# for kits, do some validation of config settings:

		if section == "kits":
			sha1s = self.config.kit_sha1_metadata
			if key not in sha1s:
				Output.fatal("No such kit: %s" % key)
			if value not in sha1s[key]:
				Output.error("No such branch for kit %s: %s" % (key, value))
				Output.header("Available branches")
				for branch in sha1s[key].keys():
					print("  ", branch)
				print()
				sys.exit(1)

		val = self.config.get_setting(section, key, default="")

		Output.header("Changing setting %s/%s" % (section, key))
		print(Color.darkcyan("Old value:"), val)
		self.config.set_setting(section, key, value)
		print(Color.cyan("New value:"), value)
		print()
		print("Setting saved to %s." % self.config.settings_path)

	def add_arguments(self, parser):

		subparsers = parser.add_subparsers(title="actions", dest="action")

		get_parser = subparsers.add_parser("get", help="get a configuration setting")
		get_parser.add_argument("section", nargs=1)
		get_parser.add_argument("key", nargs=1)
		get_parser.set_defaults(handler=self.handle_get_action)

		set_parser = subparsers.add_parser("set", help="set a configuration setting")
		set_parser.add_argument("section", nargs=1)
		set_parser.add_argument("key", nargs=1)
		set_parser.add_argument("value", nargs=1)
		set_parser.set_defaults(handler=self.handle_set_action)

	def handle_show_action(self):
		print(self.config)

	def handle(self):
		handler = getattr(self.options, "handler", self.noop)
		handler()


# vim: ts=4 sw=4 noet
