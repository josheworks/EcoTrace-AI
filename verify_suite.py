import unittest

suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(verbosity=2).run(suite)
print('SUITE_EXIT', 0 if result.wasSuccessful() else 1)
raise SystemExit(0 if result.wasSuccessful() else 1)
