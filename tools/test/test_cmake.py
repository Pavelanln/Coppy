import contextlib
import os
import typing
from typing import Iterator, Optional, Sequence
import unittest
import unittest.mock

import tools.setup_helpers.env  # noqa: F401 unused but resolves circular import
import tools.setup_helpers.cmake


T = typing.TypeVar('T')


class TestCMake(unittest.TestCase):

    @unittest.mock.patch('multiprocessing.cpu_count')
    def test_build_jobs(self, mock_cpu_count: unittest.mock.MagicMock) -> None:
        """Tests that the number of build jobs comes out correctly."""
        mock_cpu_count.return_value = 13
        cases = [
            # MAX_JOBS, USE_NINJA, IS_WINDOWS,         want
            ((     '8',      True,     False),         ['-j',  '8']),
            ((    None,      True,     False),         ['-j', '13']),
            ((    None,      True,      True),         ['-j', '13']),
            ((    None,     False,      True), ['/p:CL_MPCount=13']),
        ]
        for (max_jobs, use_ninja, is_windows), want in cases:
            with self.subTest(MAX_JOBS=max_jobs, USE_NINJA=use_ninja, IS_WINDOWS=is_windows):
                with contextlib.ExitStack() as stack:
                    stack.enter_context(env_var('MAX_JOBS', max_jobs))
                    stack.enter_context(unittest.mock.patch.object(tools.setup_helpers.cmake, 'USE_NINJA', use_ninja))
                    stack.enter_context(unittest.mock.patch.object(tools.setup_helpers.cmake, 'IS_WINDOWS', is_windows))

                    cmake = tools.setup_helpers.cmake.CMake()

                    with unittest.mock.patch.object(cmake, 'run') as cmake_run:
                        cmake.build({})

                    cmake_run.assert_called_once()
                    call, = cmake_run.mock_calls
                    build_args, _ = call.args

                self.assert_contains_sequence(build_args, want)

    @staticmethod
    def assert_contains_sequence(sequence: Sequence[T], subsequence: Sequence[T]) -> None:
        """Raises an assertion if the subsequence is not contained in the sequence."""
        if len(subsequence) == 0:
            return True  # all sequences contain the empty subsequence

        # Iterate over all windows of len(subsequence). Stop if the
        # window matches.
        for i in range(len(sequence) - len(subsequence) + 1):
            candidate = sequence[i : i + len(subsequence)]
            assert len(candidate) == len(subsequence)  # sanity check
            if candidate == subsequence:
                return  # found it
        raise AssertionError(f'{subsequence} not found in {sequence}')


@contextlib.contextmanager
def env_var(key: str, value: Optional[str]) -> Iterator[None]:
    """Sets/clears an environment variable within a Python context."""
    # Get the previous value and then override it.
    previous_value = os.environ.get(key)
    set_env_var(key, value)
    try:
        yield
    finally:
        # Restore to previous value.
        set_env_var(key, previous_value)


def set_env_var(key: str, value: Optional[str]) -> None:
    """Sets/clears an environment variable."""
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
