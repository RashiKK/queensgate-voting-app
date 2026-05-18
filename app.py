from flask import Flask, render_template, request, redirect, url_for, session, Response
from database import init_db, connect_db
import csv
import io

app = Flask(__name__)
app.secret_key = "queensgate_secret_key_2026"

init_db()


# ================= SESSION =================
def clear_session():
    session.pop("admin_logged_in", None)
    session.pop("voter_logged_in", None)
    session.pop("voter_email", None)


# ================= HOME =================
@app.route("/")
def home():
    conn = connect_db()
    topics = conn.execute("SELECT * FROM topics ORDER BY id DESC").fetchall()
    conn.close()

    return render_template(
        "index.html",
        topics=topics,
        admin_logged_in=session.get("admin_logged_in"),
        voter_logged_in=session.get("voter_logged_in"),
        voter_email=session.get("voter_email")
    )


# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            clear_session()
            session["admin_logged_in"] = True
            return redirect(url_for("home"))

        return render_template("admin_login.html", error="❌ Invalid admin credentials!")

    return render_template("admin_login.html", error=None)


# ================= VOTER LOGIN =================
@app.route("/voter_login", methods=["GET", "POST"])
def voter_login():
    conn = connect_db()
    voters = conn.execute("SELECT email FROM voters").fetchall()

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        voter = conn.execute(
            "SELECT * FROM voters WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        conn.close()

        if voter:
            clear_session()
            session["voter_email"] = email
            session["voter_logged_in"] = True

            # 🔥 FORCE PASSWORD CHANGE CHECK
            if voter["must_change_password"] == 1:
                return redirect(url_for("change_password"))

            return redirect(url_for("home"))

        return render_template(
            "voter_login.html",
            voters=voters,
            error="❌ Invalid login!"
        )

    conn.close()
    return render_template("voter_login.html", voters=voters, error=None)


# ================= CHANGE PASSWORD (FORCED) =================
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if not session.get("voter_logged_in"):
        return redirect(url_for("voter_login"))

    email = session["voter_email"]

    if request.method == "POST":
        new_password = request.form["new_password"]

        conn = connect_db()
        conn.execute("""
            UPDATE voters
            SET password=?, must_change_password=0
            WHERE email=?
        """, (new_password, email))
        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template("change_password.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================= TOPIC CREATE =================
@app.route("/create_topic", methods=["GET", "POST"])
def create_topic():
    if not session.get("admin_logged_in"):
        return "❌ Access denied"

    if request.method == "POST":
        title = request.form["title"]

        conn = connect_db()
        conn.execute("INSERT INTO topics (title, is_active) VALUES (?, 1)", (title,))
        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template("create_topic.html")


# ================= DELETE TOPIC =================
@app.route("/delete_topic/<int:topic_id>")
def delete_topic(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied"

    conn = connect_db()
    conn.execute("DELETE FROM topics WHERE id=?", (topic_id,))
    conn.execute("DELETE FROM votes WHERE topic_id=?", (topic_id,))
    conn.execute("DELETE FROM voter_usage WHERE topic_id=?", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ================= CLOSE TOPIC =================
@app.route("/close_topic/<int:topic_id>")
def close_topic(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied"

    conn = connect_db()
    conn.execute("UPDATE topics SET is_active=0 WHERE id=?", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ================= OPEN TOPIC =================
@app.route("/open_topic/<int:topic_id>")
def open_topic(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied"

    conn = connect_db()
    conn.execute("UPDATE topics SET is_active=1 WHERE id=?", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ================= VOTE =================
@app.route("/vote/<int:topic_id>", methods=["GET", "POST"])
def vote(topic_id):
    if not session.get("voter_logged_in"):
        return redirect(url_for("voter_login"))

    email = session["voter_email"]
    conn = connect_db()

    topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()

    if not topic:
        return "Topic not found"

    if topic["is_active"] == 0:
        return "Voting closed"

    voter = conn.execute("SELECT * FROM voters WHERE email=?", (email,)).fetchone()

    usage = conn.execute(
        "SELECT * FROM voter_usage WHERE topic_id=? AND voter_email=?",
        (topic_id, email)
    ).fetchone()

    if not usage:
        votes_used = 0
        conn.execute(
            "INSERT INTO voter_usage (topic_id, voter_email, votes_used) VALUES (?, ?, 0)",
            (topic_id, email)
        )
        conn.commit()
    else:
        votes_used = usage["votes_used"]

    remaining_votes = voter["voting_power"] - votes_used

    candidates = conn.execute("SELECT name FROM voters").fetchall()

    if request.method == "POST":
        if remaining_votes <= 0:
            return "No votes left"

        candidate_name = request.form["candidate_name"]

        existing = conn.execute(
            "SELECT * FROM votes WHERE topic_id=? AND candidate_name=?",
            (topic_id, candidate_name)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE votes SET vote_count = vote_count + 1 WHERE topic_id=? AND candidate_name=?",
                (topic_id, candidate_name)
            )
        else:
            conn.execute(
                "INSERT INTO votes (topic_id, candidate_name, vote_count) VALUES (?, ?, 1)",
                (topic_id, candidate_name)
            )

        conn.execute(
            "UPDATE voter_usage SET votes_used = votes_used + 1 WHERE topic_id=? AND voter_email=?",
            (topic_id, email)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("vote", topic_id=topic_id))

    conn.close()

    return render_template(
        "vote.html",
        topic=topic,
        voter_email=email,
        remaining_votes=remaining_votes,
        voting_power=voter["voting_power"],
        candidates=candidates
    )


# ================= RESULTS =================
@app.route("/results/<int:topic_id>")
def results(topic_id):
    conn = connect_db()

    topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()

    results = conn.execute(
        "SELECT candidate_name, vote_count FROM votes WHERE topic_id=? ORDER BY vote_count DESC",
        (topic_id,)
    ).fetchall()

    winner = results[0]["candidate_name"] if results else None

    conn.close()

    return render_template(
        "results.html",
        topic=topic,
        results=results,
        winner=winner
    )


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)