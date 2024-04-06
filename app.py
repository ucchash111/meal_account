from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
from dateutil.relativedelta import relativedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contributions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Add a route for admin login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        # Simple check, in real-world scenario use hashed passwords
        if username == "admin":
            admin = Admin.query.filter_by(username=username).first()
            if not admin:
                admin = Admin(username=username)
                db.session.add(admin)
                db.session.commit()
            login_user(admin)
            return redirect(url_for('admin_panel'))
    return render_template('admin_login.html')

# Add a logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete/<int:contribution_id>')
@login_required
def delete_contribution(contribution_id):
    contribution = Contribution.query.get_or_404(contribution_id)
    db.session.delete(contribution)
    db.session.commit()
    return redirect(url_for('admin_panel'))

# Add admin_panel route
@app.route('/admin/panel')
@login_required
def admin_panel():
    contributions = Contribution.query.all()
    return render_template('admin_panel.html', contributions=contributions)

class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month_year = db.Column(db.String(7), nullable=False)
    date = db.Column(db.Date, nullable=False)  # Store the exact date of contribution
    details = db.Column(db.Text, nullable=True)  # Optional field for additional details

    def __repr__(self):
        return f"<Contribution {self.name}, {self.amount}, {self.date}, Details: {self.details}>"

with app.app_context():
    db.create_all()

def get_last_month_date():
    today = datetime.now()
    first = today.replace(day=1)
    last_month = first - timedelta(days=1)
    return last_month.strftime('%m-%Y')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        amount = request.form['amount']
        details = request.form.get('details', '')  # Collect details from the form, default to empty string if not present
        contribution_date = datetime.now().date()
        month_year = contribution_date.strftime('%m-%Y')
        new_contribution = Contribution(
            name=name,
            amount=float(amount),
            month_year=month_year,
            date=contribution_date,
            details=details  # Save the details to the database
        )
        db.session.add(new_contribution)
        db.session.commit()
        return redirect(url_for('index'))
    

    selected_month = request.args.get('month')
    if selected_month:
        contributions = Contribution.query.filter(Contribution.month_year == selected_month).order_by(Contribution.date).all()
        # Compute the sum of contributions per person for the selected month
        summary_contributions = db.session.query(
            Contribution.name, 
            func.sum(Contribution.amount).label('total_amount')
        ).filter(Contribution.month_year == selected_month).group_by(Contribution.name).all()
    else:
        contributions = Contribution.query.order_by(Contribution.date).all()
        # Compute the sum of contributions per person for all months
        summary_contributions = db.session.query(
            Contribution.name, 
            func.sum(Contribution.amount).label('total_amount')
        ).group_by(Contribution.name).all()

    display_month = selected_month if selected_month else datetime.now().strftime('%m-%Y')
    
    return render_template('index.html', contributions=contributions, summary_contributions=summary_contributions, display_month=display_month)


# Other routes remain unchanged

@app.route('/last_month')
def last_month():
    last_month_date = get_last_month_date()
    return redirect(url_for('index', month=last_month_date))

if __name__ == '__main__':
    app.run(debug=True)
