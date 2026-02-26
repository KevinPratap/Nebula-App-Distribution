import queue
import threading
import soundcard as sc
import numpy as np
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal as Signal, QObject

class AudioService(QThread):
    """
    Captures audio from Microphone or System Loopback
    and emits transcribed text via Signals.
    """
    transcript_ready = Signal(str, str) # text, source_label
    error_occurred = Signal(str)

    def __init__(self, use_loopback=False, source_label="Me", parent=None):
        super().__init__(parent)
        self.use_loopback = use_loopback
        self.source_label = source_label
        self.is_listening = False
        self.queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.sample_rate = 16000
        
    def run(self):
        """Main Thread Loop"""
        self.is_listening = True
        
        # Start the recording thread (Producer)
        record_thread = threading.Thread(target=self._record_loop, daemon=True)
        record_thread.start()
        
        # Process audio (Consumer) - running in this QThread
        self._process_loop()
        
        # Cleanup
        self.is_listening = False
        record_thread.join(timeout=1.0)

    def stop(self):
        self.is_listening = False
        self.wait()

    def _record_loop(self):
        """Captures raw audio chunks"""
        try:
            if self.use_loopback:
                # Loopback (System Audio)
                speaker = sc.default_speaker()
                source = sc.get_microphone(id=str(speaker.id), include_loopback=True)
            else:
                # Microphone
                source = sc.default_microphone()

            with source.recorder(samplerate=self.sample_rate, channels=1) as recorder:
                while self.is_listening:
                    try:
                        # Record 0.25s chunks
                        data = recorder.record(numframes=int(self.sample_rate * 0.25))
                        self.queue.put(data)
                    except Exception as e:
                        self.error_occurred.emit(f"Record Error: {e}")
                        break
        except Exception as e:
            self.error_occurred.emit(f"Source Error: {e}")

    def _process_loop(self):
        """Processes raw audio into text"""
        frames = []
        silence_counter = 0
        energy_threshold = 0.02
        
        while self.is_listening:
            try:
                data = self.queue.get(timeout=0.5)
                frames.append(data)
                
                # Simple Silence Detection
                rms = np.sqrt(np.mean(data**2))
                if rms < energy_threshold:
                    silence_counter += 1
                else:
                    silence_counter = 0
                
                # Process if we have enough audio and hit silence (or buffer full)
                should_process = (len(frames) >= 4 and silence_counter >= 6) or (len(frames) >= 40)
                
                if should_process:
                    self._transcribe(frames)
                    frames = []
                    silence_counter = 0
                    
            except queue.Empty:
                continue
            except Exception as e:
                pass

    def _transcribe(self, frames):
        if not frames: return
        
        try:
            # Convert float32 frames to int16 bytes
            audio_data = np.concatenate(frames)
            
            # Skip if tool quiet
            avg_rms = np.sqrt(np.mean(audio_data**2))
            if avg_rms < 0.015: 
                return

            import io, wave
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            wav_buffer.seek(0)
            
            # Recognize
            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)
                try:
                    text = self.recognizer.recognize_google(audio)
                    if text:
                        self.transcript_ready.emit(text, self.source_label)
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    self.error_occurred.emit(f"Recognition: {e}")

        except Exception as e:
            self.error_occurred.emit(f"Processing Error: {str(e)}")

    @staticmethod
    def get_input_devices():
        try:
            return [{"id": str(mic.id), "name": mic.name} for mic in sc.all_microphones(include_loopback=True)]
        except: return []

    @staticmethod
    def get_output_devices():
        try:
            return [{"id": str(spk.id), "name": spk.name} for spk in sc.all_speakers()]
        except: return []
