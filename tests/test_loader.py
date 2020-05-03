from circleguard import Loader, InvalidKeyException
from tests.utils import CGTestCase, KEY

class TestLoader(CGTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = Loader(KEY)

    def test_loading_map_id(self):
        result = self.loader.map_id("E")
        self.assertEqual(result, 0)

        result = self.loader.map_id("9d0a8fec2fe3f778334df6bdc60b113c")
        self.assertEqual(result, 221777)

    def test_loading_user_id(self):
        result = self.loader.user_id("E")
        self.assertEqual(result, 0)

        result = self.loader.user_id("] [")
        self.assertEqual(result, 13506780)

        result = self.loader.user_id("727")
        self.assertEqual(result, 10750899)

    def test_loading_username(self):
        result = self.loader.username(0)
        self.assertEqual(result, "")

        result = self.loader.username(13506780)
        self.assertEqual(result, "] [")

    def test_incorrect_key(self):
        loader = Loader("incorrect key")
        self.assertRaises(InvalidKeyException, loader.username, 13506780)
        self.assertRaises(InvalidKeyException, loader.user_id, "] [")
        self.assertRaises(InvalidKeyException, loader.map_id, "9d0a8fec2fe3f778334df6bdc60b113c")
