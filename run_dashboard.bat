@echo off
python -m pip install -r requirements.txt
python train_model.py
python -m uvicorn server:app --host 127.0.0.1 --port 8000
