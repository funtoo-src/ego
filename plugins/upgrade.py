#!/usr/bin/python3

from ego.module import EgoModule


class Module(EgoModule):
	def add_arguments(self, parser):
		subparsers = parser.add_subparsers(title="actions", dest="action")
		# status_parser = subparsers.add_parser('status', help="Show upgrades applied to system.")
		# status_parser.set_defaults(handler=self.release_info)
		# show_parser = subparsers.add_parser('show', help="Alias for the status command.")
		# show_parser.set_defaults(handler=self.release_info)
		list_parser = subparsers.add_parser("list", help="List all available upgrades.")
		list_parser.set_defaults(handler=self.list_upgrades)

	def handle(self):
		handler = getattr(self.options, "handler", self.list_upgrades)
		handler()
