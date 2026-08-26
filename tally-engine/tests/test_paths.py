import os
import tempfile
import unittest
from unittest.mock import patch

from engine.core.paths import path_candidates


class PathTests(unittest.TestCase):
    def test_environment_path_list_is_expanded_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as temporary:
            duplicate = os.path.join(temporary, ".")
            configured = os.pathsep.join([temporary, duplicate])
            with patch.dict(os.environ, {"TALLY_TEST_PATHS": configured}):
                result = path_candidates("TALLY_TEST_PATHS")
            self.assertEqual(1, len(result))
            self.assertEqual(os.path.normcase(os.path.realpath(temporary)),
                             os.path.normcase(os.path.realpath(result[0])))


if __name__ == "__main__":
    unittest.main()
