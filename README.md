# my_trading_bot

cd /chemin/vers/votre/projet
python3 -m venv bot
source bot/bin/activate

pip3 install --upgrade pip
pip3 install --upgrade setuptools

pip3 install -r requirements.txt

python3 trading_bot.py 


quitter venv ->
deactivate

supprimer venv ->
rm -rf bot


Tester le bot en local
python -m unittest discover tests

lancer le flask en local :
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --port 7777