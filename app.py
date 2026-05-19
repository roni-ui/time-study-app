import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime

# --- SETTING HALAMAN ---
st.set_page_config(page_title="Time Study Pro", layout="centered", page_icon="⏱️")

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
    st.session_state.status_waktu = 'awal'  
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
if 'lap_data' not in st.session_state:
    st.session_state.lap_data = []

# KUNCI RAHASIA UNTUK MERESET FORM (Ganti Kunci)
if 'reset_key' not in st.session_state:
    st.session_state.reset_key = 0

# --- FUNGSI FORMAT WAKTU (MM:SS.ms) ---
def format_waktu(durasi_detik):
    m = int(durasi_detik // 60)
    s = int(durasi_detik % 60)
    ms = int((durasi_detik % 1) * 100)
    return f"{m:02d}:{s:02d}.{ms:02d}"

# --- JUDUL UTAMA ---
st.title("⏱️ Time Study Pro")
st.caption("Aplikasi Observasi Waktu Kerja - Industrial Engineering Nabati Group")

# Membuat Tab
tab1, tab2 = st.tabs(["🎮 Observasi Lapangan", "📊 Mini Insight"])

# --- TAB 1: OBSERVASI LAPANGAN ---
with tab1:
    is_running = st.session_state.status_waktu in ['berjalan', 'jeda']
    
    # KITA PASANG RESET KEY DI SETIAP INPUT
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        nama_operator = st.text_input("Nama Operator", placeholder="Nama Helper/Operator", disabled=is_running, key=f"nama_{st.session_state.reset_key}")
        lama_bekerja = st.text_input("Lama Bekerja", placeholder="Misal: 2 Tahun", disabled=is_running, key=f"lama_{st.session_state.reset_key}")
        regu = st.selectbox("Regu / Shift", ["Shift 1", "Shift 2", "Shift 3"], disabled=is_running, key=f"regu_{st.session_state.reset_key}")
    with col_input2:
        posisi_kerja = st.text_input("Posisi Kerja", placeholder="Misal : Helper Packing IB", disabled=is_running, key=f"posisi_{st.session_state.reset_key}")
        keterangan = st.text_input("Keterangan", placeholder="Misal: Material delay", disabled=is_running, key=f"ket_{st.session_state.reset_key}")

    st.markdown("---")

    # LOGIKA MENGHITUNG WAKTU RIIL
    durasi_sekarang = st.session_state.total_durasi_lalu
    if st.session_state.status_waktu == 'berjalan':
        durasi_sekarang += time.time() - st.session_state.waktu_mulai

    string_waktu = format_waktu(durasi_sekarang)

    # Visual Digital Stopwatch
    st.markdown(f"<h1 style='text-align: center; font-size: 75px; font-family: monospace; color: #72B2FF;'>{string_waktu}</h1>", unsafe_allow_html=True)
    
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
                st.session_state.id_sesi_waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.lap_data = [] 
                st.rerun()

    # KONDISI 2: STATUS BERJALAN
    elif st.session_state.status_waktu == 'berjalan':
        with col_btn1:
            if st.button("Lap", use_container_width=True):
                durasi_lap_ini = durasi_sekarang - st.session_state.waktu_lap_lalu
                
                st.session_state.lap_data.insert(0, {
                    "Lap": f"{st.session_state.nomor_lap:02d}",
                    "Lap times": format_waktu(durasi_lap_ini),
                    "Overall time": format_waktu(durasi_sekarang),
                    "durasi_angka": round(durasi_lap_ini, 2),
                    "nama": nama_operator,
                    "lama": lama_bekerja,
                    "posisi": posisi_kerja,
                    "regu": regu,
                    "keterangan": keterangan
                })
                
                st.session_state.waktu_lap_lalu = durasi_sekarang
                st.session_state.nomor_lap += 1
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

    # --- MENAMPILKAN TABEL RIWAYAT LAP ---
    if len(st.session_state.lap_data) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        
        df_display = pd.DataFrame(st.session_state.lap_data)[["Lap", "Lap times", "Overall time"]]
        st.dataframe(df_display, hide_index=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- TOMBOL SIMPAN MASSAL ---
        if st.button("💾 SIMPAN SEMUA DATA KE DATABASE", type="primary", use_container_width=True):
            if sheet:
                try:
                    rows_to_insert = []
                    for lap in reversed(st.session_state.lap_data):
                        rows_to_insert.append([
                            lap["nama"],
                            lap["lama"],
                            lap["posisi"],
                            lap["regu"],
                            f"Lap {int(lap['Lap'])}",
                            lap["durasi_angka"],
                            st.session_state.id_sesi_waktu,
                            lap["keterangan"]
                        ])
                    
                    sheet.append_rows(rows_to_insert, value_input_option='USER_ENTERED')
                    st.success("✅ Semua data Lap berhasil direkam ke Google Sheets!")
                    
                    # --- PROSES AUTOMATIC RESET ---
                    st.session_state.lap_data = []            
                    st.session_state.status_waktu = 'awal'     
                    st.session_state.total_durasi_lalu = 0.0   
                    st.session_state.waktu_lap_lalu = 0.0      
                    st.session_state.nomor_lap = 1            
                    
                    # MAGIS RESET FORM: Cukup ganti angkanya agar Streamlit membuat kotak baru yang bersih!
                    st.session_state.reset_key += 1
                    
                    time.sleep(1) 
                    st.rerun()    
                except Exception as e:
                    st.error(f"Gagal simpan data: {e}")
            else:
                st.error("Koneksi Database bermasalah.")

    # Otomatis refresh layar agar angka waktu bergerak
    if st.session_state.status_waktu == 'berjalan':
        time.sleep(0.08)
        st.rerun()

# --- TAB 2: MINI-INSIGHT ---
with tab2:
    st.subheader("Riwayat Data Terakhir")
    st.info("Menarik 15 baris terakhir dari *database*.")
    
    if st.button("🔄 Refresh Tabel"):
        if sheet:
            try:
                raw_data = sheet.get_all_values()
                if len(raw_data) > 1:
                    headers = raw_data[0]
                    df = pd.DataFrame(raw_data[1:], columns=headers)
                    
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
