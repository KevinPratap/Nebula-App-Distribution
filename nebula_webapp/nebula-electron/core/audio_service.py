import numpy as np
import os
import sys
import queue
import threading
import time
import io
import soundfile as sf
import pyaudio
from groq import Groq

class AudioService:
    """
    STEREO-COMPATIBLE INTERNAL ENGINE (v15.2)
    Fixed channel mismatch by using native device settings.
    Specifically tuned for "Stereo Mix" (Realtek).
    """
    def __init__(self, sample_rate=16000, use_loopback=True, source_label="Internal Audio"):
        self.target_rate = 16000 # AI preferred rate
        self.use_loopback = True 
        self.source_label = source_label
        self.is_listening = False
        self.queue = queue.Queue()
        self.current_volume = 0
        self.active_device_name = "Stereo Mix / Loopback"
        self._thread = None
        self.groq_key = None 
        
        # v17.0 Turbo Calibration
        self.energy_threshold = 0.0001 
        self.silence_timeout = 0.4 # Balanced (v21.2)
        self.p = pyaudio.PyAudio()
        
        # Callbacks
        self.on_transcript_callback = None 
        self.on_error_callback = None      

    def preload(self): pass

    def start(self):
        sys.stderr.write(f"DEBUG: Stereo-Compatible Engine (v15.2) starting...\n")
        sys.stderr.flush()
        if self._thread and self._thread.is_alive():
            return
        self.is_listening = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_listening = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        record_thread = threading.Thread(target=self._record_loop, daemon=True)
        record_thread.start()
        self._process_loop()
        self.is_listening = False

    def _get_best_loopback_device(self):
        """Locates the loopback/stereo mix device and its native params"""
        try:
            # 1. Look for explicit WASAPI Loopback or Stereo Mix
            potential_ids = []
            for i in range(self.p.get_device_count()):
                dev = self.p.get_device_info_by_index(i)
                name = dev.get('name').lower()
                if dev.get('maxInputChannels') > 0:
                    if "stereo mix" in name or "loopback" in name:
                        potential_ids.append(i)
            
            # 2. Prefer Stereo Mix if available
            target_idx = potential_ids[0] if potential_ids else None
            
            if target_idx is not None:
                info = self.p.get_device_info_by_index(target_idx)
                return {
                    "index": target_idx,
                    "channels": int(info.get('maxInputChannels')),
                    "rate": int(info.get('defaultSampleRate'))
                }
            
            # 3. Fallback to default input
            default = self.p.get_default_input_device_info()
            return {
                "index": default.get('index'),
                "channels": int(default.get('maxInputChannels')),
                "rate": int(default.get('defaultSampleRate'))
            }
        except:
            return None

    def _record_loop(self):
        while self.is_listening:
            stream = None
            try:
                config = self._get_best_loopback_device()
                if not config:
                    time.sleep(1)
                    continue

                sys.stderr.write(f"DEBUG: Opening Device {config['index']} ({config['channels']}ch @ {config['rate']}Hz)...\n")
                sys.stderr.flush()
                
                stream = self.p.open(
                    format=pyaudio.paFloat32,
                    channels=config['channels'],
                    rate=config['rate'],
                    input=True,
                    input_device_index=config['index'],
                    frames_per_buffer=int(config['rate'] * 0.2)
                )

                while self.is_listening:
                    try:
                        raw_data = stream.read(int(config['rate'] * 0.2), exception_on_overflow=False)
                        audio_np = np.frombuffer(raw_data, dtype=np.float32)
                        
                        # Fix Channel Mismatch in software (v15.2)
                        if config['channels'] > 1:
                            audio_np = audio_np.reshape(-1, config['channels']).mean(axis=1)
                        
                        # Downsample if needed (Naive slice for speed, or just keep as is)
                        # Groq handles 48kHz well, so we preserve quality.
                        
                        self.queue.put((audio_np, config['rate']))
                        
                        rms = np.sqrt(np.mean(audio_np**2))
                        self.current_volume = min(100, int((rms / 0.05) * 100))
                    except Exception as e:
                        sys.stderr.write(f"DEBUG: Record glitch: {e}\n")
                        break
            except Exception as e:
                sys.stderr.write(f"DEBUG: Record Loop Error: {e}\n")
                time.sleep(1)
            finally:
                if stream:
                    try: stream.close()
                    except: pass

    def _process_loop(self):
        frames = []
        current_rate = 16000
        silence_start = None
        
        while self.is_listening:
            try:
                data, rate = self.queue.get(timeout=0.5)
                current_rate = rate
                rms = np.sqrt(np.mean(data**2))
                
                if rms > self.energy_threshold:
                    frames.append(data)
                    silence_start = None
                else:
                    if frames:
                        if silence_start is None: silence_start = time.time()
                        if time.time() - silence_start > self.silence_timeout:
                            self._transcribe(frames, current_rate)
                            frames = []
                            silence_start = None
                
                if len(frames) > 15: # Faster delivery for long speech
                    self._transcribe(frames, current_rate)
                    frames = []
            except: continue

    def _transcribe(self, frames, rate):
        if not frames or not self.groq_key: return
        try:
            audio_data = np.concatenate(frames)
            if np.max(np.abs(audio_data)) < self.energy_threshold: return

            buffer = io.BytesIO()
            sf.write(buffer, audio_data, rate, format='WAV')
            buffer.seek(0)
            
            client = Groq(api_key=self.groq_key)
            text = client.audio.transcriptions.create(
                file=("speech.wav", buffer.read()),
                model="whisper-large-v3",
                response_format="text"
            ).strip()

            if text and len(text) > 3:
                sys.stderr.write(f"DEBUG: [V15.2 CLOUD] \"{text}\"\n")
                sys.stderr.flush()
                if self.on_transcript_callback:
                    self.on_transcript_callback(text, self.source_label)
        except Exception as e:
            sys.stderr.write(f"DEBUG: STT Error: {e}\n")

    @staticmethod
    def get_input_devices():
        p = pyaudio.PyAudio()
        devices = [{"id": str(i), "name": p.get_device_info_by_index(i).get('name')} 
                   for i in range(p.get_device_count()) 
                   if p.get_device_info_by_index(i).get('maxInputChannels') > 0]
        p.terminate()
        return devices

    @staticmethod
    def get_output_devices():
        p = pyaudio.PyAudio()
        devices = [{"id": str(i), "name": p.get_device_info_by_index(i).get('name')} 
                   for i in range(p.get_device_count()) 
                   if p.get_device_info_by_index(i).get('maxOutputChannels') > 0]
        p.terminate()
        return devices
