from flask import Flask, render_template
import traceback
import os

app = Flask(__name__, template_folder='templates')

print("Checking templates dir:", os.listdir('templates'))

with app.app_context():
    try:
        print("Attempting to render admin.html...")
        render_template('admin.html')
        print("SUCCESS: admin.html rendered correctly.")
    except Exception:
        print("FAILURE: admin.html failed to render.")
        print(traceback.format_exc())
