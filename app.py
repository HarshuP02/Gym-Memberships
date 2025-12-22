from flask import Flask, render_template, session, redirect
from core.db import init_db
from admin import admin_bp
from member import member_bp

app = Flask(__name__)
app.secret_key = "super-secret-key"

app.register_blueprint(admin_bp)
app.register_blueprint(member_bp)


@app.route("/")
@app.route("/landing")
def landing():
    return render_template("landing.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
