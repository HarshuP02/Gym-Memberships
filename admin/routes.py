from flask import render_template, request, redirect, session
from datetime import date, timedelta
from core.db import get_db
from core.auth import admin_required
from admin import admin_bp


@admin_bp.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin123":
            session.clear()
            session["is_admin"] = True
            return redirect("/dashboard")
        return "Invalid credentials"
    return render_template("admin/admin_login.html")


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    conn = get_db()

    today = date.today().isoformat()
    soon_date = (date.today() + timedelta(days=7)).isoformat()

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

    expiring_soon = conn.execute(
        """
        SELECT COUNT(*) FROM memberships
        WHERE end_date BETWEEN ? AND ?
        """,
        (today, soon_date)
    ).fetchone()[0]

    conn.close()  # ✅ CLOSE AT THE VERY END

    return render_template(
        "admin/dashboard.html",
        total_members=total_members,
        active_memberships=active_memberships,
        expired_memberships=expired_memberships,
        expiring_soon=expiring_soon
    )

@admin_bp.route("/members")
@admin_required
def members():
    conn = get_db()
    today = date.today().isoformat()

    rows = conn.execute("""
        SELECT m.id, m.name, m.phone, p.name, ms.end_date
        FROM members m
        LEFT JOIN memberships ms ON m.id = ms.member_id
        LEFT JOIN plans p ON ms.plan_id = p.id
        ORDER BY m.id DESC
    """).fetchall()

    conn.close()

    members = []
    for r in rows:
        members.append({
            "id": r[0],
            "name": r[1],
            "phone": r[2],
            "plan": r[3],
            "end_date": r[4],
            "active": r[4] and r[4] >= today
        })

    return render_template("admin/members.html", members=members, today=today)


@admin_bp.route("/members/add", methods=["GET", "POST"])
@admin_required
def add_member():
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO members (name, phone) VALUES (?, ?)",
                     (request.form["name"], request.form["phone"]))
        conn.commit()
        conn.close()
        return redirect("/members")

    return render_template("admin/add_member.html")


@admin_bp.route("/members/delete/<int:member_id>")
@admin_required
def delete_member(member_id):
    conn = get_db()
    conn.execute("DELETE FROM memberships WHERE member_id=?", (member_id,))
    conn.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()
    return redirect("/members")


@admin_bp.route("/plans", methods=["GET", "POST"])
@admin_required
def plans():
    conn = get_db()

    if request.method == "POST":
        conn.execute("INSERT INTO plans (name, duration) VALUES (?, ?)",
                     (request.form["name"], request.form["duration"]))
        conn.commit()

    plans = conn.execute("SELECT * FROM plans").fetchall()
    conn.close()
    return render_template("admin/plans.html", plans=plans)


@admin_bp.route("/assign/<int:member_id>", methods=["GET", "POST"])
@admin_required
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

        # ✅ FIX: correct column name
        row = conn.execute(
            "SELECT duration FROM plans WHERE id = ?",
            (plan_id,)
        ).fetchone()

        duration_days = row["duration"]  # ✅ correct

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


@admin_bp.route("/members/<int:member_id>")
@admin_required
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

@admin_bp.route("/expiring")
@admin_required
def expiring_members():
    conn = get_db()
    today = date.today().isoformat()
    soon_date = (date.today() + timedelta(days=7)).isoformat()

    rows = conn.execute(
        """
        SELECT
            m.id,
            m.name,
            m.phone,
            p.name AS plan,
            ms.end_date
        FROM memberships ms
        JOIN members m ON ms.member_id = m.id
        JOIN plans p ON ms.plan_id = p.id
        WHERE ms.end_date BETWEEN ? AND ?
        ORDER BY ms.end_date ASC
        """,
        (today, soon_date)
    ).fetchall()

    conn.close()

    return render_template(
        "admin/expiring.html",
        members=rows
    )
