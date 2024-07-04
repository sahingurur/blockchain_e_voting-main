from flask import Flask, render_template, request, redirect, url_for, flash, session
import hashlib
import datetime
import sqlite3
from collections import defaultdict
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Gizli anahtar oturumları yönetmek için gereklidir

class Vote:
    def __init__(self, aday_id, aday_adi, il, ilce):
        self.aday_id = aday_id
        self.aday_adi = aday_adi
        self.il = il
        self.ilce = ilce

class Voter:
    def __init__(self, secmen_id, sifre, secmen_il, secmen_ilce, oy_kullandi):
        self.secmen_id = secmen_id
        self.sifre = sifre
        self.secmen_il = secmen_il
        self.secmen_ilce = secmen_ilce
        self.oy_kullandi = oy_kullandi

class MerkleNode:
    def __init__(self, left, right, hash):
        self.left = left
        self.right = right
        self.hash = hash

class MerkleTree:
    def __init__(self, votes):
        self.leaves = [self.hash_vote(vote) for vote in votes]
        self.root = self.build_tree(self.leaves)

    def hash_vote(self, vote):
        vote_data = f"{vote.aday_id}-{vote.il}-{vote.ilce}"
        return hashlib.sha256(vote_data.encode()).hexdigest()

    def build_tree(self, leaves):
        if not leaves:
            return None
        nodes = [MerkleNode(None, None, leaf) for leaf in leaves]
        while len(nodes) > 1:
            temp_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                else:
                    right = left
                combined_hash = hashlib.sha256((left.hash + right.hash).encode()).hexdigest()
                temp_nodes.append(MerkleNode(left, right, combined_hash))
            nodes = temp_nodes
        return nodes[0] if nodes else None

class CoinBlock:
    def __init__(self, blok_id, oncekiblokhash, merkle_root_hash, zamandamgasi):
        self.blok_id = blok_id
        self.oncekiblokhash = oncekiblokhash
        self.merkle_root_hash = merkle_root_hash
        self.zamandamgasi = zamandamgasi
        self.blokveri = f"{merkle_root_hash}-{oncekiblokhash}-{zamandamgasi}"
        self.blokhashdegeri = hashlib.sha256(self.blokveri.encode()).hexdigest()
        self.secmenler = []  # Oy kullanan secmen_id'leri ve aday_id'leri depolamak için

class Blokzincir:
    def __init__(self):
        self.zincir = []
        self.secmenler = self.load_secmenler()
        self.oy_sonuclari = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.il_merkle_trees = defaultdict(lambda: defaultdict(list))
        self.adaylar = self.load_adaylar()
        self.genesis_blok_olusturucu()
        self.pending_votes = []
        self.secmen_vote_mapping = []

    def load_adaylar(self):
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute("SELECT aday_id, aday_adi FROM adaylar")
        adaylar = cursor.fetchall()
        connection.close()
        return [Vote(aday_id, aday_adi, None, None) for aday_id, aday_adi in adaylar]

    def load_secmenler(self):
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute("SELECT secmen_id, sifre, secmen_il, secmen_ilce, oy_kullandi FROM secmenler")
        secmenler = cursor.fetchall()
        connection.close()
        return {secmen_id: Voter(secmen_id, sifre, secmen_il, secmen_ilce, oy_kullandi) for secmen_id, sifre, secmen_il, secmen_ilce, oy_kullandi in secmenler}

    def genesis_blok_olusturucu(self):
        genesis_merkle_tree = MerkleTree([])
        self.zincir.append(CoinBlock(0, "0", genesis_merkle_tree.root.hash if genesis_merkle_tree.root else "0", datetime.datetime.now()))

    def oy_ekle(self, oy, secmen_id, sifre):
        if secmen_id not in self.secmenler or self.secmenler[secmen_id].sifre != sifre:
            return "Geçersiz kullanıcı ID veya şifre!"

        # Oy kullanma durumunu kontrol et
        if self.secmenler[secmen_id].oy_kullandi:
            return "Zaten oy kullandınız. Yeniden oy kullanamazsınız."
    
        il = self.secmenler[secmen_id].secmen_il
        ilce = self.secmenler[secmen_id].secmen_ilce
        oy.il = il
        oy.ilce = ilce
        self.oy_sonuclari[il][ilce][oy.aday_adi] += 1
        self.pending_votes.append(oy)
        self.secmen_vote_mapping.append((secmen_id, oy.aday_id))
        if len(self.pending_votes) >= 2:  # Örnek olarak 5 oy biriktiğinde yeni bir blok oluşturulacak
            self.blok_guncelle()
    
        # Oy kullanma durumunu güncelle
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute("UPDATE secmenler SET oy_kullandi = 1 WHERE secmen_id = ?", (secmen_id,))
        connection.commit()
        connection.close()
    
        self.secmenler[secmen_id].oy_kullandi = 1  # Voter objesini de güncelle
        return "Oy başarıyla eklendi!"


    def blok_guncelle(self):
        merkle_tree = MerkleTree(self.pending_votes)
        oncekiblokhash = self.son_blok.blokhashdegeri if self.son_blok else "0"
        yeni_blok_id = len(self.zincir)  # Blok ID'si olarak zincirdeki toplam blok sayısını kullanıyoruz
        yeni_blok = CoinBlock(yeni_blok_id, oncekiblokhash, merkle_tree.root.hash if merkle_tree.root else "0", datetime.datetime.now())
        yeni_blok.secmenler = self.secmen_vote_mapping.copy()  # Blok içindeki secmen_id ve aday_id bilgilerini kaydet
        self.zincir.append(yeni_blok)
        self.pending_votes = []
        self.secmen_vote_mapping = []

    def oy_sonuclari_goster(self):
        results = []
        for il, ilceler in self.oy_sonuclari.items():
            for ilce, oylar in ilceler.items():
                for aday, count in oylar.items():
                    results.append((il, ilce, aday, count))
        return results

    def merkle_root_goster(self):
        roots = []
        for i, blok in enumerate(self.zincir):
            roots.append((i, blok.merkle_root_hash))
        return roots

    def blok_dogrulama(self):
        valid_blocks = []
        for i, blok in enumerate(self.zincir[1:], start=1):
            valid_blocks.append((i + 1, blok.oncekiblokhash == self.zincir[i-1].blokhashdegeri))
        return valid_blocks

    def verify_blocks(self):
        block_details = []
        for blok in self.zincir:
            for secmen_id, aday_id in blok.secmenler:
                block_details.append((secmen_id, aday_id, blok.blokhashdegeri, blok.blok_id))
        return block_details

    @property
    def son_blok(self):
        return self.zincir[-1] if self.zincir else None

blok_zincirim = Blokzincir()

def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection

admins = {
    "admin": "admin123"
}

def generate_token(secmen_id):
    serializer = URLSafeTimedSerializer(app.secret_key)
    return serializer.dumps(secmen_id, salt=app.secret_key)

def verify_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        secmen_id = serializer.loads(token, salt=app.secret_key, max_age=expiration)
    except:
        return False
    return secmen_id

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        sifre = request.form['sifre']
        if admin_id in admins and admins[admin_id] == sifre:
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash("Geçersiz admin ID veya şifre!", "danger")
    return render_template('admin_login.html')

@app.route('/admin_panel')
def admin_panel():
    if 'admin' in session:
        return render_template('admin_panel.html')
    else:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('admin_login'))

@app.route('/results')
def results():
    if 'admin' in session:
        # Adayların toplam oy sayılarını hesapla
        toplam_oylar = defaultdict(int)
        for il, ilceler in blok_zincirim.oy_sonuclari.items():
            for ilce, oylar in ilceler.items():
                for aday, count in oylar.items():
                    toplam_oylar[aday] += count
        
        # Sonuçları tabloya ekle
        return render_template('results.html', toplam_oylar=toplam_oylar)
    else:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('admin_login'))


@app.route('/merkle_roots')
def merkle_roots():
    if 'admin' in session:
        il_ilce_roots = []
        for il, ilceler in blok_zincirim.oy_sonuclari.items():
            for ilce, oylar in ilceler.items():
                merkle_tree = MerkleTree([Vote(aday_id, aday, il, ilce) for aday in oylar for aday_id, aday_adi in enumerate(oylar)])
                oy_sayisi = sum(oylar.values())  # Oy sayısını hesapla
                il_ilce_roots.append((il, ilce, merkle_tree.root.hash if merkle_tree.root else "0", oy_sayisi))
        return render_template('merkle_roots.html', il_ilce_roots=il_ilce_roots)
    else:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('admin_login'))


@app.route('/blockchain_verification')
def blockchain_verification():
    if 'admin' in session:
        return render_template('blockchain_verification.html', valid_blocks=blok_zincirim.blok_dogrulama())
    else:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('admin_login'))

@app.route('/verify_blocks')
def verify_blocks():
    if 'admin' in session:
        # Seçmen ve oy bilgilerini tutan bir liste oluşturuyoruz
        secmen_oylari = []
        for blok in blok_zincirim.zincir:
            for secmen_id, aday_id in blok.secmenler:
                secmen_oylari.append({
                    'blok_id': blok.blok_id,
                    'secmen_id': secmen_id,
                    'aday_id': aday_id,
                    'zamandamgasi': blok.zamandamgasi,
                    'blok_hash': blok.blokhashdegeri,
                })
        return render_template('verify_blocks.html', secmen_oylari=secmen_oylari)
    else:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('admin_login'))



@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        secmen_id = request.form['secmen_id']
        sifre = request.form['sifre']
        connection = get_db_connection()
        secmen = connection.execute('SELECT * FROM secmenler WHERE secmen_id = ? AND sifre = ?', (secmen_id, sifre)).fetchone()
        connection.close()
        if secmen:
            token = generate_token(secmen['secmen_id'])
            session['token'] = token
            session['secmen_id'] = secmen['secmen_id']
            return redirect(url_for('vote'))
        else:
            flash('Giriş başarısız. Lütfen tekrar deneyin.', 'danger')
            return redirect(url_for('user_login'))

    return render_template('user_login.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'secmen_id' not in session:
        flash("Oy kullanmak için lütfen giriş yapın.", "danger")
        return redirect(url_for('user_login'))

    if 'token' not in session or not verify_token(session['token']):
        flash("Oturumunuzun süresi dolmuş. Lütfen tekrar giriş yapın.", "danger")
        return redirect(url_for('user_login'))

    connection = get_db_connection()
    adaylar = connection.execute('SELECT aday_id, aday_adi, aday_foto FROM adaylar').fetchall()
    connection.close()

    secmen_id = session.get('secmen_id')
    if blok_zincirim.secmenler[secmen_id].oy_kullandi:
        flash("Zaten oy kullandınız. Yeniden oy kullanamazsınız.", "danger")
        return redirect(url_for('vote_unsuccess'))

    if request.method == 'POST':
        aday_id = int(request.form['aday_id'])
        aday = next((aday for aday in adaylar if aday['aday_id'] == aday_id), None)
        if aday is None:
            flash("Geçersiz aday ID'si!", "danger")
            return redirect(url_for('vote'))

        sifre = blok_zincirim.secmenler[secmen_id].sifre
        message = blok_zincirim.oy_ekle(Vote(aday_id, aday['aday_adi'], "", ""), secmen_id, sifre)
        if message == "Oy başarıyla eklendi!":
            return redirect(url_for('vote_success'))
        else:
            flash(message, "danger")
            return redirect(url_for('vote'))

    return render_template('vote.html', adaylar=adaylar)


@app.route('/vote_success')
def vote_success():
    return render_template('vote_success.html')

@app.route('/vote_unsuccess')
def vote_unsuccess():
    return render_template('vote_unsuccess.html')
@app.route('/aday_islemleri')
def aday_islemleri():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM adaylar')
    adaylar = cur.fetchall()
    return render_template('aday_islemleri.html', adaylar=adaylar)

# Aday Ekleme İşlemi
@app.route('/aday_ekle', methods=['POST'])
def aday_ekle():
    aday_adi = request.form['aday_adi']
    aday_foto = request.form['aday_foto']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO adaylar (aday_adi, aday_foto) VALUES (?, ?)', (aday_adi, aday_foto))
    conn.commit()
    return redirect(url_for('aday_islemleri'))

# Aday Silme İşlemi
@app.route('/aday_sil/<int:aday_id>')
def aday_sil(aday_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM adaylar WHERE aday_id = ?', (aday_id,))
    conn.commit()
    return redirect(url_for('aday_islemleri'))

# Aday Güncelleme Sayfası
@app.route('/aday_guncelle/<int:aday_id>')
def aday_guncelle(aday_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM adaylar WHERE aday_id = ?', (aday_id,))
    aday = cur.fetchone()
    return render_template('aday_guncelle.html', aday=aday)

# Aday Güncelleme İşlemi
@app.route('/aday_guncelle/<int:aday_id>', methods=['POST'])
def aday_guncelle_post(aday_id):
    aday_adi = request.form['aday_adi']
    aday_foto = request.form['aday_foto']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE adaylar SET aday_adi = ?, aday_foto = ? WHERE aday_id = ?', (aday_adi, aday_foto, aday_id))
    conn.commit()
    return redirect(url_for('aday_islemleri'))

if __name__ == '__main__':
    app.run(debug=True)
