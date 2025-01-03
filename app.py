from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import subprocess
import logging
import yaml

app = Flask(__name__)

# Paths to log files
flask_logfile = os.path.join(os.path.dirname(__file__), 'flask.log')
bot_logfile = os.path.join(os.path.dirname(__file__), 'trading_bot.log')
config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')

# Configure logging for Flask
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(flask_logfile),
        logging.StreamHandler()
    ]
)

bot_process = None

def load_config():
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

def save_config(config):
    with open(config_file, 'w') as file:
        yaml.safe_dump(config, file, default_flow_style=False, sort_keys=False)

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
                    value = request.form.get(f"{key}_{sub_key}", config['trading'][key][sub_key])
                    config['trading'][key][sub_key] = convert_value(value)
            else:
                value = request.form.get(key, config['trading'][key])
                config['trading'][key] = convert_value(value)
        save_config(config)
        return redirect(url_for('config'))
    return render_template('config.html', config=config['trading'])

@app.route('/bot_status', methods=['GET'])
def bot_status():
    global bot_process
    if bot_process is None:
        return jsonify({"status": "Bot is not running"})
    elif bot_process.poll() is None:
        return jsonify({"status": "Bot is running"})
    else:
        return jsonify({"status": "Bot is not running"})

@app.route('/start_bot', methods=['POST'])
def start_bot():
    global bot_process
    if bot_process is None:
        # Remove and recreate the log file
        if os.path.exists(bot_logfile):
            os.remove(bot_logfile)
        open(bot_logfile, 'w').close()

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
    open(bot_logfile, 'w').close()
    if bot_process is not None:
        bot_process.terminate()
        bot_process = None
        return jsonify({"status": "Bot stopped"})
    else:
        return jsonify({"status": "Bot is not running"})

@app.route('/logs')
def logs():
    try:
        with open(flask_logfile, 'a'):
            pass
        with open(flask_logfile, 'r') as log_file:
            logs = log_file.readlines()[-1000:]  # Read the last 10 lines of logs
    except FileNotFoundError:
        logging.error(f"Log file not found: {flask_logfile}")
        logs = ["Log file not found."]
    return ''.join(logs)

@app.route('/bot_logs')
def bot_logs():
    try:
        with open(bot_logfile, 'a'):
            pass
        with open(bot_logfile, 'r') as log_file:
            logs = log_file.readlines()[-1000:]  # Read the last 100 lines of logs
    except FileNotFoundError:
        logging.error(f"Log file not found: {bot_logfile}")
        logs = ["Log file not found."]
    return ''.join(logs)

@app.route('/logs_page')
def logs_page():
    return render_template('logs.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7777)