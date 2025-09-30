from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import os
import sqlite3
import datetime

app = Flask(__name__)

# =================================================================
# FUNGSI INISIALISASI DATABASE
# =================================================================
def init_db():
    """Fungsi untuk inisialisasi database. Membuat file dan tabel jika belum ada."""
    conn = sqlite3.connect('riwayat_prediksi.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS riwayat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sumber TEXT NOT NULL,
            derajat_sosoh REAL,
            kadar_air REAL,
            butir_patah REAL,
            butir_menir REAL,
            kelas_mutu TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Database sudah siap.")


# =================================================================
# FUNGSI UNTUK MENYIMPAN DATA KE DATABASE
# =================================================================
def simpan_ke_riwayat(sumber, data_list):
    """Menyimpan satu atau lebih record prediksi ke database riwayat_prediksi.db."""
    try:
        conn = sqlite3.connect('riwayat_prediksi.db')
        cursor = conn.cursor()
        for data in data_list:
            cursor.execute('''
                INSERT INTO riwayat (sumber, derajat_sosoh, kadar_air, butir_patah, butir_menir, kelas_mutu)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sumber, data.get('derajat_sosoh'), data.get('kadar_air'), data.get('butir_patah'), data.get('butir_menir'), data.get('kelas_mutu')))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saat menyimpan ke database: {e}")

# =================================================================
# FUNGSI UTAMA UNTUK KLASIFIKASI
# =================================================================
def tentukan_kelas_mutu(derajat_sosoh, kadar_air, butir_patah, butir_menir):
    """Fungsi ini menjadi pusat logika klasifikasi."""
    try:
        derajat_sosoh = float(derajat_sosoh)
        kadar_air = float(kadar_air)
        butir_patah = float(butir_patah)
        butir_menir = float(butir_menir)
    except (ValueError, TypeError):
        return "Data Tidak Lengkap"

    if (derajat_sosoh >= 95 and kadar_air <= 14 and butir_menir <= 0.5 and butir_patah <= 15):
        return "Premium"
    elif (derajat_sosoh >= 95 and kadar_air <= 14 and butir_menir <= 2.0 and butir_patah <= 25):
        return "Medium"
    elif (derajat_sosoh >= 95 and kadar_air <= 14 and butir_menir <= 4.0 and butir_patah <= 40):
        return "Submedium"
    else:
        return "Pecah"

# =======================
# Fungsi untuk dipanggil oleh DataFrame .apply()
# =======================
def klasifikasi_mutu_df(row):
    """Fungsi ini hanya bertugas mengambil data dari baris (row) dan memberikannya ke fungsi utama."""
    return tentukan_kelas_mutu(
        row["Derajat Sosoh"],
        row["Kadar Air"],
        row["Butir Patah"],
        row["Butir Menir"]
    )

# =======================
# Route Halaman
# =======================
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    hasil = ""
    if request.method == "POST":
        derajat_sosoh = float(request.form.get("Derajat_Sosoh"))
        kadar_air = float(request.form.get("Kadar_Air"))
        
        # --- PERUBAHAN DI SINI ---
        # Nama 'Butir_patah' diubah menjadi 'Butir_Patah' agar sesuai dengan HTML
        butir_patah = float(request.form.get("Butir_Patah")) 
        
        butir_menir = float(request.form.get("Butir_Menir"))
        hasil = tentukan_kelas_mutu(derajat_sosoh, kadar_air, butir_patah, butir_menir)
        
        if hasil != "Data Tidak Lengkap":
            data_to_save = [{'derajat_sosoh': derajat_sosoh, 'kadar_air': kadar_air, 'butir_patah': butir_patah, 'butir_menir': butir_menir, 'kelas_mutu': hasil}]
            simpan_ke_riwayat('Manual', data_to_save)
            
    return render_template("predict.html", output=hasil)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if file and file.filename != '':
        filename = file.filename
        filepath = os.path.join("static", filename)
        file.save(filepath)

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".xls": dataset = pd.read_excel(filepath, engine="xlrd", decimal=',')
        elif ext == ".xlsx": dataset = pd.read_excel(filepath, engine="openpyxl", decimal=',')
        else: return "Format file tidak didukung! Harus .xls atau .xlsx", 400

        kolom_angka = ["Derajat Sosoh", "Kadar Air", "Butir Patah", "Butir Menir"]
        for kolom in kolom_angka: dataset[kolom] = pd.to_numeric(dataset[kolom], errors="coerce")
        dataset["Kelas Mutu"] = dataset.apply(klasifikasi_mutu_df, axis=1)

        data_to_save = []
        for index, row in dataset.iterrows():
            data_to_save.append({'derajat_sosoh': row.get('Derajat Sosoh'), 'kadar_air': row.get('Kadar Air'),'butir_patah': row.get('Butir Patah'), 'butir_menir': row.get('Butir Menir'), 'kelas_mutu': row.get('Kelas Mutu')})
        if data_to_save: simpan_ke_riwayat(f"File: {filename}", data_to_save)

        base_name = os.path.splitext(filename)[0]
        new_filename = f"{base_name}_laporan_hasil_klasifikasi_mutu.xlsx"
        output_path = os.path.join("static", new_filename)
        dataset.to_excel(output_path, index=False)
        download_link = f"/static/{new_filename}"
        return render_template("predict.html", download_link=download_link)
        
    return "Upload gagal! Pastikan Anda sudah memilih file.", 400

@app.route('/riwayat')
def riwayat():
    try:
        conn = sqlite3.connect('riwayat_prediksi.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, strftime('%Y-%m-%d %H:%M:%S', timestamp) as timestamp, sumber, derajat_sosoh, kadar_air, butir_patah, butir_menir, kelas_mutu FROM riwayat ORDER BY id DESC")
        data_riwayat = cursor.fetchall()
        conn.close()
        return render_template('riwayat.html', riwayat=data_riwayat)
    except Exception as e:
        print(f"Error saat mengambil riwayat: {e}")
        return render_template('riwayat.html', riwayat=[])

@app.route('/hapus_riwayat', methods=['POST'])
def hapus_riwayat():
    try:
        conn = sqlite3.connect('riwayat_prediksi.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM riwayat")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='riwayat'")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saat menghapus riwayat: {e}")
    return redirect(url_for('riwayat'))

# =======================
# Jalankan aplikasi
# =======================
if __name__ == '__main__':
    init_db()  # <-- FUNGSI INISIALISASI DIPANGGIL DI SINI
    app.run()