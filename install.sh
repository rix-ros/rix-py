cp -r rixcore ~/.rix/python/
python3 -m venv --system-site-packages ~/.rix/venv
source ~/.rix/venv/bin/activate
pip install pyinstaller
pip install ~/.rix/python/rixmsg
pip install ~/.rix/python/rixcore
deactivate
