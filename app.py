from flask import Flask,render_template,flash,request,redirect,url_for
from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField,PasswordField,BooleanField,ValidationError,TextAreaField
from flask_wtf.file import FileField
from wtforms.validators import DataRequired,EqualTo,Length,InputRequired
from wtforms.widgets import TextArea
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_ckeditor import CKEditor,CKEditorField
from werkzeug.utils import secure_filename
import uuid as uuid
import os



app = Flask(__name__)
ckeditor = CKEditor(app)

#Veritabanı

app.config['SECRET_KEY'] = "secretive"
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:12345@localhost/users"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
migrate = Migrate(app, db)

#Oturum Ayarları
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
@login_manager.user_loader
def load_user(user_id):
	return Users.query.get(int(user_id))

#Hikaye Ekleme Sayfası
@app.route('/addessay', methods=["GET","POST"])
@login_required
def addessay():
	form = EssayForm()
	if request.method == "POST":
		author = current_user.id
		essay = Essays(title = form.title.data, author_id = author, content = form.content.data)	
		#Form Temizleme
		form.title.data = ''
		form.content.data = ''
		#Database'e Ekle
		db.session.add(essay)
		db.session.commit()
		flash("Yazınız Başarıyla Kaydedildi ve Yayınlandı!")
	return render_template("addessay.html",form=form)

#Kayıt Sayfası
@app.route('/register', methods = ['GET','POST'])
def register():
	form = UserForm()
	if request.method == "POST":
		user = Users.query.filter_by(email = form.email.data).first()
		if user is None:
			#Parola Şifreleme
			hash_pw = generate_password_hash(form.password_hash.data,"sha256")
			user = Users(name = form.name.data,username= form.username.data, email= form.email.data, password_hash=hash_pw)
			db.session.add(user)
			db.session.commit()
		name = form.name.data
		form.name.data = ''
		form.email.data = ''
		form.password_hash.data = ''
		flash("Kullanıcı Başarıyla Kaydedildi!")
		return redirect(url_for('login'))

	return render_template('register.html',form = form)

#Yazı Formu
class EssayForm(FlaskForm):
	title = StringField("Başlık",validators=[DataRequired()])
	content = CKEditorField("Yazı Alanı",validators=[DataRequired()])
	submit = SubmitField("Kaydet ve Yayınla")

#Kullanıcı Formu
class UserForm(FlaskForm):
	name = StringField("İsim Soyisim",validators=[DataRequired()])
	username = StringField("Kullanıcı Adı",validators=[DataRequired()])
	email = StringField("Email",validators=[DataRequired()])
	about_author = StringField("Hakkınızda",validators=[DataRequired()])
	password_hash = PasswordField("Parola",validators=[DataRequired(),EqualTo("password_hash2")])
	password_hash2 = PasswordField("Parola Doğrula",validators=[DataRequired()])
	profile_pic = FileField("Profil Resmi")
	submit = SubmitField("Kayıt")

#Kullanıcı Giriş Formu
class LoginForm(FlaskForm):
	username = StringField("Kullanıcı Adı",validators=[DataRequired()])
	password = PasswordField("Parola",validators=[DataRequired()])
	submit = SubmitField("Giriş")

#Yorum Formu
class CommentForm(FlaskForm):
	text = StringField("Yorumunuz",validators=[InputRequired()])
	submit = SubmitField("Gönder")

#Kullanıcı Modeli
class Users(db.Model,UserMixin):
	id = db.Column(db.Integer, primary_key = True)
	name = db.Column(db.String(200), nullable = False)
	username = db.Column(db.String(20),nullable = False, unique = True)
	email = db.Column(db.String(120), nullable = False, unique = True)
	about_author = db.Column(db.Text(), nullable = True)
	date_added = db.Column(db.DateTime, default = datetime.utcnow)
	profile_pic = db.Column(db.String(200), nullable=True)
	#Parola Şifreleme
	password_hash = db.Column(db.String(120))
	essayss= db.relationship('Essays', backref = 'author')
	comments= db.relationship('Comment', backref = 'author')

	@property
	def password(self,password):
		self.password_hash = generate_password_hash(password)
	def verify_password(self,password):
		return check_password_hash(self.password_hash,password)
	def __repr__(self):
		return '<Name %r>' % self.name

#Yazı Modeli
class Essays(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	title = db.Column(db.String(50))
	content = db.Column(db.Text(), nullable= False)
	date_posted = db.Column(db.DateTime, default = datetime.utcnow)
	#Foreign Key
	author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	comments= db.relationship('Comment', backref = 'post')

#Yorum Modeli
class Comment(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	text = db.Column(db.String(200), nullable=False)
	date_created= db.Column(db.DateTime, default=datetime.utcnow)
	#Foreign Keys
	author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	post_id = db.Column(db.Integer,db.ForeignKey('essays.id'))


#Kullanıcı Güncelleme
@app.route('/update/<int:id>', methods = ["GET","POST"])
@login_required
def update(id):
	form = UserForm()
	name_to_update = Users.query.get_or_404(id)
	form.name.data = name_to_update.name
	form.username.data = name_to_update.username
	form.email.data = name_to_update.email
	form.about_author.data = name_to_update.about_author
	if request.method == "POST":
		name_to_update.name = request.form['name']
		name_to_update.username = request.form['username']
		name_to_update.email = request.form['email']
		name_to_update.about_author = request.form['about_author']
		name_to_update.password_hash = generate_password_hash(request.form['password_hash'],"sha256")

		#Profil Fotusunun Varlığını Kontrol Et
		if request.files['profile_pic']:
			name_to_update.profile_pic = request.files['profile_pic']
			#Profil Fotusun İsmini Çekme
			pic_filename = secure_filename(name_to_update.profile_pic.filename)
			# UUID Oluştur
			pic_name = str(uuid.uuid1()) + "_" + pic_filename
			
			#Profil Fotosunu Kaydet
			name_to_update.profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'],pic_name))
			#String e Çevir ve Yükle
			#saver = request.files['profile_pic']
			name_to_update.profile_pic = pic_name

			try:
				db.session.commit()
				#saver.name_to_update.profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'],pic_name))
				flash("Kullanıcı Başarıyla Güncellendi!")
				return render_template("dashboard.html",form=form,name_to_update=name_to_update,id =id)
			except:
				flash("Bir Hata Oluştu! Lütfen Tekrar Deneyiniz!")
				return render_template("update.html",form=form,name_to_update=name_to_update,id =id)
		else:
			db.session.commit()
			flash("Kullanıcı Başarıyla Güncellendi!")
			flash("Lütfen Profil Fotoğrafınızı Yükleyyiniz!")
			return render_template("dashboard.html",form=form,name_to_update=name_to_update,id =id)
	else:
		flash("Lütfen Formu Doldurunuz!")
		return render_template("update.html",form=form,name_to_update=name_to_update,id =id)

#Kullanıcı Girişi 
@app.route('/login',methods=["GET","POST"])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = Users.query.filter_by(username=form.username.data).first()
		if user:
			#Şifrelenmiş Parola Kontrolü
			if check_password_hash(user.password_hash,form.password.data):
				login_user(user)
				flash('Kullanıcı Başarıyla Giriş Yaptı!')
				return render_template("dashboard.html")
			else:
				flash('Hatalı Parola Girdiniz! Lütfen Tekrar Deneyiniz!')
		else:
			flash('Böyle Bir Kullanıcı Bulunmamaktadır! Lütfen Tekrar Deneyiniz!')
	return render_template("login.html",form=form)

#Kullanıcı Profil Sayfası
@app.route('/dashboard/<int:id>',methods=["GET","POST"])
@login_required
def dashboard(id):
	posts = Essays.query.order_by(Essays.author_id)
	return render_template("dashboard.html", posts = posts)

#Kullanıcı Silme
@app.route('/delete/<int:id>')
@login_required
def delete(id):
	if id == current_user.id or id==21:
		form = UserForm()
		user_to_delete = Users.query.get_or_404(id)
		try:
			db.session.delete(user_to_delete)
			db.session.commit()
			flash("Kullanıcı Başarıyla Silindi!")
			return render_template("index.html")
		except:
			flash("Bir Sorunla Karşılaşıldı! Lütfen Tekrar Deneyiniz!")
			return render_template("register.html",form=form)
	else:
		flash("Üzgünüm, Bu Kullanıcıyı Silemezsiniz!")
		return redirect(url_for('dashboard',id=id))

#Kullanıcı Çıkış
@app.route('/logout',methods=["GET","POST"])
@login_required
def logout():
	logout_user()
	flash("Kullanıcı Başarıyla Çıkış Yaptı!")
	return render_template("index.html")

#Tüm Yazıların Sayfası
@app.route('/wall')
def wall():
	#Database den Tüm Yazıları Çek
	posts = Essays.query.order_by(Essays.date_posted)
	return render_template("wall.html", posts = posts)

#Tek Yazı Görüntüleme
@app.route('/wall/<int:id>')
def viewessay(id):
	post = Essays.query.get_or_404(id)
	form2 = CommentForm()

	return render_template('viewessay.html', post = post, form2=form2)

#Yazı Güncelleme
@app.route('/wall/edit/<int:id>', methods=["GET","POST"])
@login_required
def editessay(id):
	post = Essays.query.get_or_404(id)
	form = EssayForm()
	if request.method == "POST":
		post.title = form.title.data
		post.content = form.content.data
		#Database Güncelleme
		db.session.add(post)
		db.session.commit()
		flash("Yazı Başarıyla Güncellendi!")
		return redirect(url_for('viewessay', id = post.id))
	form.title.data = post.title
	form.content.data = post.content
	return render_template('editessay.html',form=form)

#Yazı Silme
@app.route('/wall/delete/<int:id>')
@login_required
def deleteessay(id):
	post_to_delete = Essays.query.get_or_404(id)
	#id = current_user.id
	posts = Essays.query.order_by(Essays.date_posted)
	if id == post_to_delete.id:
		try:
			db.session.delete(post_to_delete)
			db.session.commit()
			flash("Yazı Başarıyla Silindi!")
			return render_template('wall.html',posts = posts)
		except:
			flash("Bir Problemle Karşılaşıldı! Lütfen Tekrar Deneyiniz!")
			posts = Essays.query.order_by(Essays.date_posted)
			return render_template('wall.html',posts=posts)
	else:
		flash("Bu Yazıyı Silmek İçin Yetkiniz Yoktur!")
		return render_template('wall.html',posts=posts)

#Yorum Ekleme
@app.route('/create_comment/<post_id>' , methods=["POST"])
@login_required
def create_comment(post_id):
	text = request.form.get('text')
	if not text:
		flash('Lütfen Yorum Yapınız!')
	else:
		post = Essays.query.filter_by(id = post_id)
		if post:
			comment = Comment(text=text,author=current_user,post_id=post_id)
			db.session.add(comment)
			db.session.commit()
		else:
			flash('Böyle Bir Yazı Bulunmamaktadır!')

	return redirect(url_for('viewessay',id=post_id))

#Yorum Sil
@app.route('/deletecomment/<comment_id>')
@login_required
def deletecomment(comment_id):
	comment = Comment.query.filter_by(id=comment_id).first()
	if not comment:
		flash('Böyle Bir Yorum Bulunmamaktadır!')
	else:
		db.session.delete(comment)
		db.session.commit()

	return redirect(url_for('wall'))

#Yönetici Sayfası
@app.route('/admin',methods=["GET","POST"])
@login_required
def admin():
	id = current_user.id
	registered_users = Users.query.order_by(Users.date_added)
	if id == 21:
		return render_template('admin.html',registered_users=registered_users)
	else:
		flash('Üzgünüm Bu Sayfaya Erişebilmek için Yönetici Yetkiniz Olmalıdır!')
		return redirect(url_for('index'))

#Ana Sayfa
@app.route('/')
def index():
	return render_template("index.html")