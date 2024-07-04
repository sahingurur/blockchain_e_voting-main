import sqlite3

def setup_database():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
       
    # Adaylar tablosunu oluştur
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS adaylar (
        aday_id INTEGER PRIMARY KEY,
        aday_adi TEXT NOT NULL
    )
    ''')
    
    #cursor.execute('''CREATE TABLE secmenler (
    #                   secmen_id INTEGER PRIMARY KEY,
    #                   sifre TEXT NOT NULL,
    #                  secmen_il TEXT NOT NULL,
    #                   secmen_ilce TEXT NOT NULL,
    #                   unique_id TEXT UNIQUE
    #                )''')
    
    #cursor.execute("DELETE FROM adaylar WHERE aday_id IN (1, 2);")
    #cursor.execute("ALTER TABLE adaylar ADD COLUMN aday_foto TEXT;")
    cursor.execute('''
      CREATE TABLE IF NOT EXISTS secmenler(
                   secmen_id INTEGER PRIMARY KEY,
                   sifre TEXT NOT NULL,
                   secmen_il TEXT NOT NULL,
                   secmen_ilce TEXT NOT NULL
      )
    ''')
    

# Örnek aday verileri ekle
    #cursor.execute("INSERT INTO adaylar (aday_id, aday_adi,aday_foto) VALUES (3, 'Aslı Savaş','asli.png'), (4, 'Beyza Özdemir','beyza.png'),(5,'Gurur Şahin','gurur.png')")
    '''secmenler = [
            (1, 'sifre1', 'Istanbul', 'Kadikoy'),
            (2, 'sifre2', 'Ankara', 'Cankaya'),
            (3, 'sifre3', 'Izmir', 'Bornova'),
            (4,'sifre4','Istanbul','Kadikoy'),
            (5,'sifre5','Istanbul','Avcilar'),
            (6,'sifre6','Izmir','Bornova'),
            (7,'sifre7','Istanbul','Bagcilar'),
            (8,'sifre8','Ankara','Cankaya'),
            (9,'sifre9','Istanbul','Sancaktepe'),
            (10,'sifre10','Ankara','Kizilay')

        ]'''
    
    #cursor.executemany('''INSERT INTO secmenler (secmen_id, sifre, secmen_il, secmen_ilce)
        #                  VALUES (?, ?, ?, ?)''', secmenler)

    
    

    connection.commit()
    connection.close()

setup_database()

def add_oy_kullandi_column():
    # Veritabanı bağlantısını aç
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    # Sütunu eklemek için SQL komutunu çalıştır
    cursor.execute('ALTER TABLE secmenler ADD COLUMN oy_kullandi INTEGER DEFAULT 0')

    # Değişiklikleri kaydet ve bağlantıyı kapat
    connection.commit()
    connection.close()

add_oy_kullandi_column()
