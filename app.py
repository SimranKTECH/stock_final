from flask import Flask, render_template, redirect, request, session
from psycopg2 import connect

from flask_session import Session
from tempfile import mkdtemp

import os
import datetime
import uuid

from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

app.secret_key = b'simrank'


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# session = Session(app)

dbcon = connect(
        host="localhost",
        database="stocks",
        user="postgres",
        password="1234")

    # create a cursor
db = dbcon.cursor()


os.environ["API_KEY"] = "pk_0759e49f74404315962a70a6c30c8114"

if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route('/')
@login_required
def index():
    # get user cash total
    # result = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    db.execute("select total_cash from user_data where unique_id = %s", (session["unique_id"],))
    cash = 0
    for record in db:
        cash = record[0]

    # pull all transactions belonging to user
    db.execute("SELECT stock_symbol, units_holding FROM portfolio where unique_id = %s", (session["unique_id"],))
    portfolio = []
    for record in db:
        stock = {}
        stock.update({'stock':record[0], 'quantity':record[1]})
        portfolio.append(stock)
        

    if not portfolio:
        return apology("sorry you have no holdings")

    grand_total = cash

    # determine current price, stock total value and grand total value
    for stock in portfolio:
        price = lookup(stock['stock'])['price']
        total = stock['quantity'] * price
        stock.update({'price': price, 'total': total})
        grand_total += total

    return render_template("index.html", stocks=portfolio, cash=cash, total=grand_total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure stock symbol and number of shares was submitted
        if (not request.form.get("stock")) or (not request.form.get("shares")):
            return apology("must provide stock symbol and number of shares")

        # ensure number of shares is valid
        if int(request.form.get("shares")) <= 0:
            return apology("must provide valid number of shares (integer)")

        # pull quote from yahoo finance
        quote = lookup(request.form.get("stock"))

        # check is valid stock name provided
        if quote == None:
            return apology("Stock symbol not valid, please try again")

        # calculate cost of transaction
        cost = int(request.form.get("shares")) * quote['price']

        # check if user has enough cash for transaction
        totalcash = 0
        db.execute("SELECT total_cash FROM user_data WHERE unique_id = %s", (session["unique_id"],))
        for record in db:
            totalcash = record[0]
            
        if cost > totalcash:
            return apology("you do not have enough cash for this transaction")
        
        balance = totalcash - cost

        # update cash amount in users database
        db.execute("UPDATE user_data SET total_cash = %s WHERE unique_id = %s", (balance, session["unique_id"]))
        dbcon.commit()
        
        dt = datetime.datetime.now(datetime.timezone.utc)
        # add transaction to transaction database
        db.execute("INSERT INTO stock_transactions (cost, tstamp, symbol, units, unique_id) VALUES (%s, %s, %s, %s, %s)",
            (quote['price'], dt, request.form.get("stock"), request.form.get("shares"), session["unique_id"]))
        dbcon.commit()

        # pull number of shares of symbol in portfolio
        db.execute("SELECT units_holding, average_price FROM portfolio WHERE stock_symbol = %s and unique_id = %s", (quote["symbol"],session["unique_id"]))
        curr_portfolio = None
        curr_avg = None
        print("******************************")
        for record in db:
            curr_portfolio = record[0]
            curr_avg = record[1]
            print(record)
            
        print("*****************")
        print(curr_portfolio, curr_avg)
        print("*****************")

        # add to portfolio database
        # if symbol is new, add to portfolio
        if not curr_portfolio:
            db.execute("INSERT INTO portfolio (stock_name, stock_symbol, units_holding, average_price, unique_id) VALUES (%s, %s, %s, %s, %s)",
                (quote["name"], quote["symbol"], request.form.get("shares"), quote['price'], session["unique_id"]))
            dbcon.commit()

        # if symbol is already in portfolio, update quantity of shares and total
        else:
            shares = float(request.form.get("shares"))
            newavg = (curr_avg*curr_portfolio + shares*quote['price'])/(shares + curr_portfolio)
            newunits = (curr_portfolio + shares)
            db.execute("UPDATE portfolio SET units_holding = %s, average_price = %s WHERE stock_symbol = %s and unique_id = %s",
                (newunits, newavg, quote["symbol"], session['unique_id']))
            dbcon.commit()

        dbcon.commit()
        return redirect("/")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")



@app.route("/bank", methods=["GET", "POST"])
@login_required
def bank():
    if request.method == 'GET':
        return render_template("bank.html")
    if request.method == 'POST':
        id = uuid.uuid4().int>>64
        bank_name = request.form.get('bank_name')
        amount = float(request.form.get('amount'))
        d_w = request.form.get('d_w')[0]
        tstamp = datetime.datetime.now(datetime.timezone.utc)
        print(bank_name, amount, d_w, tstamp)
        db.execute('INSERT INTO bank_transaction VALUES(%s, %s, %s, %s, %s, %s);', (id, bank_name, amount, d_w, tstamp, session["unique_id"]))
        if d_w == 'w':
            db.execute('UPDATE user_data SET total_cash=total_cash-%s WHERE unique_id = %s', (amount, session['unique_id']))
            print()
        else:
            db.execute('UPDATE user_data SET total_cash=total_cash+%s WHERE unique_id = %s', (amount, session['unique_id']))
        dbcon.commit()
        return redirect("/")
        
@app.route("/history")
@login_required
def history():
    stock_trans = []
    db.execute("SELECT symbol, cost, tstamp, units from stock_transactions where unique_id = %s", (session["unique_id"],))
    for record in db:
        currrecord = {"symbol" : record[0], "cost": record[1], "tstamp" : record[2], "units" : record[3]}
        stock_trans.append(currrecord)
        
    print(stock_trans)
    if not stock_trans:
        return apology("no transaction found")
        
    return render_template("history.html", stock_trans=stock_trans)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        db.execute("SELECT unique_id, password_hash  FROM users WHERE username = %s", (request.form.get("username"),))
        rec_count = 0
        session["unique_id"] = None
        session["password_hash"] = None
        for record in db:
            print(record)
            session["unique_id"] = record[0]
            session["password_hash"] = record[1]
            print("printing one record")
            rec_count += 1
        
        entered_password_hash = generate_password_hash(request.form.get("password"))
        print(session["password_hash"])
        print(request.form.get("password"))
        
        # Ensure username exists and password is correct
        if session["password_hash"] != request.form.get("password"):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = request.form.get("username")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure name of stock was submitted
        if not request.form.get("stock"):
            return apology("must provide stock symbol")

        # pull quote from yahoo finance
        quote = lookup(request.form.get("stock"))

        # check is valid stock name provided
        if quote == None:
            return apology("Stock symbol not valid, please try again")

        # stock name is valid
        else:
            return render_template("quoted.html", quote=quote)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password and password confirmation were submitted
        elif not request.form.get("password") or not request.form.get("password_confirm"):
            return apology("must provide password")
        
        # ensure phone number was submitted
        elif not request.form.get("phone_no"):
            return apology("must provide phone number")
        
        # ensure password and password confirmation match
        elif request.form.get("password") != request.form.get("password_confirm"):
            return apology("password and password confirmation must match")

        # hash password
        # hashval = generate_password_hash(request.form.get("password"))
        number = request.form.get("phone_no")
          #ensure phone number contains all numeric values
        if not number.isdigit():
            return apology("Phone number should contain only numeric values")
        
        #ensure account number only contains numbers
        # account = request.form.get("account")
        # if not account.isdigit():
        #     return apology("Account number should only contain numeric values")
            
        # add user to database
        db.execute("select unique_id from users where username = %s", (request.form.get("username"),))
        # ensure username is unique
        if db.rowcount != 0:
            db.execute("select * from users")
            for record in db:
                print(record)
            return apology("username is already registered")
        
        name = request.form.get("name")
        phone_no = request.form.get("phone_no")
        email_id = request.form.get("email_id")
        dob = request.form.get("dob")
        acc_no = request.form.get("acc_no")
        age = request.form.get("age")
        cash = 10000
        
        db.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (request.form.get("username"), request.form.get("password")))
        dbcon.commit()
        print("****************************")
        # print(db.statusmessage, db.rowcount)
        session["user_id"] = request.form.get("username")
        
        db.execute("select * from users")
        for record in db:
            print(record)
            
        dbcon.commit()
        
        db.execute("select unique_id from users where username = %s", (request.form.get("username"),))
        rec_count = 0
        for record in db:
            print(record)
            session["unique_id"] = record[0]
            rec_count += 1
        
        # # remember which user has logged in

        db.execute("insert into user_data values (%s, %s, %s, %s, %s, %s, %s, %s)", (name, phone_no, email_id, dob, acc_no, age, cash, session["unique_id"]))
        dbcon.commit()
        # redirect user to home page
        return redirect("/")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks = []
    db.execute("SELECT distinct(stock_symbol) from portfolio where unique_id = %s", (session["unique_id"],))
    for record in db:
        stocks.append(record[0])
    
    if request.method == "POST":
        symbol = request.form.get("stock")
        shares = request.form.get("shares")
        shares = int(shares)

        print("Recieved symbol : ", symbol)
        print("Recieved shares : ", shares)

        db.execute("SELECT units_holding from portfolio where unique_id = %s and stock_symbol = %s", (session["unique_id"], symbol))
        no_of_shares = None
        for record in db:
            no_of_shares = record[0]
            
        print(no_of_shares)
        if not symbol:
            return apology("must provide symbol", 403)
        if shares > no_of_shares:
            return apology("The user does not own that many shares of the stock")

        data_recieved = lookup(symbol)
        # store the price information of the required stock
        latest_price = data_recieved["price"]
        latest_price = float(latest_price)

        
        db.execute("UPDATE user_data set total_cash = total_cash + %s where unique_id = %s", (shares * latest_price, session["unique_id"]))
        dbcon.commit()
        
        db.execute("UPDATE portfolio set units_holding = units_holding - %s where unique_id = %s and stock_symbol = %s", (shares, session["unique_id"], symbol))
        dbcon.commit()
        
        dt = datetime.datetime.now(datetime.timezone.utc)
        db.execute("INSERT INTO stock_transactions (cost, tstamp, symbol, units, unique_id) VALUES (%s, %s, %s, %s, %s)",
            (latest_price, dt, symbol, -1*shares, session["unique_id"]))
        dbcon.commit()

        return redirect("/")
    
    return render_template("sell.html", stocks=stocks)

#report generation
@app.route("/report", methods=["GET", "POST"])
def report():
    #get all the stock transaction with username shree
    db.execute("select * from user_data")
    result = db.fetchall()
    
    return render_template("report.html", result = result)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == '__main__':
    app.run(debug=True)