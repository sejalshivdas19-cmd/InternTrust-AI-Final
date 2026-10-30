from flask import render_template
from app.blueprints.main import main_bp


@main_bp.route("/")
def index():
    return render_template("main/index.html")


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/how-it-works")
def how_it_works():
    return render_template("main/how_it_works.html")


@main_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("main/privacy_policy.html")


@main_bp.route("/terms")
def terms():
    return render_template("main/terms.html")


@main_bp.route("/contact")
def contact():
    return render_template("main/contact.html")
