from flask import Flask, render_template, request, redirect, url_for
import yaml
import os
import threading
import time
import logging

app = Flask(__name__)

# Chemin vers le fichier de configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')

logfile = "flask.log"

# Configurez la journalisation
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(logfile),
        logging.StreamHandler()
    ]
)

# Charger la configuration
def load_config(file_path=CONFIG_PATH):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Sauvegarder la configuration
def save_config(config, file_path=CONFIG_PATH):
    with open(file_path, 'w') as file:
        yaml.dump(config, file)

# Page principale avec des liens vers les dashboards et autres pages
@app.route('/')
def index():
    # Exemple de liens vers Grafana ou InfluxDB
    dashboards = [
        {"name": "Trading Dashboard", "url": "https://musashi37.synology.me:3000/"},
        {"name": "Performance Metrics", "url": "https://musashi37.synology.me:8086/orgs/57304d3de321d62f/data-explorer?fluxScriptEditor"}
    ]
    return render_template('index.html', dashboards=dashboards)

# Page de configuration
@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        # Mettre à jour la configuration avec les données du formulaire
        config = load_config()
        for key in config['trading']:
            config['trading'][key] = request.form.get(key, config['trading'][key])
        save_config(config)
        return redirect(url_for('config'))
    
    # Charger la configuration actuelle pour affichage
    config = load_config()
    return render_template('config.html', config=config['trading'])

# Page des logs
@app.route('/logs')
def logs():
    botlogfile = "trading_bot.log" 
    with open(botlogfile, 'r') as log_file:
        logs = log_file.readlines()[-20:]  # Lire les 20 dernières lignes de logs
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    from trading import run_trading_bot
    logging.info("Starting trading bot...")
    try:
        run_trading_bot()
    except Exception as e:
        logging.error(f"Error running trading bot: {e}")

    app.run(host='0.0.0.0', port=7777)