import os
import re
from flask import Flask, jsonify, render_template, request

from cs50 import SQL
from helpers import lookup

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///mashup.db")


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Render map"""
    if not os.environ.get("API_KEY"):
        raise RuntimeError("API_KEY not set")
    return render_template("index.html", key=os.environ.get("API_KEY"))


@app.route("/articles")
def articles():
    """Look up articles for geo"""

    # get geo from index.html form
    geo = request.args.get("geo")

    # check if geo was provided
    if not geo:
        raise RuntimeError("missing geo")

    # lookup articles for geo
    articles = lookup(geo)

    # return a json array of objects with up to 5 items
    if len(articles) > 5:
        articles_list = []
        for i in range(5):
            articles_list.append(articles[i])
        return jsonify(articles_list)
    else:
        return jsonify(articles)


@app.route("/search")
def search():
    """Search for places that match query"""

    # get q and conatenate wild card symbol
    q = request.args.get("q") + "%"

    # query database
    places = db.execute("""
                        SELECT * FROM "places"
                        WHERE (postal_code LIKE :q)
                        OR (place_name LIKE :q)
                        OR (admin_name1 LIKE :q)
                        OR (admin_code1 LIKE :q)
                        OR ((place_name||", "||admin_name1) LIKE :q)
                        OR ((place_name||" "||admin_name1) LIKE :q)
                        OR ((place_name||", "||admin_code1) LIKE :q)
                        OR ((place_name||" "||admin_code1) LIKE :q)
                        OR ((place_name||", "||admin_name1||", "||country_code) LIKE :q)
                        OR ((place_name||" "||admin_name1||" "||country_code) LIKE :q)
                        OR ((place_name||", "||admin_code1||", "||country_code) LIKE :q)
                        OR ((place_name||" "||admin_code1||" "||country_code) LIKE :q)""", q=q)

    if len(places) > 10:
        places_list = []
        for i in range(10):
            places_list.append(places[i])
        return jsonify(places_list)
    else:
        return jsonify(places)


@app.route("/update")
def update():
    """Find up to 10 places within view"""

    # Ensure parameters are present
    if not request.args.get("sw"):
        raise RuntimeError("missing sw")
    if not request.args.get("ne"):
        raise RuntimeError("missing ne")

    # Ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
        raise RuntimeError("invalid ne")

    # Explode southwest corner into two variables
    sw_lat, sw_lng = map(float, request.args.get("sw").split(","))

    # Explode northeast corner into two variables
    ne_lat, ne_lng = map(float, request.args.get("ne").split(","))

    # Find 10 cities within view, pseudorandomly chosen if more within view
    if sw_lng <= ne_lng:

        # Doesn't cross the antimeridian
        rows = db.execute("""SELECT * FROM places
                          WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude AND longitude <= :ne_lng)
                          GROUP BY country_code, place_name, admin_code1
                          ORDER BY RANDOM()
                          LIMIT 10""",
                          sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    else:

        # Crosses the antimeridian
        rows = db.execute("""SELECT * FROM places
                          WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude OR longitude <= :ne_lng)
                          GROUP BY country_code, place_name, admin_code1
                          ORDER BY RANDOM()
                          LIMIT 10""",
                          sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    # Output places as JSON
    return jsonify(rows)
