from flask import render_template, request, redirect, session
from core.db import get_db
from member import member_bp
from datetime import date, datetime
import sqlite3

@member_bp.route("/member_login", methods=["GET", "POST"])
def member_login():
    error = None

    if request.method == "POST":
        conn = get_db()
        member = conn.execute("SELECT * FROM members WHERE phone=?",
                              (request.form["phone"],)).fetchone()
        conn.close()

        if member:
            session["member_id"] = member["id"]
            return redirect("/member_dashboard")
        error = "Member not found"

    return render_template("member/member_login.html", error=error)


@member_bp.route("/member_dashboard")
def member_dashboard():
    if "member_id" not in session:
        return redirect("/member_login")

    member_id = session["member_id"]

    conn = sqlite3.connect("gym.db")
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT 
            m.name,
            p.name AS plan,
            ms.start_date,
            ms.end_date
        FROM members m
        LEFT JOIN memberships ms ON m.id = ms.member_id
        LEFT JOIN plans p ON ms.plan_id = p.id
        WHERE m.id = ?
        ORDER BY ms.end_date DESC
        LIMIT 1
    """, (member_id,)).fetchone()

    conn.close()

    if not row or not row["end_date"]:
        return render_template(
            "member/member_dashboard.html",
            data=None
        )

    # ---- DATE CALCULATIONS (CORRECT) ----
    start_date = datetime.strptime(row["start_date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(row["end_date"], "%Y-%m-%d").date()
    today = date.today()

    total_days = (end_date - start_date).days
    remaining_days = (end_date - today).days
    used_days = total_days - remaining_days

    progress = int((used_days / total_days) * 100) if total_days > 0 else 0
    progress = max(0, min(progress, 100))  # clamp 0–100

    is_active = end_date >= today

    return render_template(
        "member/member_dashboard.html",
        data=row,
        remaining_days=remaining_days,
        progress=progress,
        is_active=is_active
    )
