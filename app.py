from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import subprocess
import logging
import yaml

import trading.informations as info

app = Flask(__name__)

# Paths to log files
flask_logfile = os.path.join(os.path.dirname(__file__), 'flask.log')
bot_logfile = os.path.join(os.path.dirname(__file__), 'trading_bot.log')
config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')

# Configure logging for Flask
flask_handler = logging.FileHandler(flask_logfile)
flask_handler.setLevel(logging.DEBUG)
flask_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

flask_logger = logging.getLogger('flask_app')
flask_logger.setLevel(logging.DEBUG)
flask_logger.addHandler(flask_handler)

# Remove default Flask logger handlers to avoid duplicate logs
for handler in app.logger.handlers[:]:
    app.logger.removeHandler(handler)

app.logger.addHandler(flask_handler)

bot_process = None

def load_config():
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

def save_config(config):
    with open(config_file, 'w') as file:
        yaml.safe_dump(config, file)

def convert_value(value):
    if value.lower() in ['true', 'false']:
        return value.lower() == 'true'
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET', 'POST'])
def config():
    config = load_config()
    if request.method == 'POST':
        for key in config['trading']:
            if isinstance(config['trading'][key], dict):
                for sub_key in config['trading'][key]:
                    config['trading'][key][sub_key] = convert_value(request.form.get(f"{key}_{sub_key}"))
            else:
                config['trading'][key] = convert_value(request.form.get(key))
        save_config(config)
        return redirect(url_for('config'))
    return render_template('config.html', config=config)

@app.route('/calculate_yield', methods=['GET', 'POST'])
def calculate_yield():
    result = None
    if request.method == 'POST':
        capital = float(request.form['capital'])
        cible = float(request.form['cible'])
        temps = int(request.form['temps'])
        dca = float(request.form['dca'])
        
        result = info.calculate_rendement(capital, cible, temps, dca)
    return render_template('calculate_yield.html', result=result)

@app.route('/start_bot', methods=['POST'])
def start_bot():
    global bot_process
    # Remove and recreate the log file
    if os.path.exists(bot_logfile):
        os.remove(bot_logfile)
    if bot_process is None:
        bot_directory = os.path.dirname(os.path.abspath(__file__))
        bot_process = subprocess.Popen(['python', 'trading/trading_bot.py'], cwd=bot_directory)
        return jsonify({"status": "Bot started"})
    else:
        return jsonify({"status": "Bot is already running"})

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    global bot_process
    # Remove and recreate the log file
    if os.path.exists(bot_logfile):
        os.remove(bot_logfile)
    if bot_process is not None:
        bot_process.terminate()
        bot_process = None
        return jsonify({"status": "Bot stopped"})
    else:
        return jsonify({"status": "Bot is not running"})

@app.route('/bot_status', methods=['GET'])
def bot_status():
    global bot_process
    if bot_process is None:
        return jsonify({"status": "Bot is not running"})
    elif bot_process.poll() is None:
        return jsonify({"status": "Bot is running"})
    else:
        return jsonify({"status": "Bot is not running"})

@app.route('/flask_logs')
def flask_logs():
    try:
        with open(flask_logfile, 'a'):
            pass
        with open(flask_logfile, 'r') as flask_log_file:
            logs = flask_log_file.readlines()[-1000:]  # Lire les 1000 dernières lignes de logs
        flask_log_file.close()
    except FileNotFoundError:
        logging.error(f"Log file not found: {flask_logfile}")
        logs = ["Log file not found."]
    return ''.join(logs)

@app.route('/bot_logs')
def bot_logs():
    try:
        with open(bot_logfile, 'a'):
            pass
        with open(bot_logfile, 'r') as bot_log_file:
            logs = bot_log_file.readlines()[-1000:]  # Lire les 1000 dernières lignes de logs
            bot_log_file.close()
    except FileNotFoundError:
        logging.error(f"Log file not found: {bot_logfile}")
        logs = ["Log file not found."]
    return ''.join(logs)

@app.route('/logs')
def logs():
    return render_template('logs.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7777)