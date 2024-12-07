import unittest
from trading import run_trading_bot, default_config

class TestTradingBot(unittest.TestCase):
    
    def test_default_config(self):
        # Vérifiez que la configuration par défaut est chargée
        self.assertIsNotNone(default_config)
        self.assertIn('pair_symbol', default_config)
    
    def test_run_trading_bot(self):
        # Vous pouvez appeler run_trading_bot() ici si cela fait sens dans votre contexte de test
        # Par exemple, en vérifiant qu'il ne lève pas d'erreurs
        try:
            run_trading_bot()
        except Exception as e:
            self.fail(f"run_trading_bot a échoué avec l'erreur: {e}")

if __name__ == '__main__':
    unittest.main()