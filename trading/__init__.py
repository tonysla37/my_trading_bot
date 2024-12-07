import yaml
import os

# Chemin vers le fichier de configuration à la racine du projet
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')

# Fonctions pour gérer la configuration
def load_config(file_path=CONFIG_PATH):
    """Charge la configuration depuis un fichier YAML."""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def save_config(config, file_path=CONFIG_PATH):
    """Sauvegarde la configuration dans un fichier YAML."""
    with open(file_path, 'w') as file:
        yaml.dump(config, file)

# Charger la configuration par défaut lors de l'importation du package
default_config = load_config()

# Importer les modules principaux du package
from .trading_bot import main as run_trading_bot
from .trade import *
from .indicators import *
from .influx_utils import *
from .informations import *