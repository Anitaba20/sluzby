from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import jwt
import re
import os
from io import BytesIO
from PIL import Image

load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "tajny-kluc")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-tajny-kluc")

db = SQLAlchemy(app)
mail = Mail(app)


google_blueprint = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_to="google_prihlasenie"
)

app.register_blueprint(google_blueprint, url_prefix="/login")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Inzerat(db.Model):
    __tablename__ = "inzeraty"

    id = db.Column(db.Integer, primary_key=True)

    nazov = db.Column(db.String(200), nullable=False)
    kategoria = db.Column(db.String(100), nullable=False)
    podkategoria = db.Column(db.String(100))

    cena = db.Column(db.Float)
    cena_dohodou = db.Column(db.Boolean, default=False)

    lokalita = db.Column(db.String(100), nullable=False)
    psc = db.Column(db.String(20))

    popis = db.Column(db.Text, nullable=False)

    obrazok = db.Column(db.String(255))
    obrazok_2 = db.Column(db.String(255))
    obrazok_3 = db.Column(db.String(255))

    datum_pridania = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Hodnotenie(db.Model):
    __tablename__ = "hodnotenia"

    id = db.Column(db.Integer, primary_key=True)
    hodnotenie = db.Column(db.Integer, nullable=False)
    datum = db.Column(db.DateTime, default=datetime.utcnow)

    autor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    hodnoteny_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    inzerat_id = db.Column(db.Integer, db.ForeignKey("inzeraty.id"), nullable=False)


class Recenzia(db.Model):
    __tablename__ = "recenzie"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    datum = db.Column(db.DateTime, default=datetime.utcnow)

    autor_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    inzerat_id = db.Column(
        db.Integer,
        db.ForeignKey("inzeraty.id"),
        nullable=False
    )


with app.app_context():
    db.create_all()


@app.context_processor
def globalne_premenne():
    return {
        "kategorie_pocty": {
            "dom_a_byvanie": Inzerat.query.filter_by(kategoria="Dom a bývanie").count(),
            "zahrada": Inzerat.query.filter_by(kategoria="Záhrada a exteriér").count(),
            "stahovanie": Inzerat.query.filter_by(kategoria="Sťahovanie a doprava").count(),
            "doucovanie": Inzerat.query.filter_by(kategoria="Doučovanie").count(),
            "online": Inzerat.query.filter_by(kategoria="Online služby").count(),
            "administrativa": Inzerat.query.filter_by(kategoria="Administratíva a financie").count(),
            "starostlivost": Inzerat.query.filter_by(kategoria="Starostlivosť a pomoc").count(),
            "krasa": Inzerat.query.filter_by(kategoria="Krása a zdravie").count(),
            "fotografovanie": Inzerat.query.filter_by(kategoria="Fotografovanie").count(),
            "preklady": Inzerat.query.filter_by(kategoria="Preklady").count()
        },

        "podkategorie_pocty": {
            "Rekonštrukcie": Inzerat.query.filter_by(podkategoria="Rekonštrukcie").count(),
            "Maľovanie a stierkovanie": Inzerat.query.filter_by(podkategoria="Maľovanie a stierkovanie").count(),
            "Elektrikárske práce": Inzerat.query.filter_by(podkategoria="Elektrikárske práce").count(),
            "Vodoinštalačné práce": Inzerat.query.filter_by(podkategoria="Vodoinštalačné práce").count(),

            "Kosenie trávnikov": Inzerat.query.filter_by(podkategoria="Kosenie trávnikov").count(),
            "Údržba záhrad": Inzerat.query.filter_by(podkategoria="Údržba záhrad").count(),
            "Živé ploty": Inzerat.query.filter_by(podkategoria="Živé ploty").count(),
            "Terénne úpravy": Inzerat.query.filter_by(podkategoria="Terénne úpravy").count(),

            "Sťahovanie": Inzerat.query.filter_by(podkategoria="Sťahovanie").count(),
            "Preprava": Inzerat.query.filter_by(podkategoria="Preprava").count(),

            "Tvorba webstránok": Inzerat.query.filter_by(podkategoria="Tvorba webstránok").count(),
            "Grafika a dizajn": Inzerat.query.filter_by(podkategoria="Grafika a dizajn").count(),
            "SEO a marketing": Inzerat.query.filter_by(podkategoria="SEO a marketing").count(),
            "Správa sociálnych sietí": Inzerat.query.filter_by(podkategoria="Správa sociálnych sietí").count(),
            "Servis počítačov": Inzerat.query.filter_by(podkategoria="Servis počítačov").count(),

            "Účtovníctvo": Inzerat.query.filter_by(podkategoria="Účtovníctvo").count(),
            "Mzdy a personalistika": Inzerat.query.filter_by(podkategoria="Mzdy a personalistika").count(),
            "Administratívna pomoc": Inzerat.query.filter_by(podkategoria="Administratívna pomoc").count(),
            "Daňové priznania": Inzerat.query.filter_by(podkategoria="Daňové priznania").count(),

            "Opatrovanie detí": Inzerat.query.filter_by(podkategoria="Opatrovanie detí").count(),
            "Opatrovanie seniorov": Inzerat.query.filter_by(podkategoria="Opatrovanie seniorov").count(),
            "Upratovanie": Inzerat.query.filter_by(podkategoria="Upratovanie").count(),
            "Pomoc v domácnosti": Inzerat.query.filter_by(podkategoria="Pomoc v domácnosti").count(),

            "Kaderníctvo": Inzerat.query.filter_by(podkategoria="Kaderníctvo").count(),
            "Kozmetika": Inzerat.query.filter_by(podkategoria="Kozmetika").count(),
            "Manikúra a pedikúra": Inzerat.query.filter_by(podkategoria="Manikúra a pedikúra").count(),
            "Masáže": Inzerat.query.filter_by(podkategoria="Masáže").count(),
            "Tetovanie": Inzerat.query.filter_by(podkategoria="Tetovanie").count(),

            "Iné - Dom a bývanie": Inzerat.query.filter_by(podkategoria="Iné - Dom a bývanie").count(),
            "Iné - Záhrada a exteriér": Inzerat.query.filter_by(podkategoria="Iné - Záhrada a exteriér").count(),
            "Iné - Sťahovanie a doprava": Inzerat.query.filter_by(podkategoria="Iné - Sťahovanie a doprava").count(),
            "Iné - Online služby": Inzerat.query.filter_by(podkategoria="Iné - Online služby").count(),
            "Iné - Administratíva a financie": Inzerat.query.filter_by(podkategoria="Iné - Administratíva a financie").count(),
            "Iné - Starostlivosť a pomoc": Inzerat.query.filter_by(podkategoria="Iné - Starostlivosť a pomoc").count(),
            "Iné - Krása a zdravie": Inzerat.query.filter_by(podkategoria="Iné - Krása a zdravie").count()
        }
    }


def uloz_obrazok(subor):
    if not subor or subor.filename == "":
        return None

    povolene_pripony = ["jpg", "jpeg", "png", "webp"]

    if "." not in subor.filename:
        raise ValueError("Obrázok nebol nahraný. Povolené sú iba JPG, JPEG, PNG alebo WEBP.")

    nazov = secure_filename(subor.filename)
    pripona = nazov.rsplit(".", 1)[1].lower()

    if pripona not in povolene_pripony:
        raise ValueError("Obrázok nebol nahraný. Povolené sú iba JPG, JPEG, PNG alebo WEBP.")

    cesta = os.path.join(UPLOAD_FOLDER, nazov)

    subor.save(cesta)

    try:
        obrazok = Image.open(cesta)
        sirka, vyska = obrazok.size
    except Exception:
        if os.path.exists(cesta):
            os.remove(cesta)
        raise ValueError("Obrázok nebol nahraný. Súbor nie je platný obrázok.")

    max_velkost = 5 * 1024 * 1024

    if os.path.getsize(cesta) > max_velkost:
        obrazok.close()
        os.remove(cesta)
        raise ValueError("Obrázok nebol nahraný. Maximálna veľkosť je 5 MB.")

    if sirka < 600 or vyska < 400:
        obrazok.close()
        os.remove(cesta)
        raise ValueError("Obrázok nebol nahraný. Minimálne rozmery sú 600 × 400 px.")

    max_sirka = 1000
    max_vyska = 700

    obrazok.thumbnail((max_sirka, max_vyska))

    if pripona in ["jpg", "jpeg"]:
        obrazok = obrazok.convert("RGB")

    obrazok.save(cesta, optimize=True, quality=85)
    obrazok.close()

    return nazov


def vytvor_reset_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def over_reset_token(token):
    try:
        data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return data["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def posli_reset_email(email, reset_link):

    sprava = Message(
        subject="Reset hesla - sluzby.sk",
        recipients=[email]
    )

    sprava.body = f"""
Dobrý deň,

požiadali ste o reset hesla na stránke sluzby.sk.

Kliknite na tento odkaz:

{reset_link}

Odkaz je platný 30 minút.

Ak ste o zmenu hesla nepožiadali, tento e-mail ignorujte.

Tím sluzby.sk
"""

    mail.send(sprava)


@app.route("/")
def index():
    return render_template("stranky/index.html")


@app.route("/registracia", methods=["GET", "POST"])
def registracia():
    chyba = ""
    uspech = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        terms = request.form.get("terms")

        if not username or not email or not password or not password2:
            chyba = "Vyplňte všetky povinné polia."
        elif not terms:
            chyba = "Musíte súhlasiť s podmienkami používania."
        elif password != password2:
            chyba = "Heslá sa nezhodujú."
        elif not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", password):
            chyba = "Heslo musí mať minimálne 8 znakov, jedno veľké písmeno, jedno malé písmeno a jednu číslicu."
        elif User.query.filter_by(email=email).first():
            chyba = "Používateľ s týmto e-mailom už existuje."
        else:
            novy_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password)
            )

            db.session.add(novy_user)
            db.session.commit()

            uspech = "Registrácia bola úspešná. Teraz sa môžete prihlásiť."

    return render_template("auth/registracia.html", chyba=chyba, uspech=uspech)


@app.route("/prihlasenie", methods=["GET", "POST"])
def prihlasenie():
    chyba = ""
    email = ""
    sprava = request.args.get("sprava", "")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user:
            chyba = "Používateľ s týmto e-mailom neexistuje."
        elif not check_password_hash(user.password, password):
            chyba = "Nesprávne heslo."
        else:
            session["user_id"] = user.id
            session["user_name"] = user.username
            return redirect(url_for("index"))

    return render_template("auth/prihlasenie.html", chyba=chyba, email=email, sprava=sprava)


@app.route("/google-prihlasenie")
def google_prihlasenie():
    if not google.authorized:
        return redirect(url_for("google.login"))

    response = google.get("/oauth2/v2/userinfo")

    if not response.ok:
        return redirect(url_for("prihlasenie", sprava="Prihlásenie cez Google sa nepodarilo."))

    google_data = response.json()

    email = google_data.get("email", "").strip().lower()
    google_name = google_data.get("name", "")

    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            username=google_name,
            email=email,
            password=generate_password_hash(os.urandom(24).hex())
        )

        db.session.add(user)
        db.session.commit()

    session["user_id"] = user.id
    session["user_name"] = user.username

    return redirect(url_for("index"))


@app.route("/odhlasenie")
def odhlasenie():
    session.clear()
    return redirect(url_for("index"))

@app.route("/zabudnute-heslo", methods=["GET", "POST"])
def zabudnute_heslo():

    chyba = ""
    sprava = ""

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        user = User.query.filter_by(email=email).first()

        if not user:

            chyba = "Používateľ s týmto e-mailom neexistuje."

        else:

            token = vytvor_reset_token(user.id)

            reset_link = url_for(
                "reset_hesla",
                token=token,
                _external=True
            )

            try:

                posli_reset_email(
                    email,
                    reset_link
                )

                sprava = "Resetovací odkaz bol odoslaný na váš e-mail."

            except Exception:

                chyba = (
                    "Nepodarilo sa odoslať e-mail. "
                    "Skúste to znova neskôr."
                )

    return render_template(
        "auth/zabudnute_heslo.html",
        chyba=chyba,
        sprava=sprava
    )

@app.route("/reset-hesla/<token>", methods=["GET", "POST"])
def reset_hesla(token):
    chyba = ""

    user_id = over_reset_token(token)

    if not user_id:
        return redirect(url_for("prihlasenie", sprava="Resetovací odkaz je neplatný alebo expiroval."))

    user = User.query.get(user_id)

    if not user:
        return redirect(url_for("prihlasenie", sprava="Používateľ neexistuje."))

    if request.method == "POST":
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not password or not password2:
            chyba = "Vyplňte obe polia."
        elif password != password2:
            chyba = "Heslá sa nezhodujú."
        elif not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", password):
            chyba = "Heslo musí mať minimálne 8 znakov, jedno veľké písmeno, jedno malé písmeno a jednu číslicu."
        else:
            user.password = generate_password_hash(password)
            db.session.commit()

            return redirect(url_for("prihlasenie", sprava="Heslo bolo úspešne zmenené. Prihláste sa."))

    return render_template("auth/reset_hesla.html", chyba=chyba)


@app.route("/pridat-inzerat", methods=["GET", "POST"])
def pridat_inzerat():
    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    chyba = ""
    uspech = ""

    if request.method == "POST":
        nazov = request.form.get("title", "").strip()
        kategoria = request.form.get("category", "").strip()
        podkategoria = request.form.get("subcategory", "").strip()
        cena = request.form.get("price", "").strip()
        cena_dohodou = True if request.form.get("cena_dohodou") else False
        lokalita = request.form.get("location", "").strip()
        psc = request.form.get("psc", "").strip()
        popis = request.form.get("description", "").strip()

        if not nazov or not kategoria or not lokalita or not popis:
            chyba = "Vyplňte všetky povinné polia."
        elif not cena and not cena_dohodou:
            chyba = "Zadajte cenu alebo označte možnosť Cena dohodou."
        else:
            cena_float = float(cena) if cena else None

            novy_inzerat = Inzerat(
                nazov=nazov,
                kategoria=kategoria,
                podkategoria=podkategoria,
                cena=cena_float,
                cena_dohodou=cena_dohodou,
                lokalita=lokalita,
                psc=psc,
                popis=popis,
                obrazok=uloz_obrazok(request.files.get("photo")),
                obrazok_2=uloz_obrazok(request.files.get("photo2")),
                obrazok_3=uloz_obrazok(request.files.get("photo3")),
                user_id=session["user_id"]
            )

            db.session.add(novy_inzerat)
            db.session.commit()

            return redirect(url_for("detail_inzeratu", inzerat_id=novy_inzerat.id))

    return render_template("inzeraty/pridat_inzerat.html", chyba=chyba, uspech=uspech)


@app.route("/moje-inzeraty")
def moje_inzeraty():
    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    inzeraty = Inzerat.query.filter_by(
        user_id=session["user_id"]
    ).order_by(
        Inzerat.datum_pridania.desc()
    ).all()

    return render_template("inzeraty/moje_inzeraty.html", inzeraty=inzeraty)

@app.route("/moje-konto")
def moje_konto():

    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    user = User.query.get(session["user_id"])

    pocet_inzeratov = Inzerat.query.filter_by(
        user_id=user.id
    ).count()

    return render_template(
        "auth/moje_konto.html",
        user=user,
        pocet_inzeratov=pocet_inzeratov
    )

@app.route("/zmenit-heslo", methods=["GET", "POST"])
def zmenit_heslo():

    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    user = User.query.get(session["user_id"])

    chyba = ""
    sprava = ""

    if request.method == "POST":

        stare_heslo = request.form.get("stare_heslo", "")
        nove_heslo = request.form.get("nove_heslo", "")
        nove_heslo2 = request.form.get("nove_heslo2", "")

        if not check_password_hash(user.password, stare_heslo):

            chyba = "Aktuálne heslo nie je správne."

        elif nove_heslo != nove_heslo2:

            chyba = "Nové heslá sa nezhodujú."

        elif not re.match(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$",
            nove_heslo
        ):

            chyba = (
                "Heslo musí mať minimálne 8 znakov, "
                "jedno veľké písmeno, jedno malé písmeno "
                "a jednu číslicu."
            )

        else:

            user.password = generate_password_hash(nove_heslo)

            db.session.commit()

            sprava = "Heslo bolo úspešne zmenené."

    return render_template(
        "auth/zmenit_heslo.html",
        chyba=chyba,
        sprava=sprava
    )

@app.route("/zrusit-konto", methods=["POST"])
def zrusit_konto():

    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    user_id = session["user_id"]

    Inzerat.query.filter_by(user_id=user_id).delete()

    user = User.query.get(user_id)

    if user:
        db.session.delete(user)

    db.session.commit()
    session.clear()

    return redirect(url_for("index"))


@app.route("/inzerat/<int:inzerat_id>")
def detail_inzeratu(inzerat_id):
    inzerat = Inzerat.query.get_or_404(inzerat_id)
    poskytovatel = User.query.get(inzerat.user_id)

    hodnotenia_db = Hodnotenie.query.filter_by(inzerat_id=inzerat.id).all()
    pocet_hodnoteni = len(hodnotenia_db)

    if pocet_hodnoteni > 0:
        priemer_hodnotenia = round(
            sum(h.hodnotenie for h in hodnotenia_db) / pocet_hodnoteni,
            1
        )
    else:
        priemer_hodnotenia = None

    hodnotenia = []

    for hodnotenie in hodnotenia_db:
        autor = User.query.get(hodnotenie.autor_user_id)
        hodnotenia.append((hodnotenie, autor))

    recenzie_db = Recenzia.query.filter_by(
        inzerat_id=inzerat.id
    ).order_by(
        Recenzia.datum.desc()
    ).all()

    recenzie = []

    for recenzia in recenzie_db:
        autor = User.query.get(recenzia.autor_user_id)
        recenzie.append((recenzia, autor))

    dalsie_inzeraty = Inzerat.query.filter(
        Inzerat.user_id == inzerat.user_id,
        Inzerat.id != inzerat.id
    ).limit(3).all()

    pocet_inzeratov = Inzerat.query.filter_by(user_id=inzerat.user_id).count()

    return render_template(
        "inzeraty/detail_inzeratu.html",
        inzerat=inzerat,
        poskytovatel=poskytovatel,
        priemer_hodnotenia=priemer_hodnotenia,
        pocet_hodnoteni=pocet_hodnoteni,
        hodnotenia=hodnotenia,
        recenzie=recenzie,
        dalsie_inzeraty=dalsie_inzeraty,
        pocet_inzeratov=pocet_inzeratov
    )

@app.route("/poskytovatel/<int:user_id>/inzeraty")
def inzeraty_poskytovatela(user_id):
    poskytovatel = User.query.get_or_404(user_id)

    inzeraty = Inzerat.query.filter_by(
        user_id=user_id
    ).order_by(
        Inzerat.datum_pridania.desc()
    ).all()

    return render_template(
        "inzeraty/inzeraty_poskytovatela.html",
        poskytovatel=poskytovatel,
        inzeraty=inzeraty
    )

@app.route("/upravit-inzerat/<int:inzerat_id>", methods=["GET", "POST"])
def upravit_inzerat(inzerat_id):
    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    inzerat = Inzerat.query.get_or_404(inzerat_id)

    if inzerat.user_id != session["user_id"]:
        return redirect(url_for("moje_inzeraty"))

    chyba = ""

    if request.method == "POST":
        nazov = request.form.get("title", "").strip()
        kategoria = request.form.get("category", "").strip()
        podkategoria = request.form.get("subcategory", "").strip()
        cena = request.form.get("price", "").strip()
        lokalita = request.form.get("location", "").strip()
        psc = request.form.get("psc", "").strip()
        popis = request.form.get("description", "").strip()

        if not nazov or not kategoria or not lokalita or not popis:
            chyba = "Vyplňte všetky povinné polia."
        else:
            try:
                inzerat.nazov = nazov
                inzerat.kategoria = kategoria
                inzerat.podkategoria = podkategoria

                if cena and cena != "None":
                    inzerat.cena = float(cena.replace(",", "."))
                else:
                    inzerat.cena = None

                inzerat.lokalita = lokalita
                inzerat.psc = psc
                inzerat.popis = popis

                foto1 = uloz_obrazok(request.files.get("photo"))
                foto2 = uloz_obrazok(request.files.get("photo2"))
                foto3 = uloz_obrazok(request.files.get("photo3"))

                if foto1:
                    inzerat.obrazok = foto1

                if foto2:
                    inzerat.obrazok_2 = foto2

                if foto3:
                    inzerat.obrazok_3 = foto3

                db.session.commit()

                return redirect(
                    url_for(
                        "detail_inzeratu",
                        inzerat_id=inzerat.id
                    )
                )

            except ValueError as e:
                chyba = str(e)

    return render_template(
        "inzeraty/upravit_inzerat.html",
        inzerat=inzerat,
        chyba=chyba
    )

@app.route("/zmazat-inzerat/<int:inzerat_id>", methods=["POST"])
def zmazat_inzerat(inzerat_id):
    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    inzerat = Inzerat.query.get_or_404(inzerat_id)

    if inzerat.user_id == session["user_id"]:
        Hodnotenie.query.filter_by(inzerat_id=inzerat.id).delete()
        Recenzia.query.filter_by(inzerat_id=inzerat.id).delete()
        db.session.delete(inzerat)
        db.session.commit()

    return redirect(url_for("moje_inzeraty"))


@app.route("/kontaktovat-poskytovatela/<int:inzerat_id>", methods=["GET", "POST"])
def kontaktovat_poskytovatela(inzerat_id):
    inzerat = Inzerat.query.get_or_404(inzerat_id)
    poskytovatel = User.query.get(inzerat.user_id)

    chyba = ""
    uspech = ""

    if request.method == "POST":
        meno = request.form.get("meno", "").strip()
        email = request.form.get("email", "").strip()
        sprava_text = request.form.get("sprava", "").strip()

        if not meno or not email or not sprava_text:
            chyba = "Vyplňte všetky povinné údaje."

        elif not poskytovatel or not poskytovatel.email:
            chyba = "Poskytovateľ nemá uložený e-mail."

        else:
            sprava_email = Message(
                subject=f"Nová správa k inzerátu: {inzerat.nazov}",
                recipients=[poskytovatel.email]
            )

            sprava_email.body = f"""
Dobrý deň,

prišla vám nová správa k inzerátu:
{inzerat.nazov}

Meno odosielateľa:
{meno}

E-mail odosielateľa:
{email}

Správa:
{sprava_text}

"""

            try:
                mail.send(sprava_email)
                uspech = "Správa bola odoslaná poskytovateľovi."
            except Exception as e:
                chyba = f"E-mail sa nepodarilo odoslať: {e}"

    return render_template(
        "inzeraty/kontaktovat_poskytovatela.html",
        inzerat=inzerat,
        poskytovatel=poskytovatel,
        chyba=chyba,
        uspech=uspech
    )

@app.route("/pridat-hodnotenie/<int:inzerat_id>", methods=["POST"])
def pridat_hodnotenie(inzerat_id):
    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    inzerat = Inzerat.query.get_or_404(inzerat_id)
    autor_user_id = session["user_id"]

    if inzerat.user_id == autor_user_id:
        return redirect(url_for("detail_inzeratu", inzerat_id=inzerat.id))

    hodnota = request.form.get("hodnotenie")

    if not hodnota:
        return redirect(url_for("detail_inzeratu", inzerat_id=inzerat.id))

    hodnota = int(hodnota)

    if hodnota < 1 or hodnota > 5:
        return redirect(url_for("detail_inzeratu", inzerat_id=inzerat.id))

    existujuce_hodnotenie = Hodnotenie.query.filter_by(
        autor_user_id=autor_user_id,
        inzerat_id=inzerat.id
    ).first()

    if existujuce_hodnotenie:
        existujuce_hodnotenie.hodnotenie = hodnota
        existujuce_hodnotenie.datum = datetime.utcnow()
    else:
        nove_hodnotenie = Hodnotenie(
            hodnotenie=hodnota,
            autor_user_id=autor_user_id,
            hodnoteny_user_id=inzerat.user_id,
            inzerat_id=inzerat.id
        )

        db.session.add(nove_hodnotenie)

    db.session.commit()

    return redirect(url_for("detail_inzeratu", inzerat_id=inzerat.id))


@app.route("/pridat-recenzie/<int:inzerat_id>", methods=["POST"])
def pridat_recenzie(inzerat_id):
    if not session.get("user_id"):
        return redirect(url_for("prihlasenie"))

    inzerat = Inzerat.query.get_or_404(inzerat_id)
    text = request.form.get("text", "").strip()

    if text and inzerat.user_id != session["user_id"]:
        nova = Recenzia(
            text=text,
            autor_user_id=session["user_id"],
            inzerat_id=inzerat.id
        )

        db.session.add(nova)
        db.session.commit()

    return redirect(url_for("detail_inzeratu", inzerat_id=inzerat.id))


def zobraz_kategoriu(nazov_kategorie, sablona):
    query = Inzerat.query.filter_by(
        kategoria=nazov_kategorie
    )

    query, price_min, price_max, location, sort = filtruj_inzeraty(query)

    inzeraty = query.all()

    return render_template(
        sablona,
        inzeraty=inzeraty,
        price_min=price_min,
        price_max=price_max,
        location=location,
        sort=sort
    )

def filtruj_inzeraty(query):

    price_min = request.args.get("price_min", "").strip()
    price_max = request.args.get("price_max", "").strip()
    location = request.args.get("location", "").strip()
    sort = request.args.get("sort", "newest")

    if location:
        hladana_lokalita = f"%{location}%"

        query = query.filter(
            db.or_(
                Inzerat.lokalita.ilike(hladana_lokalita),
                Inzerat.psc.ilike(hladana_lokalita)
            )
        )

    if price_min:
        query = query.filter(Inzerat.cena_dohodou == False)
        query = query.filter(Inzerat.cena >= float(price_min))

    if price_max:
        query = query.filter(Inzerat.cena_dohodou == False)
        query = query.filter(Inzerat.cena <= float(price_max))

    if sort == "oldest":
        query = query.order_by(Inzerat.datum_pridania.asc())
    else:
        query = query.order_by(Inzerat.datum_pridania.desc())

    return query, price_min, price_max, location, sort

@app.route("/dom-a-byvanie")
def dom_a_byvanie():
    return zobraz_kategoriu("Dom a bývanie", "kategorie/dom_a_byvanie.html")


@app.route("/zahrada-a-exterier")
def zahrada_a_exterier():
    return zobraz_kategoriu("Záhrada a exteriér", "kategorie/zahrada_a_exterier.html")


@app.route("/stahovanie-doprava")
def stahovanie_doprava():
    return zobraz_kategoriu("Sťahovanie a doprava", "kategorie/stahovanie_doprava.html")


@app.route("/doucovanie")
def doucovanie():
    return zobraz_kategoriu("Doučovanie", "kategorie/doucovanie.html")


@app.route("/online-sluzby")
def online_sluzby():
    return zobraz_kategoriu("Online služby", "kategorie/online_sluzby.html")


@app.route("/administrativa-a-financie")
def administrativa_a_financie():
    return zobraz_kategoriu("Administratíva a financie", "kategorie/administrativa_a_financie.html")


@app.route("/starostlivost-a-pomoc")
def starostlivost_a_pomoc():
    return zobraz_kategoriu("Starostlivosť a pomoc", "kategorie/starostlivost_a_pomoc.html")


@app.route("/krasa-a-zdravie")
def krasa_a_zdravie():
    return zobraz_kategoriu("Krása a zdravie", "kategorie/krasa_a_zdravie.html")


@app.route("/fotografovanie")
def fotografovanie():
    return zobraz_kategoriu("Fotografovanie", "kategorie/fotografovanie.html")


@app.route("/preklady")
def preklady():
    return zobraz_kategoriu("Preklady", "kategorie/preklady.html")


@app.route("/podkategoria/<nazov>")
def podkategoria(nazov):
    query = Inzerat.query.filter_by(
        podkategoria=nazov
    )

    query, price_min, price_max, location, sort = filtruj_inzeraty(query)

    inzeraty = query.all()

    return render_template(
        "kategorie/podkategoria.html",
        nazov=nazov,
        inzeraty=inzeraty,
        price_min=price_min,
        price_max=price_max,
        location=location,
        sort=sort
    )


@app.route("/vyhladavanie")
def vyhladavanie():
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    price_min = request.args.get("price_min", "").strip()
    price_max = request.args.get("price_max", "").strip()
    sort = request.args.get("sort", "newest").strip()

    query = Inzerat.query

    if q:
        hladane = f"%{q}%"
        query = query.filter(
            db.or_(
                Inzerat.nazov.ilike(hladane),
                Inzerat.popis.ilike(hladane),
                Inzerat.kategoria.ilike(hladane),
                Inzerat.podkategoria.ilike(hladane)
            )
        )

    if location:
        hladana_lokalita = f"%{location}%"
        query = query.filter(
            db.or_(
                Inzerat.lokalita.ilike(hladana_lokalita),
                Inzerat.psc.ilike(hladana_lokalita)
            )
        )

    if price_min:
        query = query.filter(Inzerat.cena_dohodou == False)
        query = query.filter(Inzerat.cena >= float(price_min.replace(",", ".")))

    if price_max:
        query = query.filter(Inzerat.cena_dohodou == False)
        query = query.filter(Inzerat.cena <= float(price_max.replace(",", ".")))

    if sort == "oldest":
        query = query.order_by(Inzerat.datum_pridania.asc())
    else:
        query = query.order_by(Inzerat.datum_pridania.desc())

    vysledky = query.all()

    return render_template(
        "vyhladavanie.html",
        vysledky=vysledky,
        q=q,
        location=location,
        price_min=price_min,
        price_max=price_max,
        sort=sort
    )

@app.route("/o-nas")
def o_nas():
    return render_template("stranky/o_nas.html")


@app.route("/kontakt")
def kontakt():
    return render_template("stranky/kontakt.html")


@app.route("/podmienky-pouzivania")
def podmienky_pouzivania():
    return render_template("stranky/podmienky_pouzivania.html")


@app.route("/ochrana-osobnych-udajov")
def ochrana_osobnych_udajov():
    return render_template("stranky/ochrana_osobnych_udajov.html")

if __name__ == "__main__":
    app.run(debug=True)