import sqlite3

# Membuat koneksi ke database (file akan dibuat jika belum ada)
conn = sqlite3.connect('riwayat_prediksi.db')
cursor = conn.cursor()

# Membuat tabel untuk menyimpan riwayat
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

print("Database dan tabel 'riwayat' berhasil dibuat.")

# Menutup koneksi
conn.commit()
conn.close()