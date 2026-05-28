import unittest
from pprint import pprint

from lichecker import LicenseChecker

license_overrides = {}
whitelist = [
    "idna",  # BSD-like
    "charset-normalizer",  # MIT
]

allow_nonfree = False
allow_viral = False
allow_unknown = False
allow_unlicense = True
allow_ambiguous = False

pkg_name = "pyheartradio"


class TestLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        licheck = LicenseChecker(
            pkg_name,
            license_overrides=license_overrides,
            whitelisted_packages=whitelist,
            allow_ambiguous=allow_ambiguous,
            allow_unlicense=allow_unlicense,
            allow_unknown=allow_unknown,
            allow_viral=allow_viral,
            allow_nonfree=allow_nonfree,
        )
        print("Package", pkg_name)
        print("Version", licheck.version)
        print("License", licheck.license)
        print("Transient Requirements")
        pprint(licheck.transient_dependencies)
        cls.licheck = licheck

    def test_license_compliance(self):
        pprint(self.licheck.versions)
        pprint(self.licheck.licenses)
        self.licheck.validate()
