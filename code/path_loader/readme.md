activate environment

```bash
source venv/bin/activate
```

install dep
```bash
pip install pyserial
```

save packets in requirements
```bash
pip freeze > requirements.txt
```

deactivate env
```bash
deactivate
```

python3 -m venv venv
source venv/bin/activate
python -m ensurepip --upgrade
python -m pip install pyserial

cd /Users/luciobaiocchi/università/thesis/code/path_loader
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install matplotlib numpy
python -m pip install pyserial