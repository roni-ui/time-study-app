import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime
import json

# --- SETTING HALAMAN ---
st.set_page_config(page_title="Time Study Pro - Nabati", layout="centered", page_icon="⏱️")

# --- KONEKSI GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "google_sheets_creds" in st.secrets:
            creds_dict = st.secrets["google_sheets_creds"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("kredensial.json", scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Data_Time_Study").sheet1 
        return sheet
    except Exception as e:
        st.error(f"Koneksi Google Sheets Gagal: {e}")
        return None

sheet = init_connection()

# --- INISIALISASI STATE UTK STOPWATCH & SESI ---
if 'status_waktu' not in st.session_state:
    st.session_state.status_waktu = 'awal'  # Pilihan: 'awal', 'berjalan', 'jeda'
if 'waktu_mulai' not in st.session_state:
    st.session_state.waktu_mulai = 0.0
if 'total_durasi_lalu' not in st.session_state:
    st.session_state.total_durasi_lalu = 0.0
if 'waktu_lap_lalu' not in st.session_state:
    st.session_state.waktu_lap_lalu = 0.0
if 'nomor_lap' not in st.session_state:
    st.session_state.nomor_lap = 1
if 'id_sesi_waktu' not in st.session_state:
    st.session_state.id_sesi_waktu = ""

# --- JUDUL UTAMA ---
st.title("⏱️ Time Study Pro")
st.caption("Aplikasi Observasi Waktu Kerja - Industrial Engineering Nabati Group")

# Membuat Tab
tab1, tab2 = st.tabs(["🎮 Observasi Lapangan", "📊 Mini Insight"])

# --- TAB 1: OBSERVASI LAPANGAN ---
with tab1:
    st.subheader("Form Input Operator")
    
    # Input data operator di awal (dikunci/disabled jika stopwatch sedang berjalan)
    is_running = st.session_state.status_waktu == 'berjalan' or st.session_state.status_waktu == 'jeda'
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        nama_operator = st.text_input("Nama Operator", placeholder="Nama Helper/Opertor", disabled=is_running)
        regu = st.selectbox("Regu / Shift", ["Shift 1", "Shift 2", "Shift 3"], disabled=is_running)
    with col_input2:
        posisi_kerja = st.text_input("Posisi Kerja", placeholder="Misal : Helper Packing IB", disabled=is_running)
        keterangan = st.text_input("Keterangan Tambahan", placeholder="Misal: Material delay, lancar", disabled=is_running)

    st.markdown("---")
    st.subheader("Kendali Waktu")

    # LOGIKA MENGHITUNG WAKTU RIIL UNTUK TAMPILAN SCREEN
    durasi_sekarang = st.session_state.total_durasi_lalu
    if st.session_state.status_waktu == 'berjalan':
        durasi_sekarang += time.time() - st.session_state.waktu_mulai

    # Mengubah detik menjadi format MM:SS.SS
    menit = int(durasi_sekarang // 60)
    detik = int(durasi_sekarang % 60)
    milidetik = int((durasi_sekarang % 1) * 100)
    string_waktu = f"{menit:02d}:{detik:02d}:{milidetik:02d}"

    # Visual Digital Stopwatch
    st.markdown(f"<h1 style='text-align: center; font-size: 65px; font-family: monospace; color: #FF4B4B;'>{string_waktu}</h1>", unsafe_allow_html=True)
    st.write(f"<p style='text-align: center; color: gray;'>Lap Aktif: {st.session_state.nomor_lap}</p>", unsafe_allow_html=True)

    # Tata Letak Tombol Kendali
    col_btn1, col_btn2 = st.columns(2)

    # KONDISI 1: STATUS AWAL
    if st.session_state.status_waktu == 'awal':
        with col_btn1:
            st.button("Lap", disabled=True, use_container_width=True)
        with col_btn2:
            if st.button("Start", type="primary", use_container_width=True):
                st.session_state.status_waktu = 'berjalan'
                st.session_state.waktu_mulai = time.time()
                st.session_state.waktu_lap_lalu = 0.0
                st.session_state.total_durasi_lalu = 0.0
                st.session_state.nomor_lap = 1
                # Mengunci ID waktu unik untuk sesi ini
                st.session_state.id_sesi_waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.rerun()

    # KONDISI 2: STATUS BERJALAN
    elif st.session_state.status_waktu == 'berjalan':
        with col_btn1:
            if st.button("Lap", use_container_width=True):
                # Hitung durasi bersih lap ini
                durasi_lap_ini = durasi_sekarang - st.session_state.waktu_lap_lalu
                
                if sheet:
                    try:
                        # Kirimkan murni sebagai angka (float), biarkan Google Sheets yang mengatur komanya
                        durasi_angka = round(durasi_lap_ini, 2)
                        row_data = [
                            nama_operator, 
                            posisi_kerja, 
                            regu, 
                            f"Lap {st.session_state.nomor_lap}", 
                            durasi_angka, 
                            st.session_state.id_sesi_waktu, 
                            keterangan
                        ]
                        # Tambahkan 'USER_ENTERED' agar Google Sheets membacanya sebagai angka kalkulator
                        sheet.append_row(row_data, value_input_option='USER_ENTERED')
                        st.toast(f"✅ Lap {st.session_state.nomor_lap} Berhasil Disimpan!", icon="💾")
                        
                        # Perbarui penanda lap selanjutnya
                        st.session_state.waktu_lap_lalu = durasi_sekarang
                        st.session_state.nomor_lap += 1
                    except Exception as e:
                        st.error(f"Gagal simpan data ke Google Sheets: {e}")
                else:
                    st.error("Koneksi Database bermasalah.")
                st.rerun()
                
        with col_btn2:
            if st.button("Stop", type="primary", use_container_width=True):
                st.session_state.status_waktu = 'jeda'
                st.session_state.total_durasi_lalu = durasi_sekarang
                st.rerun()

    # KONDISI 3: STATUS JEDA
    elif st.session_state.status_waktu == 'jeda':
        with col_btn1:
            if st.button("Reset", use_container_width=True):
                st.session_state.status_waktu = 'awal'
                st.session_state.total_durasi_lalu = 0.0
                st.session_state.waktu_lap_lalu = 0.0
                st.session_state.nomor_lap = 1
                st.rerun()
        with col_btn2:
            if st.button("Resume", type="primary", use_container_width=True):
                st.session_state.status_waktu = 'berjalan'
                st.session_state.waktu_mulai = time.time()
                st.rerun()

    # Fitur Otomatis Refresh Layar saat Stopwatch Berjalan (agar angka berdetak naik)
    if st.session_state.status_waktu == 'berjalan':
        time.sleep(0.1)
        st.rerun()

# --- TAB 2: MINI-INSIGHT ---
with tab2:
    st.subheader("Riwayat Data Terakhir")
    st.info("Menarik 15 baris terakhir dari *database* hari ini untuk konfirmasi visual.")
    
    if st.button("🔄 Refresh Tabel"):
        if sheet:
            try:
                raw_data = sheet.get_all_values()
                if len(raw_data) > 1:
                    headers = raw_data[0]
                    df = pd.DataFrame(raw_data[1:], columns=headers)
                    
                    # Pembersihan format angka agar rapi desimalnya (mengatasi koma regional Indonesia)
                    kolom_angka = ['Durasi Lap', 'Average', 'Unit/Min', 'Unit/min+Allowance']
                    for col in kolom_angka:
                        if col in df.columns:
                            df[col] = df[col].astype(str).str.strip().str.replace(',', '.', regex=False)
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
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
            st.error("Koneksi database belum siap.")
