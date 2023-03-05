from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

# kullanıcı giriş kontrolü için decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session: # eğer logged_in diyer bir anahtar kelime varsa true dönücektir
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın...","danger")
            return redirect(url_for("login"))

    return decorated_function

# Kullanıcı kayıt formu
class RegisterForm(Form):
    # validators sınırlandırmalar için kullanılıyor mesela boş geçilemez ya da 5 harfden az olamaz
    name = StringField("İsim Soyisim",validators=[validators.length(min=4,max=25)]) # parantezin içine birden fazla sınırlandırma yazabilirsin
    userName = StringField("Kullanıcı Adı:",validators=[validators.length(min=5,max=35)])
    email = StringField("email",validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz...")]) # burda gerçekten bir email girilip girilmediği kontrol edilir.
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message = "Lüfen bir parola belirleyiniz..."),
        validators.EqualTo(fieldname="confirm",message="parolalarınız uyuşmuyor") # tekrar girilen şifreyle aynı değilse hata vericek
    ])
    confirm = PasswordField("Parolanızı Doğrula:")

class LoginForm(Form):
    userName = StringField("kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key = "ybblog" # flash  yazılarının çalışması için gerekli. Ama nedenini tam anlamadım.

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor" # bu kod sayesinde alınan veriler bir dictinory tipinde geliyor.

mysql = MySQL(app)


@app.route("/")
def index():
    number = [1,2,3,4,5]
    return render_template("index.html",numbers = number)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method  == "POST" and form.validate(): # validate bir sıkıntı yoksa true döner. Kısaca yukarıda belirlediğimiz koşulları sağlıyorsa true döner.
        name = form.name.data
        userName = form.userName.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data) # parola şifrelenerek kaydedilicek.

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name,userName,email,password) VALUES(%s,%s,%s,%s)"
        
        cursor.execute(sorgu,(name,userName,email,password))
        mysql.connection.commit()
        cursor.close()

        flash("Başarıyla Kayıt Oldunuz...","success")

        return redirect(url_for("login")) 
    else:
        return render_template("register.html",form = form)

# Login işlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    
    form = LoginForm(request.form)
    if request.method == "POST":
        
        userName = form.userName.data
        passwordEntered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "Select * From users where userName = %s"

        # eğer eşleşme yoksa resultun değeri 0 olucaktır.
        result = cursor.execute(sorgu,(userName,)) # sonuna vürgül konulmasının nedeni: tek elemanlı demet oluşturmak için gerekli.
        
        if result > 0:
            data = cursor.fetchone() # bu kod sayesinde kullanıcının bütün bilgilerini bir dict. olarak alıyorum.
            real_password = data["password"]
            if sha256_crypt.verify(passwordEntered,real_password): # şifreler databasede şifrelendiğinden bu method sayesinde kontrol yapılabiliiyor.
                flash("başarıla giriş yaptınızz...","success")

                session["logged_in"] = True
                session["userName"] = userName

                return redirect(url_for("index"))
            else:
                flash("parolanızı yanlış girdiniz...","danger")
                return redirect(url_for("login"))


        else:
            flash("Böyle bir kullanıcı bulunmuyor...","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form = form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu,(session["userName"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

    

# makale ekleme
@app.route("/addarticle", methods = ["GET","POST"])
def addarticle():

    form = ArticleForm(request.form)

    if request.method =="POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "Insert into  articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["userName"],content))

        mysql.connection.commit()

        cursor.close()

        flash("Makale başarıyla eklendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)

class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale içeriği",validators=[validators.Length(min=10)])

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

# detay sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where id = %s"

    resault = cursor.execute(sorgu,(id,))

    if resault > 0:
        article  = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["userName"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"

        cursor.execute(sorgu2,(id,))

        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug = True)