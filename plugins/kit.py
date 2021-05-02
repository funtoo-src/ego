#!/usr/bin/python3

import os
import sys
from datetime import datetime

from ego.module import EgoModule
from ego.output import Color, ago
from git_helper import GitHelper
from mediawiki.cli_parser import wikitext_parse


class Module(EgoModule):
	def setup(self):
		self.repo = GitHelper(self, self.root)

	@property
	def root(self):
		if not hasattr(self, "_root"):
			root = self.config.meta_repo_root
			if not os.path.exists(os.path.dirname(root)):
				os.makedirs(os.path.dirname(root))
			self._root = root
		return self._root

	def add_arguments(self, parser):
		subparsers = parser.add_subparsers(title="actions", dest="action")
		status_parser = subparsers.add_parser("status", help="Show current kit settings.")
		status_parser.set_defaults(handler=self.meta_repo_info)
		show_parser = subparsers.add_parser("show", help="Alias for the status command.")
		show_parser.set_defaults(handler=self.meta_repo_info)
		list_parser = subparsers.add_parser("list", help="List all available kits.")
		list_parser.set_defaults(handler=self.kits_list)

	def kits_list(self):
		if not self._output_header():
			return

		print(
			"  " + Color.UNDERLINE + "kit".ljust(20),
			"is active?".ljust(15),
			"branch".ljust(15),
			"stability".ljust(9),
			Color.END,
		)
		kit_sha1 = self.config.kit_sha1_metadata

		for kit in self.config.kit_info_metadata["kit_order"]:
			if kit not in kit_sha1:
				continue

			kit_branch, kit_default_branch = self.config.get_configured_kit(kit)
			firstline = True
			for branch in kit_sha1[kit].keys():
				if firstline:
					kit_out = Color.blue(kit)
					firstline = False
				else:
					kit_out = ""
				if branch == kit_branch:
					if branch == kit_default_branch:
						branch_out = Color.blue(branch)
					else:
						branch_out = Color.cyan(branch)
					is_active = Color.blue("active")
				else:
					is_active = ""
					branch_out = branch
				print(
					"  " + str(kit_out.ljust(20)),
					is_active.ljust(15),
					branch_out.ljust(15),
					self._get_branch_stability_string(kit, branch).ljust(15),
				)
		self._output_footer()

	def _output_header(self):
		if not self.config.metadata_exists():
			self._no_repo_available()
			return False

		last_sync = self.repo.last_sync()
		if last_sync is not None:
			sync_ago_string = ago(datetime.now() - self.repo.last_sync())
			print(Color.green(self.config.meta_repo_root) + " (updated %s):" % sync_ago_string)
			print()
		return True

	def _output_footer(self):
		wikitext = "{{Note|This information comes from {{c|/etc/ego.conf}} and meta-repo metadata. After making"
		wikitext += " changes to {{c|ego.conf}}, be sure to run {{c|ego sync}} in so that the individual kit "
		wikitext += "repositories on disk are synchronized with the kit branches shown above.}}"
		wikitext_parse(wikitext, sys.stdout, indent="  ")
		sys.stdout.write("\n")

	def _get_branch_stability_string(self, kit, kit_branch):
		try:
			kit_stability = self.config.kit_info_metadata["kit_settings"][kit]["stability"][kit_branch]
		except KeyError:
			return Color.yellow("deprecated")
		if kit_stability == "prime":
			kit_stability = Color.green("prime")
		elif kit_stability == "near-prime":
			kit_stability = Color.blue("near-prime")
		elif kit_stability == "beta":
			kit_stability = Color.yellow("beta")
		elif kit_stability in ["alpha", "dev", "current"]:
			kit_stability = Color.red(kit_stability)
		return kit_stability

	def meta_repo_info(self):
		"""
		This implements 'ego sync status' and is just a starting point. It currently displays the ego.conf-defined
		or default repo, but not the actual git repo that is selected on disk. So it should be a lot more sophisticated
		so that users can see when they've updated ego.conf but forgotten to run ego sync to update their meta-repo.
		"""

		if not self._output_header():
			return

		print(
			"  " + Color.UNDERLINE + "kit".ljust(20),
			"active branch".ljust(20),
			"default".ljust(20),
			"stability".ljust(9) + Color.END,
		)
		for kit in self.config.kit_info_metadata["kit_order"]:
			kit_branch, kit_default_branch = self.config.get_configured_kit(kit)
			if kit_branch is None:
				kit_branch = kit_default_branch
			if (
				"stability" in self.config.kit_info_metadata["kit_settings"][kit]
				and kit_branch in self.config.kit_info_metadata["kit_settings"][kit]["stability"]
			):
				kit_stability = self._get_branch_stability_string(kit, kit_branch)
			else:
				kit_stability = ""
			if kit_branch == kit_default_branch:
				print(
					"  " + kit.ljust(20),
					Color.BLUE + kit_default_branch.ljust(20),
					"(same)".ljust(20),
					str(kit_stability).ljust(10) + Color.END,
				)
			else:
				kb_out = kit_default_branch if kit_default_branch else "(None)"
				print(
					"  " + kit.ljust(20),
					Color.CYAN + kit_branch.ljust(20),
					kb_out.ljust(20),
					str(kit_stability).ljust(10) + Color.END,
				)
		self._output_footer()

	def handle(self):
		handler = getattr(self.options, "handler", self.meta_repo_info)
		handler()
