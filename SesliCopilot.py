import customtkinter as ctk
from pynput import keyboard
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import numpy as np
import os
import pyautogui
import time
import pyperclip
import threading
import json

# Tema ayarları
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Koordinat konfigürasyon dosyası
CONFIG_FILE = "koordinatlar.json"

# Varsayılan koordinatlar
DEFAULT_KOORDINATLAR = {
    "vscode": {
        "yazma_x": 1689,
        "yazma_y": 987,
        "gonder_x": 1884,
        "gonder_y": 1007
    },
    "vs": {
        "yazma_x": 1775,
        "yazma_y": 921,
        "gonder_x": 1869,
        "gonder_y": 970
    }
}

def koordinatlari_yukle():
    """JSON dosyasından koordinatları yükle"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return DEFAULT_KOORDINATLAR.copy()
    return DEFAULT_KOORDINATLAR.copy()

def koordinatlari_kaydet(koordinatlar):
    """Koordinatları JSON dosyasına kaydet"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(koordinatlar, f, indent=2, ensure_ascii=False)

# Koordinatları yükle
koordinatlar = koordinatlari_yukle()

# Aktif kullanılacak koordinatlar (varsayılan VS Code)
mesaj_yazma_alani = (koordinatlar["vscode"]["yazma_x"], koordinatlar["vscode"]["yazma_y"])
mesaj_gonder_buton = (koordinatlar["vscode"]["gonder_x"], koordinatlar["vscode"]["gonder_y"])

# Kayıt durumu
kaydediliyor = False
ses_verisi = []
sample_rate = 16000

class SesliCopilotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎙️ Sesli Copilot - Modern")
        self.geometry("600x800")
        self.configure(fg_color="#0f172a")
        self.resizable(False, False)

        # Aktif IDE seçimi
        self.aktif_ide = "vscode"
        
        # Koordinat bulma durumu
        self.koordinat_aktif = False
        self.koordinat_timer = None
        
        # Animasyon için
        self.animasyon_aktif = False
        self.animasyon_adim = 0

        # --- ÜST PANEL (IDE SEÇİMİ) ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(pady=15, padx=20, fill="x")

        self.vscode_buton = ctk.CTkButton(
            self.top_frame, 
            text="📝 VS Code", 
            corner_radius=20,
            fg_color="#10b981", 
            hover_color="#059669", 
            font=("Inter", 14, "bold"),
            command=self.vscode_sec,
            height=40
        )
        self.vscode_buton.pack(side="left", expand=True, padx=5)

        self.vs_buton = ctk.CTkButton(
            self.top_frame, 
            text="🎨 Visual Studio", 
            corner_radius=20,
            fg_color="#1e293b", 
            hover_color="#334155",
            border_width=2, 
            border_color="#8b5cf6",
            font=("Inter", 14, "bold"),
            command=self.vs_sec,
            height=40
        )
        self.vs_buton.pack(side="left", expand=True, padx=5)

        self.koordinat_buton = ctk.CTkButton(
            self.top_frame,
            text="📍 Koordinat",
            corner_radius=20,
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=2,
            border_color="#8b5cf6",
            font=("Inter", 14, "bold"),
            command=self.koordinat_toggle,
            height=40,
            width=140
        )
        self.koordinat_buton.pack(side="left", padx=5)

        # Koordinat gösterim alanı (başlangıçta gizli)
        self.koordinat_frame = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=15)
        
        self.koordinat_label = ctk.CTkLabel(
            self.koordinat_frame,
            text="X: 0, Y: 0",
            font=("Consolas", 16, "bold"),
            text_color="#10b981"
        )
        self.koordinat_label.pack(padx=20, pady=10)

        # --- ORTA PANEL (SES GÖRSELLEŞTİRİCİ) ---
        self.circle_frame = ctk.CTkFrame(
            self, 
            width=220, 
            height=220, 
            corner_radius=110,
            fg_color="transparent", 
            border_width=4, 
            border_color="#22d3ee"
        )
        self.circle_frame.pack(pady=20)
        self.circle_frame.pack_propagate(False)

        self.mic_label = ctk.CTkLabel(
            self.circle_frame, 
            text="🎙️", 
            font=("Inter", 50)
        )
        self.mic_label.place(relx=0.5, rely=0.4, anchor="center")
        
        self.status_label = ctk.CTkLabel(
            self.circle_frame, 
            text="⚪ Beklemede", 
            font=("Inter", 13, "bold"),
            text_color="#64748b"
        )
        self.status_label.place(relx=0.5, rely=0.68, anchor="center")

        # --- ALGILANAN METİN ALANI ---
        ctk.CTkLabel(
            self, 
            text="📝 Algılanan Metin:", 
            font=("Inter", 12, "bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=40, pady=(10, 5))
        
        self.text_area = ctk.CTkTextbox(
            self, 
            height=80, 
            corner_radius=15, 
            border_width=1, 
            border_color="#334155",
            fg_color="#1e293b",
            font=("Inter", 11)
        )
        self.text_area.pack(fill="x", padx=40, pady=(0, 15))

        # --- KOORDİNATLAR PANELİ ---
        self.coord_container = ctk.CTkFrame(self, fg_color="transparent")
        self.coord_container.pack(fill="x", padx=40, pady=(0, 10))

        # VS Code Koordinatları
        self.vscode_coord_frame = ctk.CTkFrame(
            self.coord_container, 
            corner_radius=15, 
            border_width=1, 
            border_color="#334155",
            fg_color="#1e293b"
        )
        self.vscode_coord_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        ctk.CTkLabel(
            self.vscode_coord_frame, 
            text="📝 VS Code Koordinatları", 
            font=("Inter", 11, "bold"),
            text_color="#10b981"
        ).pack(pady=8)
        
        # Yazma alanı
        yazma_frame = ctk.CTkFrame(self.vscode_coord_frame, fg_color="transparent")
        yazma_frame.pack(pady=3, padx=10)
        ctk.CTkLabel(yazma_frame, text="Yazma:", font=("Inter", 9), text_color="#94a3b8").pack(side="left", padx=(0, 5))
        
        self.vscode_yazma_x = ctk.CTkEntry(yazma_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vscode_yazma_x.pack(side="left", padx=2)
        self.vscode_yazma_x.insert(0, str(koordinatlar["vscode"]["yazma_x"]))
        self.vscode_yazma_x.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vscode"))
        
        self.vscode_yazma_y = ctk.CTkEntry(yazma_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vscode_yazma_y.pack(side="left", padx=2)
        self.vscode_yazma_y.insert(0, str(koordinatlar["vscode"]["yazma_y"]))
        self.vscode_yazma_y.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vscode"))
        
        # Gönder butonu
        gonder_frame = ctk.CTkFrame(self.vscode_coord_frame, fg_color="transparent")
        gonder_frame.pack(pady=(3, 8), padx=10)
        ctk.CTkLabel(gonder_frame, text="Gönder:", font=("Inter", 9), text_color="#94a3b8").pack(side="left", padx=(0, 5))
        
        self.vscode_gonder_x = ctk.CTkEntry(gonder_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vscode_gonder_x.pack(side="left", padx=2)
        self.vscode_gonder_x.insert(0, str(koordinatlar["vscode"]["gonder_x"]))
        self.vscode_gonder_x.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vscode"))
        
        self.vscode_gonder_y = ctk.CTkEntry(gonder_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vscode_gonder_y.pack(side="left", padx=2)
        self.vscode_gonder_y.insert(0, str(koordinatlar["vscode"]["gonder_y"]))
        self.vscode_gonder_y.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vscode"))

        # Visual Studio Koordinatları
        self.vs_coord_frame = ctk.CTkFrame(
            self.coord_container, 
            corner_radius=15, 
            border_width=1, 
            border_color="#334155",
            fg_color="#1e293b"
        )
        self.vs_coord_frame.pack(side="left", fill="both", expand=True, padx=(8, 0))
        
        ctk.CTkLabel(
            self.vs_coord_frame, 
            text="🎨 Visual Studio Koordinatları", 
            font=("Inter", 11, "bold"),
            text_color="#10b981"
        ).pack(pady=8)
        
        # Yazma alanı
        vs_yazma_frame = ctk.CTkFrame(self.vs_coord_frame, fg_color="transparent")
        vs_yazma_frame.pack(pady=3, padx=10)
        ctk.CTkLabel(vs_yazma_frame, text="Yazma:", font=("Inter", 9), text_color="#94a3b8").pack(side="left", padx=(0, 5))
        
        self.vs_yazma_x = ctk.CTkEntry(vs_yazma_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vs_yazma_x.pack(side="left", padx=2)
        self.vs_yazma_x.insert(0, str(koordinatlar["vs"]["yazma_x"]))
        self.vs_yazma_x.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vs"))
        
        self.vs_yazma_y = ctk.CTkEntry(vs_yazma_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vs_yazma_y.pack(side="left", padx=2)
        self.vs_yazma_y.insert(0, str(koordinatlar["vs"]["yazma_y"]))
        self.vs_yazma_y.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vs"))
        
        # Gönder butonu
        vs_gonder_frame = ctk.CTkFrame(self.vs_coord_frame, fg_color="transparent")
        vs_gonder_frame.pack(pady=(3, 8), padx=10)
        ctk.CTkLabel(vs_gonder_frame, text="Gönder:", font=("Inter", 9), text_color="#94a3b8").pack(side="left", padx=(0, 5))
        
        self.vs_gonder_x = ctk.CTkEntry(vs_gonder_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vs_gonder_x.pack(side="left", padx=2)
        self.vs_gonder_x.insert(0, str(koordinatlar["vs"]["gonder_x"]))
        self.vs_gonder_x.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vs"))
        
        self.vs_gonder_y = ctk.CTkEntry(vs_gonder_frame, width=60, height=28, corner_radius=8, font=("Inter", 10))
        self.vs_gonder_y.pack(side="left", padx=2)
        self.vs_gonder_y.insert(0, str(koordinatlar["vs"]["gonder_y"]))
        self.vs_gonder_y.bind("<KeyRelease>", lambda e: self.koordinat_degisti("vs"))

        # --- LOG ALANI ---
        ctk.CTkLabel(
            self, 
            text="📋 Sistem Logu:", 
            font=("Inter", 12, "bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=40, pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(
            self, 
            height=100, 
            corner_radius=15,
            fg_color="#0d1117",
            border_width=1,
            border_color="#334155",
            font=("Consolas", 10),
            text_color="#10b981"
        )
        self.log_text.pack(fill="x", padx=40, pady=(0, 20))
        
        self.log("✅ Program başlatıldı")
        self.log("⌨️  END tuşuna basarak kayıt başlatabilirsiniz")

        # Ses akışını başlat (hata varsa skip et)
        try:
            self.ses_stream = sd.InputStream(
                callback=self.ses_callback, 
                channels=1, 
                samplerate=sample_rate
            )
            self.ses_stream.start()
        except Exception as e:
            self.log(f"⚠️  Ses akışı hatası: {str(e)}")
            self.ses_stream = None
        
        # Global klavye dinleyicisini başlat
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

        # Kapanış protokolü
        self.protocol("WM_DELETE_WINDOW", self.kapat)

    def log(self, mesaj):
        """Log alanına mesaj ekle"""
        self.log_text.insert("end", f"{mesaj}\n")
        self.log_text.see("end")

    def koordinat_degisti(self, ide):
        """Koordinat değiştiğinde otomatik kaydet"""
        try:
            if ide == "vscode":
                koordinatlar["vscode"]["yazma_x"] = int(self.vscode_yazma_x.get())
                koordinatlar["vscode"]["yazma_y"] = int(self.vscode_yazma_y.get())
                koordinatlar["vscode"]["gonder_x"] = int(self.vscode_gonder_x.get())
                koordinatlar["vscode"]["gonder_y"] = int(self.vscode_gonder_y.get())
            elif ide == "vs":
                koordinatlar["vs"]["yazma_x"] = int(self.vs_yazma_x.get())
                koordinatlar["vs"]["yazma_y"] = int(self.vs_yazma_y.get())
                koordinatlar["vs"]["gonder_x"] = int(self.vs_gonder_x.get())
                koordinatlar["vs"]["gonder_y"] = int(self.vs_gonder_y.get())
            
            # JSON'a kaydet
            koordinatlari_kaydet(koordinatlar)
            
            # Aktif IDE ise koordinatları güncelle
            if self.aktif_ide == ide:
                self.koordinatlari_uygula()
        except ValueError:
            pass

    def koordinatlari_uygula(self):
        """Aktif IDE'nin koordinatlarını global değişkenlere uygula"""
        global mesaj_yazma_alani, mesaj_gonder_buton
        
        if self.aktif_ide == "vscode":
            mesaj_yazma_alani = (koordinatlar["vscode"]["yazma_x"], koordinatlar["vscode"]["yazma_y"])
            mesaj_gonder_buton = (koordinatlar["vscode"]["gonder_x"], koordinatlar["vscode"]["gonder_y"])
        elif self.aktif_ide == "vs":
            mesaj_yazma_alani = (koordinatlar["vs"]["yazma_x"], koordinatlar["vs"]["yazma_y"])
            mesaj_gonder_buton = (koordinatlar["vs"]["gonder_x"], koordinatlar["vs"]["gonder_y"])

    def vscode_sec(self):
        """VS Code IDE'yi aktif et"""
        self.aktif_ide = "vscode"
        self.koordinatlari_uygula()
        
        # Buton renklerini güncelle
        self.vscode_buton.configure(fg_color="#10b981", border_width=0)
        self.vs_buton.configure(fg_color="#1e293b", border_width=2)
        
        self.log("✅ VS Code koordinatları aktif")

    def vs_sec(self):
        """Visual Studio IDE'yi aktif et"""
        self.aktif_ide = "vs"
        self.koordinatlari_uygula()
        
        # Buton renklerini güncelle
        self.vscode_buton.configure(fg_color="#1e293b", border_width=2)
        self.vs_buton.configure(fg_color="#10b981", border_width=0)
        
        self.log("✅ Visual Studio koordinatları aktif")

    def koordinat_toggle(self):
        """Koordinat bulma özelliğini aç/kapat"""
        if not self.koordinat_aktif:
            # Koordinat bulmayı aktif et
            self.koordinat_aktif = True
            self.koordinat_frame.pack(after=self.top_frame, padx=20, pady=(0, 10))
            self.koordinat_buton.configure(fg_color="#ff6b00", border_width=0)
            self.koordinat_guncelle()
            self.log("📍 Koordinat bulma aktif")
        else:
            # Koordinat bulmayı kapat
            self.koordinat_aktif = False
            self.koordinat_frame.pack_forget()
            self.koordinat_buton.configure(fg_color="#1e293b", border_width=2)
            if self.koordinat_timer:
                self.after_cancel(self.koordinat_timer)
            self.log("📍 Koordinat bulma kapatıldı")

    def koordinat_guncelle(self):
        """Fare koordinatlarını sürekli güncelle"""
        if self.koordinat_aktif:
            x, y = pyautogui.position()
            self.koordinat_label.configure(text=f"X: {x:4d}, Y: {y:4d}")
            self.koordinat_timer = self.after(100, self.koordinat_guncelle)

    def mikrofon_animasyon_baslat(self):
        """Kayıt animasyonunu başlat"""
        self.animasyon_aktif = True
        self.circle_frame.configure(border_color="#ef4444")
        self.status_label.configure(text="🎙️ KAYIT EDİYOR", text_color="#ef4444")
        self.mikrofon_animasyon()

    def mikrofon_animasyon_durdur(self):
        """Kayıt animasyonunu durdur"""
        self.animasyon_aktif = False
        self.circle_frame.configure(border_color="#22d3ee")
        self.status_label.configure(text="⚙️ İşleniyor...", text_color="#f59e0b")

    def mikrofon_animasyon(self):
        """Animasyon efekti"""
        if self.animasyon_aktif:
            self.animasyon_adim += 1
            # Basit bir pulse efekti
            scale = 1 + np.sin(self.animasyon_adim * 0.2) * 0.05
            # Border rengini değiştir (pulse efekti)
            self.after(50, self.mikrofon_animasyon)

    def copilot_mesaj_gonder(self, metin):
        """Copilot Chat'e mesaj gönderir"""
        self.log(f"📤 Copilot'a gönderiliyor: {metin}")
        
        # Mesaj yazma alanına 2 kez tıkla
        pyautogui.click(*mesaj_yazma_alani)
        time.sleep(0.1)
        pyautogui.click(*mesaj_yazma_alani)
        time.sleep(0.1)
        
        # Mesajı panoya kopyala ve yapıştır
        pyperclip.copy(metin)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)
        
        # Gönder butonuna tıkla
        pyautogui.click(*mesaj_gonder_buton)
        self.log("✅ Mesaj gönderildi!")

    def ses_kaydet(self):
        """Kayıt başlat/durdur"""
        global kaydediliyor, ses_verisi
        
        if not kaydediliyor:
            # Kayıt başlat
            kaydediliyor = True
            ses_verisi = []
            self.mikrofon_animasyon_baslat()
            self.log("🎤 Kayıt başladı... (END'e tekrar basın)")
        else:
            # Kayıt durdur
            kaydediliyor = False
            self.mikrofon_animasyon_durdur()
            self.log("⏹️  Kayıt durdu, işleniyor...")
            
            # İşlemi ayrı thread'de yap
            threading.Thread(target=self.isleme_yap, daemon=True).start()

    def isleme_yap(self):
        """Ses işleme ve gönderme"""
        global ses_verisi
        
        if len(ses_verisi) > 0:
            # Ses verisini birleştir ve kaydet
            audio_data = np.concatenate(ses_verisi, axis=0)
            temp_file = "temp_audio.wav"
            sf.write(temp_file, audio_data, sample_rate)
            
            # Google Speech Recognition ile metne çevir
            self.log("🔄 Ses metne çevriliyor...")
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_file) as source:
                    audio = recognizer.record(source)
                
                metin = recognizer.recognize_google(audio, language="tr")
                
                # Metin alanına yaz
                self.text_area.delete("0.0", "end")
                self.text_area.insert("0.0", metin)
                
                self.log(f"📝 Algılanan: {metin}")
                
                # "kabul" kontrolü
                if "kabul" in metin.lower():
                    self.log("✅ 'Kabul' algılandı - CTRL+Enter basılıyor")
                    pyautogui.hotkey('ctrl', 'enter')
                    self.status_label.configure(text="✅ CTRL+Enter basıldı", text_color="#10b981")
                # "dur" kontrolü
                elif "dur" in metin.lower():
                    self.log("⛔ 'Dur' algılandı - CTRL+Backspace basılıyor")
                    pyautogui.hotkey('ctrl', 'backspace')
                    self.status_label.configure(text="⛔ CTRL+Backspace", text_color="#f59e0b")
                else:
                    # Copilot'a gönder
                    self.copilot_mesaj_gonder(metin)
                    self.status_label.configure(text="✅ Tamamlandı", text_color="#10b981")
                
            except sr.UnknownValueError:
                self.log("❌ Ses anlaşılamadı")
                self.status_label.configure(text="❌ Hata", text_color="#ef4444")
            except sr.RequestError as e:
                self.log(f"❌ API hatası: {e}")
                self.status_label.configure(text="❌ Hata", text_color="#ef4444")
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                # 2 saniye sonra durumu sıfırla
                self.after(2000, lambda: self.status_label.configure(
                    text="⚪ Beklemede", text_color="#64748b"
                ))
        else:
            self.log("❌ Ses kaydı bulunamadı")
            self.status_label.configure(text="⚪ Beklemede", text_color="#64748b")
        
        ses_verisi = []

    def ses_callback(self, indata, frames, time_info, status):
        """Ses kaydı callback"""
        if kaydediliyor:
            ses_verisi.append(indata.copy())

    def on_press(self, key):
        """Klavye tuşu kontrolü"""
        try:
            if key == keyboard.Key.end:
                self.ses_kaydet()
        except AttributeError:
            pass

    def kapat(self):
        """Programı kapat"""
        if self.ses_stream:
            self.ses_stream.stop()
            self.ses_stream.close()
        self.listener.stop()
        self.destroy()

if __name__ == "__main__":
    app = SesliCopilotApp()
    app.mainloop()
