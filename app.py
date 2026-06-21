from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "task_manager_secret"

# ---------------- DATABASE ----------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "taskmanager.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    due_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

# Create DB tables
with app.app_context():
    db.create_all()

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            username = request.form["username"].strip()
            password = request.form["password"].strip()

            if not username or not password:
                flash("Username and password are required.", "danger")
                return redirect(url_for("register"))

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username already exists!", "danger")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            username = request.form["username"].strip()
            password = request.form["password"].strip()

            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["username"] = user.username
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid username or password!", "danger")
                return redirect(url_for("login"))
        except Exception as e:
            flash(f"Login failed: {str(e)}", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    tasks = Task.query.filter_by(user_id=user_id).all()

    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "Completed"])
    pending_tasks = len([task for task in tasks if task.status == "Pending"])
    high_priority = len([task for task in tasks if task.priority == "High"])

    return render_template(
        "dashboard.html",
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        high_priority=high_priority
    )

@app.route("/add_task", methods=["GET", "POST"])
def add_task():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            title = request.form["title"]
            description = request.form["description"]
            priority = request.form["priority"]
            due_date = request.form["due_date"]

            task = Task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                user_id=session["user_id"]
            )
            db.session.add(task)
            db.session.commit()

            flash("Task added successfully!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            db.session.rollback()
            flash(f"Task creation failed: {str(e)}", "danger")
            return redirect(url_for("add_task"))

    return render_template("add_task.html")

@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    task = Task.query.get_or_404(task_id)

    if task.user_id != session["user_id"]:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        try:
            task.title = request.form["title"]
            task.description = request.form["description"]
            task.priority = request.form["priority"]
            task.due_date = request.form["due_date"]
            task.status = request.form["status"]

            db.session.commit()
            flash("Task updated successfully!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            db.session.rollback()
            flash(f"Task update failed: {str(e)}", "danger")
            return redirect(url_for("dashboard"))

    return render_template("edit_task.html", task=task)

@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    task = Task.query.get_or_404(task_id)

    if task.user_id != session["user_id"]:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("dashboard"))

    try:
        db.session.delete(task)
        db.session.commit()
        flash("Task deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Delete failed: {str(e)}", "danger")

    return redirect(url_for("dashboard"))

@app.route("/toggle_status/<int:task_id>")
def toggle_status(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    task = Task.query.get_or_404(task_id)

    if task.user_id != session["user_id"]:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("dashboard"))

    try:
        task.status = "Completed" if task.status == "Pending" else "Pending"
        db.session.commit()
        flash("Task status updated!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Status update failed: {str(e)}", "danger")

    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
