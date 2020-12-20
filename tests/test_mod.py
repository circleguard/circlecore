from tests.utils import CGTestCase

from circleguard import Mod, FuzzyMod

class TestLoader(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_mod_string_parsing(self):
        # one normal, one "special" (nc and pf), and one multimod mod
        self.assertEqual(Mod("HD"), Mod.HD)
        self.assertEqual(Mod("NC"), Mod.NC)
        self.assertEqual(Mod("SOHDDT"), Mod.HD + Mod.DT + Mod.SO)

        self.assertRaises(ValueError, lambda: Mod("DTH"))
        self.assertRaises(ValueError, lambda: Mod("DH"))

    def test_equality_reflexivity(self):
        # reflexivity test
        self.assertEqual(Mod("NC"), Mod("NC"))

    def test_mod_ordering(self):
        self.assertEqual(Mod("DTHDSO"), Mod("SOHDDT"), "Identical mods ordered differently were not equal")
        self.assertEqual(Mod("DTHR").long_name(), Mod("HRDT").long_name(), "Long name of identical mods ordered differently were not equal")
        self.assertEqual(Mod("SOAPFLEZ").short_name(), Mod("EZSOFLAP").short_name(), "Short name of identical mods ordered differently were not equal")

        self.assertEqual(Mod("HD").short_name(), "HD")
        self.assertEqual(Mod("HR").long_name(), "HardRock")
        self.assertEqual(Mod("DTHR").long_name(), "DoubleTime HardRock")
        self.assertEqual(Mod("HRDT").long_name(), "DoubleTime HardRock")

    def test_fuzzy_mod(self):
        fuzzy_mod = FuzzyMod(Mod.HD, [Mod.DT, Mod.EZ])

        self.assertTrue(Mod.HD in fuzzy_mod)
        self.assertTrue(Mod.HD + Mod.DT in fuzzy_mod)
        self.assertTrue(Mod.HD + Mod.EZ in fuzzy_mod)
        self.assertTrue(Mod.HD + Mod.EZ + Mod.DT in fuzzy_mod)
        self.assertFalse(Mod.NM in fuzzy_mod)
        self.assertFalse(Mod.DT in fuzzy_mod)
        self.assertFalse(Mod.EZ in fuzzy_mod)
        self.assertFalse(Mod.EZ + Mod.DT in fuzzy_mod)

        self.assertListEqual(fuzzy_mod.all_mods,
            [Mod.HD, Mod.HDDT, Mod.HD + Mod.EZ, Mod.HD + Mod.EZ + Mod.DT])

        self.assertRaises(TypeError, lambda: FuzzyMod(Mod.HD, []) in fuzzy_mod)
