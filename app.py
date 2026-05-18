from flask import Flask, render_template, request, redirect, url_for, session, Response
from database import init_db, connect_db
import csv
import io

app = Flask(__name__)
app.secret_key = "queensgate_secret_key_2026"

# Initialize DB
init_db()


# ================= SESSION HELPER =================
def clear_session():
    session.pop("admin_logged_in", None)
    session.pop("voter_logged_in", None)
    session.pop("voter_name", None)


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
        voter_name=session.get("voter_name")
    )


# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return "❌ Access denied. Admin only."

    conn = connect_db()
    topics = conn.execute("SELECT * FROM topics ORDER BY id DESC").fetchall()
    conn.close()

    return render_template("admin_dashboard.html", topics=topics)


# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            clear_session()  # 🔥 FIX: remove voter session

            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        return render_template("admin_login.html", error="❌ Invalid admin credentials!")

    return render_template("admin_login.html", error=None)


# ================= VOTER LOGIN =================
@app.route("/voter_login", methods=["GET", "POST"])
def voter_login():
    conn = connect_db()
    voters = conn.execute("SELECT name FROM voters").fetchall()
    conn.close()

    if request.method == "POST":
        voter_name = request.form["voter_name"]
        secret_code = request.form["secret_code"]

        conn = connect_db()
        voter = conn.execute(
            "SELECT * FROM voters WHERE name=? AND secret_code=?",
            (voter_name, secret_code)
        ).fetchone()
        conn.close()

        if voter:

            clear_session()  # 🔥 FIX: remove admin session

            session["voter_logged_in"] = True
            session["voter_name"] = voter_name

            return redirect(url_for("home"))

        return render_template(
            "voter_login.html",
            voters=voters,
            error="❌ Wrong secret code!"
        )

    return render_template("voter_login.html", voters=voters, error=None)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================= CREATE TOPIC (ADMIN ONLY) =================
@app.route("/create_topic", methods=["GET", "POST"])
def create_topic():
    if not session.get("admin_logged_in"):
        return "❌ Access denied. Admin only."

    if request.method == "POST":
        title = request.form["title"]

        conn = connect_db()
        conn.execute("INSERT INTO topics (title, is_active) VALUES (?, 1)", (title,))
        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    return render_template("create_topic.html")


# ================= DELETE TOPIC (ADMIN ONLY) =================
@app.route("/delete_topic/<int:topic_id>")
def delete_topic(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied. Admin only."

    conn = connect_db()
    conn.execute("DELETE FROM topics WHERE id=?", (topic_id,))
    conn.execute("DELETE FROM votes WHERE topic_id=?", (topic_id,))
    conn.execute("DELETE FROM voter_usage WHERE topic_id=?", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# ================= CLOSE TOPIC =================
@app.route("/close_topic/<int:topic_id>")
def close_topic(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied. Admin only."

    conn = connect_db()
    conn.execute("UPDATE topics SET is_active=0 WHERE id=?", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# ================= OPEN TOPIC =================
@app.route("/open_topic/<int:topic_id>")
def open_topic(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied. Admin only."

    conn = connect_db()
    conn.execute("UPDATE topics SET is_active=1 WHERE id=?", (topic_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# ================= VOTE =================
@app.route("/vote/<int:topic_id>", methods=["GET", "POST"])
def vote(topic_id):
    if not session.get("voter_logged_in"):
        return redirect(url_for("voter_login"))

    voter_name = session.get("voter_name")

    conn = connect_db()

    topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
    if not topic:
        conn.close()
        return "❌ Topic not found."

    if topic["is_active"] == 0:
        conn.close()
        return "❌ Voting is closed."

    voter = conn.execute("SELECT * FROM voters WHERE name=?", (voter_name,)).fetchone()
    voting_power = voter["voting_power"]

    usage = conn.execute(
        "SELECT * FROM voter_usage WHERE topic_id=? AND voter_name=?",
        (topic_id, voter_name)
    ).fetchone()

    if usage is None:
        votes_used = 0
        conn.execute(
            "INSERT INTO voter_usage (topic_id, voter_name, votes_used) VALUES (?, ?, 0)",
            (topic_id, voter_name)
        )
        conn.commit()
    else:
        votes_used = usage["votes_used"]

    remaining_votes = voting_power - votes_used

    candidates = conn.execute(
        "SELECT name FROM voters WHERE name != ?",
        (voter_name,)
    ).fetchall()

    if request.method == "POST":
        candidate_name = request.form["candidate_name"]

        if remaining_votes <= 0:
            conn.close()
            return "❌ No remaining votes."

        existing_vote = conn.execute(
            "SELECT * FROM votes WHERE topic_id=? AND candidate_name=?",
            (topic_id, candidate_name)
        ).fetchone()

        if not existing_vote:
            conn.execute(
                "INSERT INTO votes (topic_id, candidate_name, vote_count) VALUES (?, ?, 1)",
                (topic_id, candidate_name)
            )
        else:
            conn.execute(
                "UPDATE votes SET vote_count = vote_count + 1 WHERE topic_id=? AND candidate_name=?",
                (topic_id, candidate_name)
            )

        conn.execute(
            "UPDATE voter_usage SET votes_used = votes_used + 1 WHERE topic_id=? AND voter_name=?",
            (topic_id, voter_name)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("vote", topic_id=topic_id))

    conn.close()

    return render_template(
        "vote.html",
        topic=topic,
        voter_name=voter_name,
        remaining_votes=remaining_votes,
        voting_power=voting_power,
        candidates=candidates
    )


# ================= RESULTS =================
@app.route("/results/<int:topic_id>")
def results(topic_id):
    conn = connect_db()
    topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()

    if not topic:
        conn.close()
        return "❌ Topic not found."

    if topic["is_active"] == 1 and not session.get("admin_logged_in"):
        conn.close()
        return "❌ Results hidden until closed."

    results_data = conn.execute(
        "SELECT candidate_name, vote_count FROM votes WHERE topic_id=? ORDER BY vote_count DESC",
        (topic_id,)
    ).fetchall()

    winner = results_data[0]["candidate_name"] if results_data else None

    conn.close()

    return render_template(
        "results.html",
        topic=topic,
        results=results_data,
        winner=winner
    )


# ================= EXPORT CSV =================
@app.route("/export_results/<int:topic_id>")
def export_results(topic_id):
    if not session.get("admin_logged_in"):
        return "❌ Access denied."

    conn = connect_db()

    topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
    results_data = conn.execute(
        "SELECT candidate_name, vote_count FROM votes WHERE topic_id=? ORDER BY vote_count DESC",
        (topic_id,)
    ).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Candidate", "Votes"])
    for row in results_data:
        writer.writerow([row["candidate_name"], row["vote_count"]])

    filename = f"{topic['title'].replace(' ', '_')}_results.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)