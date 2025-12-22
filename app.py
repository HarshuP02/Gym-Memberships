from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date, timedelta
from functools import wraps

app = Flask(__name__)
DB_NAME = "gym.db"
app.secret_key = "super-secret-key"  # required for session


# ---------- DB CONNECTION ----------
def get_db():
    conn = sqlite3.connect("gym.db")
    conn.row_factory = sqlite3.Row  # ✅ THIS IS THE FIX
    return conn


# ---------- INIT DB ----------
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        duration INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        plan_id INTEGER,
        start_date TEXT,
        end_date TEXT
    )
    """)

    conn.commit()
    conn.close()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect("/admin_login")  # or /admin/login
        return f(*args, **kwargs)
    return decorated


# ---------- LANDING ----------
@app.route("/")
@app.route("/landing")
def landing():
    return render_template("landing.html")

#---------- ADMIN LOGIN ---------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session.clear()
            session["is_admin"] = True
            return redirect("/dashboard")

        return "Invalid admin credentials"

    return render_template("admin/admin_login.html")


# ---------- MEMBERS LIST ----------
@app.route("/members")
@admin_required
def members():

    conn = get_db()
    today = date.today().isoformat()

    rows = conn.execute("""
    SELECT 
        m.id,
        m.name,
        m.phone,
        p.name,
        ms.end_date
    FROM members m
    LEFT JOIN memberships ms ON m.id = ms.member_id
    LEFT JOIN plans p ON ms.plan_id = p.id
    ORDER BY m.id DESC
    """).fetchall()

    conn.close()

    members = []
    for r in rows:
        is_active = r[4] and r[4] >= today
        members.append({
            "id": r[0],
            "name": r[1],
            "phone": r[2],
            "plan": r[3],
            "end_date": r[4],
            "active": is_active
        })

    return render_template("admin/members.html", members=members, today=today)


# ---------- ADD MEMBER ----------
@app.route("/members/add", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO members (name, phone) VALUES (?, ?)",
            (request.form["name"], request.form["phone"])
        )
        conn.commit()
        conn.close()
        return redirect("/members")

    return render_template("admin/add_member.html")


# ---------- DELETE MEMBER (SAFE) ----------
@app.route("/members/delete/<int:member_id>")
def delete_member(member_id):
    conn = get_db()

    conn.execute("DELETE FROM memberships WHERE member_id = ?", (member_id,))
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))

    conn.commit()
    conn.close()
    return redirect("/members")


# ---------- PLANS ----------
@app.route("/plans", methods=["GET", "POST"])
@admin_required
def plans():

    conn = get_db()

    if request.method == "POST":
        conn.execute(
            "INSERT INTO plans (name, duration) VALUES (?, ?)",
            (request.form["name"], request.form["duration"])
        )
        conn.commit()

    plans = conn.execute("SELECT * FROM plans").fetchall()
    conn.close()
    return render_template("admin/plans.html", plans=plans)


# ---------- ASSIGN / RENEW ----------
@app.route("/assign/<int:member_id>", methods=["GET", "POST"])
def assign(member_id):
    conn = get_db()

    member = conn.execute(
        "SELECT * FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()

    plans = conn.execute(
        "SELECT * FROM plans"
    ).fetchall()

    if request.method == "POST":
        plan_id = request.form["plan_id"]

        row = conn.execute(
            "SELECT duration FROM plans WHERE id = ?",
            (plan_id,)
        ).fetchone()

        duration_days = row["duration"]  # ✅ NOW THIS WORKS

        start_date = date.today()
        end_date = start_date + timedelta(days=duration_days)

        conn.execute(
            """
            INSERT INTO memberships (member_id, plan_id, start_date, end_date)
            VALUES (?, ?, ?, ?)
            """,
            (member_id, plan_id, start_date, end_date)
        )

        conn.commit()
        conn.close()
        return redirect("/members")

    conn.close()
    return render_template(
        "admin/assign.html",
        member=member,
        plans=plans
    )


#----------- MEMBERS DETAILS----------
@app.route("/members/<int:member_id>")
def member_detail(member_id):
    conn = get_db()
    today = date.today().isoformat()

    member = conn.execute(
        "SELECT * FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()

    membership = conn.execute(
        """
        SELECT
            m.start_date,
            m.end_date,
            p.name AS plan_name
        FROM memberships m
        JOIN plans p ON m.plan_id = p.id
        WHERE m.member_id = ?
        ORDER BY m.end_date DESC
        LIMIT 1
        """,
        (member_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "admin/member_detail.html",
        member=member,
        membership=membership,
        today=today
    )


#----------- DASHBOARD ------------
@app.route("/dashboard")
@admin_required
def dashboard():
    conn = get_db()
    today = date.today().isoformat()

    total_members = conn.execute(
        "SELECT COUNT(*) FROM members"
    ).fetchone()[0]

    active_memberships = conn.execute(
        """
        SELECT COUNT(*) FROM memberships
        WHERE end_date >= ?
        """,
        (today,)
    ).fetchone()[0]

    expired_memberships = conn.execute(
        """
        SELECT COUNT(*) FROM memberships
        WHERE end_date < ?
        """,
        (today,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_members=total_members,
        active_memberships=active_memberships,
        expired_memberships=expired_memberships
    )


#---------- MEMBERS LOGIN ---------
@app.route("/member_login", methods=["GET", "POST"])
def member_login():
    error = None

    if request.method == "POST":
        phone = request.form["phone"]

        conn = sqlite3.connect("gym.db")
        conn.row_factory = sqlite3.Row

        member = conn.execute(
            "SELECT * FROM members WHERE phone = ?",
            (phone,)
        ).fetchone()

        conn.close()

        if member:
            session["member_id"] = member["id"]
            return redirect("/member_dashboard")
        else:
            error = "❌ Member not found. Please contact gym admin."

    return render_template("member/member_login.html", error=error)


#---------- MEMBERS DASHBOARD --------
@app.route("/member_dashboard")
def member_dashboard():
    if "member_id" not in session:
        return redirect("/member_login")

    member_id = session["member_id"]

    conn = sqlite3.connect("gym.db")
    conn.row_factory = sqlite3.Row

    data = conn.execute("""
        SELECT m.name, p.name AS plan,
               ms.start_date, ms.end_date
        FROM members m
        LEFT JOIN memberships ms ON m.id = ms.member_id
        LEFT JOIN plans p ON ms.plan_id = p.id
        WHERE m.id = ?
    """, (member_id,)).fetchone()

    conn.close()

    return render_template("member/member_dashboard.html", data=data)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- RUN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True,)
