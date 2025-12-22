from flask import render_template, request, redirect, session
from core.db import get_db
from member import member_bp


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

    conn = get_db()
    data = conn.execute("""
        SELECT m.name, p.name AS plan, ms.start_date, ms.end_date
        FROM members m
        LEFT JOIN memberships ms ON m.id = ms.member_id
        LEFT JOIN plans p ON ms.plan_id = p.id
        WHERE m.id=?
    """, (session["member_id"],)).fetchone()

    conn.close()
    return render_template("member/member_dashboard.html", data=data)
