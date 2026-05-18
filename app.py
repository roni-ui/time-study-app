import streamlit as st
import pandas as pd
import datetime
import time
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Time Study Pro", page_icon="⏱️", layout="centered")
st.title("⏱️ Time Study Pro")

# ==========================================
# KONEKSI KE GOOGLE SHEETS
# ==========================================
# Catatan: Pastikan file 'kredensial.json' dari Google Cloud sudah ada di folder yang sama
import json # Tambahkan ini di deretan import paling atas (di bawah import streamlit)

@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Jika berjalan di Streamlit Cloud (membaca dari brankas rahasia)
        if "google_sheets_creds" in st.secrets:
            creds_dict = st.secrets["google_sheets_creds"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        # Jika berjalan di laptop (membaca file json)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("kredensial.json", scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Data_Time_Study").sheet1 
        return sheet
    except Exception as e:
        st.error(f"Error aslinya: {e}")
        return None
sheet = init_connection()

# ==========================================
# INISIALISASI SESSION STATE (Untuk Stopwatch)
# ==========================================
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'laps' not in st.session_state:
    st.session_state.laps = []
if 'lap_start_time' not in st.session_state:
    st.session_state.lap_start_time = None

# ==========================================
# PEMBAGIAN TAB
# ==========================================
tab1, tab2 = st.tabs(["🎯 Observasi", "📊 Mini-Insight"])

# --- TAB 1: OBSERVASI LAPANGAN ---
with tab1:
    st.subheader("Identitas Sesi")
    col1, col2, col3 = st.columns(3)
    with col1:
        regu = st.selectbox("Regu", ["Regu 1", "Regu 2", "Regu 3"])
    with col2:
        posisi = st.text_input("Posisi", placeholder="Contoh: Packing")
    with col3:
        nama = st.text_input("Nama Operator", placeholder="Nama...")

    st.markdown("---")
    st.subheader("Kendali Waktu")
    
    col_start, col_lap, col_stop = st.columns(3)
    
    # Tombol Start
    if col_start.button("🟢 Start", use_container_width=True):
        if not st.session_state.is_running:
            st.session_state.is_running = True
            st.session_state.lap_start_time = time.time()
            st.session_state.laps = []
            st.success("Sesi observasi dimulai!")

    # Tombol Lap
    if col_lap.button("🟡 Lap", use_container_width=True):
        if st.session_state.is_running:
            lap_time = time.time() - st.session_state.lap_start_time
            st.session_state.laps.append(round(lap_time, 2))
            st.session_state.lap_start_time = time.time() # Reset waktu untuk lap berikutnya
            
    # Tombol Stop
    if col_stop.button("🔴 Stop", use_container_width=True):
        if st.session_state.is_running:
            st.session_state.is_running = False
            lap_time = time.time() - st.session_state.lap_start_time
            if lap_time > 0.1: # Menyimpan sisa waktu berjalan jika tombol stop ditekan
                st.session_state.laps.append(round(lap_time, 2))
            st.warning("Sesi observasi selesai.")

    # Visualisasi Data Lap Sementara
    if st.session_state.laps:
        st.write("**Rincian Waktu per Unit (Detik):**")
        lap_df = pd.DataFrame({"Lap": [f"Lap {i+1}" for i in range(len(st.session_state.laps))], 
                               "Durasi (Detik)": st.session_state.laps})
        st.dataframe(lap_df, use_container_width=True)

    st.markdown("---")
    keterangan = st.text_area("Keterangan Tambahan", placeholder="Contoh: Ada jeda 2 menit karena material habis...")

    # Tombol Eksekusi Pengiriman Data
    if st.button("💾 Simpan Data ke Sheets", type="primary", use_container_width=True):
        if nama and posisi and st.session_state.laps:
            if sheet:
                waktu_sekarang = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_to_insert = []
                
                # Format Satu Baris per Lap (Running Total)
                for i, lap_duration in enumerate(st.session_state.laps):
                    row = [nama, posisi, regu, f"Lap {i+1}", lap_duration, waktu_sekarang, keterangan]
                    data_to_insert.append(row)
                
                try:
                    sheet.append_rows(data_to_insert)
                    st.success(f"Sukses! {len(st.session_state.laps)} baris data berhasil dikirim ke Cloud.")
                    st.session_state.laps = [] # Kosongkan memori setelah terkirim
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat mengirim data: {e}")
            else:
                st.error("Koneksi ke Google Sheets belum siap. Cek file kredensial JSON!")
        else:
            st.error("Lengkapi Nama, Posisi, dan pastikan ada data Lap sebelum menyimpan!")

# --- TAB 2: MINI-INSIGHT ---
with tab2:
    st.subheader("Riwayat Data Terakhir")
    st.info("Menarik 15 baris terakhir dari *database* hari ini untuk konfirmasi visual.")
    
    if st.button("🔄 Refresh Tabel"):
        if sheet:
            try:
                # Menggunakan get_all_values() agar data ditarik sebagai teks murni
                # Ini mencegah Python salah menebak koma Indonesia sebagai pemisah ribuan US
                raw_data = sheet.get_all_values()
                
                if len(raw_data) > 1:
                    headers = raw_data[0]
                    df = pd.DataFrame(raw_data[1:], columns=headers)
                    
                    # 1. Bersihkan kolom angka: ganti koma jadi titik, lalu ubah ke angka desimal (float)
                    kolom_angka = ['Durasi Lap', 'Average', 'Unit/Min', 'Unit/min+Allowance']
                    for col in kolom_angka:
                        if col in df.columns:
                            # Hapus spasi kosong jika ada, ubah koma ke titik
                            df[col] = df[col].astype(str).str.strip().str.replace(',', '.', regex=False)
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 2. Tampilkan di Streamlit dengan format 2 angka di belakang koma
                    st.dataframe(
                        df.tail(15), 
                        use_container_width=True,
                        column_config={
                            "Durasi Lap": st.column_config.NumberColumn("Durasi Lap", format="%.2f"),
                            "Average": st.column_config.NumberColumn("Average", format="%.2f"),
                            "Unit/Min": st.column_config.NumberColumn("Unit/Min", format="%.2f"),
                            "Unit/min+Allowance": st.column_config.NumberColumn("Unit/min+Allowance", format="%.2f")
                        }
                    )
                else:
                    st.write("Belum ada data di Spreadsheet.")
            except Exception as e:
                st.error(f"Gagal menarik data: {e}")
        else:
            st.error("Koneksi ke Google Sheets belum siap.")
