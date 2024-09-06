from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, Email, Optional
from flask_paginate import Pagination, get_page_parameter
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    quality = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    image_link = db.Column(db.String(255), nullable=True)

class SupportMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<SupportMessage {self.name}>'

class LoginForm(FlaskForm):
    username = StringField('نام کاربری', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('رمز عبور', validators=[DataRequired()])
    submit = SubmitField('ورود')

class MovieForm(FlaskForm):
    title = StringField('نام فیلم', validators=[DataRequired()])
    link = StringField('لینک دانلود', validators=[DataRequired()])
    description = TextAreaField('خلاصه داستان', validators=[DataRequired()])
    language = StringField('زبان', validators=[DataRequired()])
    size = StringField('حجم', validators=[DataRequired()])
    quality = StringField('کیفیت', validators=[DataRequired()])
    duration = StringField('مدت زمان', validators=[DataRequired()])
    image_link = StringField('لینک عکس', validators=[DataRequired()])
    submit = SubmitField('ثبت')

class SupportForm(FlaskForm):
    name = StringField('نام', validators=[DataRequired(), Length(min=1, max=150)])
    email = StringField('ایمیل', validators=[DataRequired(), Email(), Length(min=6, max=150)])
    message = TextAreaField('پیام', validators=[DataRequired()])
    submit = SubmitField('ارسال')

class SearchForm(FlaskForm):
    search = StringField('جستجو:', validators=[DataRequired()])
    submit = SubmitField('جستجو')

class AdvancedSearchForm(FlaskForm):
    title = StringField('عنوان فیلم', validators=[Optional()])
    language = StringField('زبان فیلم', validators=[Optional()])
    quality = StringField('کیفیت فیلم', validators=[Optional()])
    duration = StringField('مدت زمان فیلم', validators=[Optional()])
    submit = SubmitField('جستجو پیشرفته')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('لطفاً برای دسترسی به این صفحه وارد شوید.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and check_password_hash(admin.password, form.password.data):
            session['admin_id'] = admin.id
            flash('ورود موفقیت آمیز بود!', 'success')
            return redirect(url_for('admin_movies'))
        else:
            flash('نام کاربری یا رمز عبور نامعتبر است', 'danger')
    return render_template('login.html', form=form)

def limit_description(description):
    words = description.split()
    if len(words) > 30:
        return ' '.join(words[:30]) + ' ...'
    return description

@app.route('/')
def index():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    movies = Movie.query.paginate(page=page, per_page=per_page)
    pagination = Pagination(page=page, total=movies.total, record_name='movies', per_page=per_page)
    search_form = SearchForm()
    return render_template('index.html', movies=movies.items, pagination=pagination, limit_description=limit_description, search_form=search_form)

@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    if form.validate_on_submit():
        search_query = form.search.data.strip()
        movies = Movie.query.filter(Movie.title.contains(search_query)).all()
        return render_template('search_results.html', movies=movies, search_query=search_query)
    
    return redirect(url_for('index'))

@app.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    form = AdvancedSearchForm()
    if form.validate_on_submit():
        title = form.title.data
        language = form.language.data
        quality = form.quality.data
        duration = form.duration.data
        movies = Movie.query.filter(
            (Movie.title.contains(title) if title else True),
            (Movie.language == language) if language else True,
            (Movie.quality == quality) if quality else True,
            (Movie.duration == duration) if duration else True
        ).all()
        return render_template('search_results.html', movies=movies, search_query='Advanced Search')
    
    return render_template('advanced_search.html', form=form)

@app.route('/support', methods=['GET', 'POST'])
def support():
    form = SupportForm()
    if form.validate_on_submit():
        new_message = SupportMessage(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data
        )
        db.session.add(new_message)
        db.session.commit()
        flash('پیام شما با موفقیت ارسال شد!', 'success')
        return redirect(url_for('support'))
    return render_template('support.html', form=form)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    form = MovieForm()
    if form.validate_on_submit():
        new_movie = Movie(
            title=form.title.data,
            link=form.link.data,
            description=form.description.data,
            language=form.language.data,
            size=form.size.data,
            quality=form.quality.data,
            duration=form.duration.data,
            image_link=form.image_link.data
        )
        db.session.add(new_movie)
        db.session.commit()
        flash('فیلم با موفقیت اضافه شد!', 'success')
        return redirect(url_for('index'))
    return render_template('admin.html', form=form)

@app.route('/admin/movies')
@login_required
def admin_movies():
    movies = Movie.query.all()
    return render_template('admin_movies.html', movies=movies)

@app.route('/admin/users')
@login_required
def admin_users():
    admins = Admin.query.all()
    return render_template('admin_users.html', admins=admins)

@app.route('/delete_movie/<int:movie_id>')
@login_required
def delete_movie(movie_id):
    movie = Movie.query.get(movie_id)
    if not movie:
        flash('فیلم پیدا نشد!', 'danger')
        return redirect(url_for('admin_movies'))

    db.session.delete(movie)
    db.session.commit()
    flash('فیلم با موفقیت حذف شد!', 'success')
    return redirect(url_for('admin_movies'))

@app.route('/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    form = MovieForm(obj=movie)
    if form.validate_on_submit():
        form.populate_obj(movie)
        db.session.commit()
        flash('فیلم با موفقیت ویرایش شد!', 'success')
        return redirect(url_for('index'))
    return render_template('admin.html', form=form)

@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    flash('شما با موفقیت خارج شدید', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
