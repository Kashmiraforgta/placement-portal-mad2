from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
@pages_bp.route("/<path:_>")  # let Vue's own simple router handle sub-paths
def index(_=None):
    return render_template("index.html")
