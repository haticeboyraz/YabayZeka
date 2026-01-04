import sounddevice as sd
import soundfile as sf
import numpy as np

def record_and_play():
    """
    2 saniye boyunca mikrofona dinle ve kaydı hoparlörden çal
    """
    duration = 2  # saniye
    sample_rate = 44100  # Hz
    
    print("Dinlemeye başlanıyor... (2 saniye)")
    
    # Ses kaydı yap
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()  # Kaydı bitir
    
    print("Kaydı çalıyorum...")
    
    # Kaydı geri çal
    sd.play(recording, samplerate=sample_rate)
    sd.wait()  # Oynatmayı bitir
    
    print("İşlem tamamlandı!")
    
    return recording

if __name__ == "__main__":
    record_and_play()
