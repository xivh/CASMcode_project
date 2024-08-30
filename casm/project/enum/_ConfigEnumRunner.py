import sys
from typing import TYPE_CHECKING, Any, Callable, Optional

from libcasm.configuration import (
    Configuration,
)

if TYPE_CHECKING:
    from casm.project.enum import ConfigEnumRunner, EnumData


class ConfigEnumRunner:
    """Configuration enumeration runner

    ConfigEnumRunner helps by:

    - checking a filter function and adding configurations to a configuration set
      or skipping them based on the value
    - maintaining running counts of configurations added and excluded
    - periodically committing an enumeration to disk
    - printing information about the enumeration process

    If the configuration enumerator has an enum_index attribute, ConfigEnumRunner
    can print information about the number of configurations generated, new, and
    filtered for each step.

    See EnumCommand.occ_by_supercell for an example of how to use this class.

    """

    def __init__(
        self,
        config_enum: Any,
        curr: "EnumData",
        desc: str,
        filter_f: Optional[Callable[[Configuration, "EnumData"], bool]] = None,
        print_steps_f: Optional[Callable[["ConfigEnumRunner"], None]] = None,
        n_per_commit: int = 100000,
        print_commits: bool = True,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        config_enum: Any
            The current configuration enumerator.
        curr: casm.project.EnumData
            The current enumeration data. This is used to store and commit
            configurations.
        desc: str
            A brief description of the enumeration method.
        filter_f: Optional[Callable[[libcasm.configuration.Configuration, \
        casm.project.EnumData], bool]] = None
            A custom filter function which, if provided, should return True to keep
            a configuration, or False to skip. The arguments are the current
            configuration and the current enumeration data.
        print_steps_f: Optional[Callable[[casm.project.ConfigEnumRunner], None]] = None
            If provided, call this method with this instance for each change in
            config_enum.enum_index to print information about the current enumeration
            step.
        n_per_commit: int = 100000
            The number of configurations to enumerate per commit.
        print_commits: bool = True
            If True, print information about each commit.
        verbose: bool = False
            If True, print verbose output.
        dry_run: bool = False
            If True, do not actually add configurations to configuration_set.
        """
        self.config_enum = config_enum
        """Any: The current configuration enumerator."""

        self.curr = curr
        """casm.project.EnumData: The current enumeration data. This is used to store 
        and commit configurations."""

        self.desc = desc
        """str: A brief description of the enumeration method."""

        if filter_f is None:

            def filter_f(config: Configuration, enum: "EnumData"):
                return True

        self.filter_f = filter_f
        """Callable[[libcasm.configuration.Configuration, casm.project.EnumData], \
        bool]: A custom filter function which, if provided, should return True to keep 
        a configuration, or False to skip. 
        
        The arguments are the current configuration and the current enumeration data."""

        self.n_since_last_commit = 0
        """int: The number of configurations enumerated since the last commit"""

        self.n_per_commit = n_per_commit
        """int: The number of configurations to enumerate per commit"""

        self.enumerator_has_enum_index = hasattr(self.config_enum, "enum_index")
        """bool: True if the enumerator has an enum_index attribute"""

        self.curr_enum_index = None
        """Optional[int]: During enumeration, `curr_enum_index` is set to the index of 
        the current enumeration step obtained from `config_enum.enum_index`. 
        
        If the enumerator does not have an `enum_index` attribute it is treated as 
        having a single step."""

        self.n_config_init = len(self.curr.configuration_set)
        """int: The size of `configuration_set` before enumeration begins"""

        self.n_config_final = None
        """Optional[int]: The size of `configuration_set` after enumeration ends"""

        self.n_config_before = len(self.curr.configuration_set)
        """int: The size of `configuration_set` before the current combination of 
        background and sites"""

        self.n_config_total = 0
        """int: The number of configurations generated with the current combination of
        background and sites"""

        self.n_config_excluded = 0
        """int: The number of configurations generated with the current combination of
        background and sites, and excluded by a user's filter"""

        self.print_steps_f = print_steps_f
        """Optional[Callable[[casm.project.ConfigEnumRunner], None]]: If provided, call 
        this method with this instance for each change in enum_index to print 
        information about the current enumeration step"""

        self.print_commits = print_commits
        """bool: If True, print information about each commit"""

        self.verbose = verbose
        """bool: If True, print verbose output"""

        self.dry_run = dry_run
        """bool: If True, do not actually add configurations to configuration_set"""

    def begin(self):
        if self.verbose:
            print(f"-- Begin: {self.desc} --")
            print()
        self.n_since_last_commit = 0

    def _begin_enum_step(self):
        """Set counts at the beginning of an enumeration step"""
        self.n_config_total = 0
        self.n_config_excluded = 0
        self.n_config_before = len(self.curr.configuration_set)

        if self.verbose and self.print_steps_f is not None:
            self.print_steps_f(self)

    def _finish_enum_step(self):
        """Set counts at the end of an enumeration step"""
        n_config_after = len(self.curr.configuration_set)
        n_config_new = n_config_after - self.n_config_before

        if self.verbose and self.print_steps_f is not None:
            print(
                f"{self.n_config_total} configurations "
                f"({n_config_new} new, {self.n_config_excluded} excluded by filter)"
            )
            print()
            sys.stdout.flush()

    def check(self, configuration: Configuration) -> bool:
        """Call with each enumerated configuration, to check filter_f, insert in
        configuration_set or skip, commit if time, and update counts.

        Parameters
        ----------
        configuration: Configuration
            The configuration to check and possibly add to the configuration set.

        Returns
        -------
        filter_f_value: bool
            True if the configuration was added to the configuration set, False if
            it was excluded by the filter.
        """
        _index = 0
        if self.enumerator_has_enum_index:
            _index = self.config_enum.enum_index
        if _index != self.curr_enum_index:
            if self.curr_enum_index is not None:
                self._finish_enum_step()
            self.curr_enum_index = _index
            self._begin_enum_step()

        self.n_config_total += 1
        filter_f_value = self.filter_f(configuration, self.curr)
        if filter_f_value:
            self.curr.configuration_set.add(configuration)
        else:
            self.n_config_excluded += 1
        self.n_since_last_commit += 1
        if not self.dry_run:
            if self.n_since_last_commit >= self.n_per_commit:
                if self.verbose and self.print_commits:
                    print("!!!")
                    print(
                        f"Committing... ({self.n_since_last_commit} since last commit)"
                    )
                    print(self.curr)
                self.curr.commit(verbose=self.verbose)
                if self.verbose and self.print_commits:
                    print("!!!")
                    print()
                    sys.stdout.flush()
                self.n_since_last_commit = 0

        return filter_f_value

    def finish(self):
        """Call when enumeration is complete"""
        if self.curr_enum_index is not None:
            self._finish_enum_step()
        self.n_config_final = len(self.curr.configuration_set)

        if self.verbose and self.print_steps_f is not None:
            print("  DONE")
            print()

        if self.verbose:
            print("-- Summary --")
            print()
            print(f"  Initial number of configurations: {self.n_config_init}")
            print(f"  Final number of configurations: {self.n_config_final}")
            print()
            sys.stdout.flush()

        if self.verbose and self.print_commits:
            if self.dry_run:
                print("** Dry run: Not committing... **")
            else:
                print("Committing...")
            print()
            print(self.curr)
            print()
            sys.stdout.flush()

        if not self.dry_run:
            self.curr.commit(verbose=self.verbose)
            if self.verbose:
                print()
