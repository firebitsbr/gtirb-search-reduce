#! /usr/bin/env python3

# Enhanced Delta Debugging class
# Updated to Python 3 by Jeremy Lacomis, 2019


# Original comment by Andreas:
# Copyright (c) 1999, 2000, 2001 Andreas Zeller.
# To plug this into your system, all you have to do is to create a
# subclass with a dedicated `test()' method.  Basically, you would
# invoke the DD test case minimization algorithm (= the `ddmin()'
# method) with a list of characters; the `test()' method would combine
# them to a document and run the test.  This should be easy to realize
# and give you some good starting results; the file includes a simple
# sample application.
#
# This file is in the public domain; feel free to copy, modify, use
# and distribute this software as you wish - with one exception.
# Passau University has filed a patent for the use of delta debugging
# on program states (A. Zeller: `Isolating cause-effect chains',
# Saarland University, 2001).  The fact that this file is publicly
# available does not imply that I or anyone else grants you any rights
# related to this patent.
#
# The use of Delta Debugging to isolate failure-inducing code changes
# (A. Zeller: `Yesterday, my program worked', ESEC/FSE 1999) or to
# simplify failure-inducing input (R. Hildebrandt, A. Zeller:
# `Simplifying failure-inducing input', ISSTA 2000) is, as far as I
# know, not covered by any patent, nor will it ever be.  If you use
# this software in any way, I'd appreciate if you include a citation
# such as `This software uses the delta debugging algorithm as
# described in (insert one of the papers above)'.
#
# All about Delta Debugging is found at the delta debugging web site,
#
#               http://www.st.cs.uni-sb.de/dd/
#
# Happy debugging,
#
# Andreas Zeller

from enum import Enum, auto
from functools import lru_cache
# import resource


class Result(Enum):
    PASS = auto()
    FAIL = auto()
    UNRESOLVED = auto()


class DD:
    # Delta debugging base class.  To use this class for a particular
    # setting, create a subclass with an overloaded `test()' method.
    #
    # Main entry points are:
    # - `ddmin()' which computes a minimal failure-inducing configuration, and
    # - `dd()' which computes a minimal failure-inducing difference.
    #
    # See also the usage sample at the end of this file.
    #
    # For further fine-tuning, you can implement an own `resolve()'
    # method (tries to add or remove configuration elements in case of
    # inconsistencies), or implement an own `split()' method, which
    # allows you to split configurations according to your own
    # criteria.
    #
    # The class includes other previous delta debugging alorithms,
    # which are obsolete now; they are only included for comparison
    # purposes.

    # Resolving directions.
    ADD = "ADD"                         # Add deltas to resolve
    REMOVE = "REMOVE"                   # Remove deltas to resolve

    # Debugging output
    debug_test = False
    debug_dd = False
    debug_split = False
    debug_resolve = False

    def __init__(self):
        self.__resolving = False
        self.__last_reported_length = False
        self.monotony = False
        self.cache_outcomes = True
        self.minimize = True
        self.maximize = True
        self.assume_axioms_hold = True
        self.cachehits = 0
        self.cachemisses = 0

    # Helpers
    def __listminus(self, c1, c2):
        """Return a list of all elements of C1 that are not in C2."""
        s2 = {}
        for delta in c2:
            s2[delta] = 1

        c = []
        for delta in c1:
            if delta not in s2:
                c.append(delta)

        return c

    def __listintersect(self, c1, c2):
        """Return the common elements of C1 and C2."""
        s2 = {}
        for delta in c2:
            s2[delta] = 1

        c = []
        for delta in c1:
            if delta in s2:
                c.append(delta)

        return c

    def __listunion(self, c1, c2):
        """Return the union of C1 and C2."""
        s1 = {}
        for delta in c1:
            s1[delta] = 1

        c = c1[:]
        for delta in c2:
            if delta not in s1:
                c.append(delta)

        return c

    def __listsubseteq(self, c1, c2):
        """Return 1 if C1 is a subset or equal to C2."""
        s2 = {}
        for delta in c2:
            s2[delta] = 1

        for delta in c1:
            if delta not in s2:
                return 0

        return 1

    # Output
    def coerce(self, c):
        """Return the configuration C as a compact string"""
        # Default: use printable representation
        return str(c)

    def pretty(self, c):
        """Like coerce(), but sort beforehand"""
        sorted_c = c[:]
        sorted_c.sort()
        return self.coerce(sorted_c)

    # Testing
    # maxsize is the maximum number of cached tests
    @lru_cache(maxsize=16384)
    def test(self, c):
        """Test the configuration C.  Return PASS, FAIL, or UNRESOLVED"""
        return self._test(c)

    def _test(self, c):
        """Stub to overload in subclasses"""
        return Result.UNRESOLVED          # Placeholder

    # Splitting
    def split(self, c, n):
        """Split C into [C_1, C_2, ..., C_n]."""
        if self.debug_split:
            print(f"split({self.coerce(c)}, {n})...")

        outcome = self._split(c, n)

        if self.debug_split:
            print(f"split({self.coerce(c)}, {n}) = {outcome}")

        return outcome

    def _split(self, c, n):
        """Stub to overload in subclasses"""
        subsets = []
        start = 0
        for i in range(n):
            subset = c[start:(start + (len(c) - start) // (n - i))]
            subsets.append(subset)
            start = start + len(subset)
        return subsets

    # Resolving
    def resolve(self, csub, c, direction):
        """If direction == ADD, resolve inconsistency by adding deltas
           to CSUB.  Otherwise, resolve by removing deltas from CSUB."""

        if self.debug_resolve:
            print(f"resolve({csub}, {self.coerce(c)}, {direction})...")

        outcome = self._resolve(csub, c, direction)

        if self.debug_resolve:
            print(f"resolve({csub}, {self.coerce(c)}, "
                  f"{direction}) = {outcome}")

        return outcome

    def _resolve(self, csub, c, direction):
        """Stub to overload in subclasses."""
        # By default, no way to resolve
        return None

    # Test with fixes
    def test_and_resolve(self, csub, r, c, direction):
        """Repeat testing CSUB + R while unresolved."""

        initial_csub = csub[:]
        c2 = self.__listunion(r, c)

        csubr = self.__listunion(csub, r)
        t = self.test(tuple(csubr))

        # necessary to use more resolving mechanisms which can reverse each
        # other, can (but needn't) be used in subclasses
        self._resolve_type = 0

        while t == Result.UNRESOLVED:
            self.__resolving = 1
            csubr = self.resolve(csubr, c, direction)

            if csubr is None:
                # Nothing left to resolve
                break

            if len(csubr) >= len(c2):
                # Added everything: csub == c2. ("Upper" Baseline)
                # This has already been tested.
                csubr = None
                break

            if len(csubr) <= len(r):
                # Removed everything: csub == r. (Baseline)
                # This has already been tested.
                csubr = None
                break

            t = self.test(tuple(csubr))

        self.__resolving = 0
        if csubr is None:
            return Result.UNRESOLVED, initial_csub

        # assert t == Result.PASS or t == Result.FAIL
        csub = self.__listminus(csubr, r)
        return t, csub

    # Inquiries
    def resolving(self):
        """Return 1 while resolving."""
        return self.__resolving

    # Logging
    def report_progress(self, c, title):
        if len(c) != self.__last_reported_length:
            print()
            print(f"{title}: {len(c)} deltas left:{self.coerce(c)}")
            self.__last_reported_length = len(c)

    def test_mix(self, csub, c, direction):
        if self.minimize:
            (t, csub) = self.test_and_resolve(csub, [], c, direction)
            if t == Result.FAIL:
                return (t, csub)

        if self.maximize:
            csubbar = self.__listminus(self.CC, csub)
            cbar = self.__listminus(self.CC, c)
            if direction == self.ADD:
                directionbar = self.REMOVE
            else:
                directionbar = self.ADD

            (tbar, csubbar) = self.test_and_resolve(csubbar, [], cbar,
                                                    directionbar)

            csub = self.__listminus(self.CC, csubbar)

            if tbar == Result.PASS:
                t = Result.FAIL
            elif tbar == Result.FAIL:
                t = Result.PASS
            else:
                t = Result.UNRESOLVED

        return (t, csub)

    # Delta Debugging (new ISSTA version)
    def ddgen(self, c, minimize, maximize):
        """Return a 1-minimal failing subset of C"""

        self.minimize = minimize
        self.maximize = maximize

        n = 2
        self.CC = c

        if self.debug_dd:
            print(f"dd({self.pretty(c)}, {n})...")

        outcome = self._dd(c, n)

        if self.debug_dd:
            print(f"dd({self.pretty(c)}, {n}) = {outcome}")

        return outcome

    def _dd(self, c, n):
        """Stub to overload in subclasses"""

        assert self.test(tuple([])) == Result.PASS

        run = 1
        cbar_offset = 0

        # We replace the tail recursion from the paper by a loop
        while True:
            tc = self.test(tuple(c))
            assert tc == Result.FAIL or tc == Result.UNRESOLVED
            print(self.test.cache_info())

            if n > len(c):
                # No further minimizing
                print("dd: done")
                return c

            self.report_progress(c, "dd")

            cs = self.split(c, n)

            print()
            print(f"dd (run #{run}): trying", end='')
            for i in range(n):
                if i > 0:
                    print("+", end='')
                print(len(cs[i]), end='')
            print()

            c_failed = 0
            cbar_failed = 0

            next_c = c[:]
            next_n = n

            # Check subsets
            for i in range(n):
                if self.debug_dd:
                    print(f"dd: trying {self.pretty(cs[i])}")

                (t, cs[i]) = self.test_mix(cs[i], c, self.REMOVE)

                if t == Result.FAIL:
                    # Found
                    if self.debug_dd:
                        print(f"dd: found {len(cs[i])} deltas:")
                        print(self.pretty(cs[i]))

                    c_failed = 1
                    next_c = cs[i]
                    next_n = 2
                    cbar_offset = 0
                    self.report_progress(next_c, "dd")
                    break

            if not c_failed:
                # Check complements
                cbars = n * [Result.UNRESOLVED]

                # print(f"cbar_offset = {cbar_offset}")

                for j in range(n):
                    i = (j + cbar_offset) % n
                    cbars[i] = self.__listminus(c, cs[i])
                    t, cbars[i] = self.test_mix(cbars[i], c, self.ADD)

                    doubled = self.__listintersect(cbars[i], cs[i])
                    if doubled != []:
                        cs[i] = self.__listminus(cs[i], doubled)

                    if t == Result.FAIL:
                        if self.debug_dd:
                            print(f"dd: reduced to {len(cbars[i])}")
                            print("deltas:")
                            print(self.pretty(cbars[i]))

                        cbar_failed = 1
                        next_c = self.__listintersect(next_c, cbars[i])
                        next_n = next_n - 1
                        self.report_progress(next_c, "dd")

                        # In next run, start removing the following subset
                        cbar_offset = i
                        break

            if not c_failed and not cbar_failed:
                if n >= len(c):
                    # No further minimizing
                    print("dd: done")
                    return c

                next_n = min(len(c), n * 2)
                print(f"dd: increase granularity to {next_n}")
                cbar_offset = (cbar_offset * next_n) // n

            c = next_c
            n = next_n
            run = run + 1

    def ddmin(self, c):
        return self.ddgen(c, 1, 0)

    def ddmax(self, c):
        return self.ddgen(c, 0, 1)

    def ddmix(self, c):
        return self.ddgen(c, 1, 1)

    # General delta debugging (new TSE version)
    def dddiff(self, c):
        n = 2

        if self.debug_dd:
            print(f"dddiff({self.pretty(c)}, {n})...")

        outcome = self._dddiff([], c, n)

        if self.debug_dd:
            print(f"dddiff({self.pretty(c)}, {n}) = {outcome}")

        return outcome

    def _dddiff(self, c1, c2, n):
        run = 1
        cbar_offset = 0

        # We replace the tail recursion from the paper by a loop
        while 1:
            if self.debug_dd:
                print(f"dd: c1 = {self.pretty(c1)}")
                print(f"dd: c2 = {self.pretty(c2)}")

            if self.assume_axioms_hold:
                t1 = Result.PASS
                t2 = Result.FAIL
            else:
                t1 = self.test(tuple(c1))
                t2 = self.test(tuple(c2))

            assert t1 == Result.PASS
            assert t2 == Result.FAIL
            assert self.__listsubseteq(c1, c2)

            c = self.__listminus(c2, c1)

            if self.debug_dd:
                print(f"dd: c2 - c1 = {self.pretty(c)}")

            if n > len(c):
                # No further minimizing
                print("dd: done")
                return (c, c1, c2)

            self.report_progress(c, "dd")

            cs = self.split(c, n)

            print()
            print(f"dd (run #{run}): trying", end='')
            for i in range(n):
                if i > 0:
                    print("+", end='')
                print(len(cs[i]), end='')
            print()

            progress = 0

            next_c1 = c1[:]
            next_c2 = c2[:]
            next_n = n

            # Check subsets
            for j in range(n):
                i = (j + cbar_offset) % n

                if self.debug_dd:
                    print(f"dd: trying {self.pretty(cs[i])}")

                (t, csub) = self.test_and_resolve(cs[i], c1, c, self.REMOVE)
                csub = self.__listunion(c1, csub)

                if t == Result.FAIL and t1 == Result.PASS:
                    # Found
                    progress = 1
                    next_c2 = csub
                    next_n = 2
                    cbar_offset = 0

                    if self.debug_dd:
                        print(f"dd: reduce c2 to {len(next_c2)} deltas:")
                        print(self.pretty(next_c2))
                    break

                if t == Result.PASS and t2 == Result.FAIL:
                    # Reduce to complement
                    progress = 1
                    next_c1 = csub
                    next_n = max(next_n - 1, 2)
                    cbar_offset = i

                    if self.debug_dd:
                        print(f"dd: increase c1 to {len(next_c1)} deltas:")
                        print(self.pretty(next_c1))
                    break

                csub = self.__listminus(c, cs[i])
                (t, csub) = self.test_and_resolve(csub, c1, c, self.ADD)
                csub = self.__listunion(c1, csub)

                if t == Result.PASS and t2 == Result.FAIL:
                    # Found
                    progress = 1
                    next_c1 = csub
                    next_n = 2
                    cbar_offset = 0

                    if self.debug_dd:
                        print(f"dd: increase c1 to {len(next_c1)} deltas:")
                        print(self.pretty(next_c1))
                    break

                if t == Result.FAIL and t1 == Result.PASS:
                    # Increase
                    progress = 1
                    next_c2 = csub
                    next_n = max(next_n - 1, 2)
                    cbar_offset = i

                    if self.debug_dd:
                        print(f"dd: reduce c2 to {len(next_c2)} deltas:")
                        print(self.pretty(next_c2))
                    break

            if progress:
                self.report_progress(self.__listminus(next_c2, next_c1), "dd")
            else:
                if n >= len(c):
                    # No further minimizing
                    print("dd: done")
                    return (c, c1, c2)

                next_n = min(len(c), n * 2)
                print(f"dd: increase granularity to {next_n}")
                cbar_offset = (cbar_offset * next_n) // n

            c1 = next_c1
            c2 = next_c2
            n = next_n
            run = run + 1

    def dd(self, c):
        return self.dddiff(c)           # Backwards compatibility
