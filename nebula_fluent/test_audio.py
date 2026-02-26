import sys
import os
sys.path.append(os.getcwd())
from core.audio_service import AudioService

print("Testing Input Devices...")
try:
    mics = AudioService.get_input_devices()
    print(f"Mics found: {len(mics)}")
    for m in mics: print(f" - {m['name']}")
except Exception as e:
    print(f"Mic Error: {e}")

print("\nTesting Output Devices...")
try:
    spks = AudioService.get_output_devices()
    print(f"Speakers found: {len(spks)}")
    for s in spks: print(f" - {s['name']}")
except Exception as e:
    print(f"Speaker Error: {e}")
