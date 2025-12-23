
from flask import Flask, render_template, request, redirect, session, flash
import sqlite3, datetime

app=Flask(__name__)
app.secret_key="tanuj_key"
DB="warehouse.db"
CURRENCY="₹"

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init():
    conn=db(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,company TEXT,reorder_level INT,stock INT,mrp REAL,selling REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS trans(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INT,type TEXT,qty INT,mrp REAL,selling REAL,date TEXT)")
    conn.commit(); conn.close()

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form['username']=="admin" and request.form['password']=="admin123":
            session['logged']=True
            return redirect('/')
        flash("Wrong username or password")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def need(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a,**k):
        if not session.get("logged"):return redirect('/login')
        return f(*a,**k)
    return wrap

@app.route('/')
@need
def dash():
    conn=db()
    items=conn.execute("SELECT * FROM items").fetchall()
    total=len(items)
    qty=sum([i['stock'] for i in items])
    low=sum(1 for i in items if i['stock']<=i['reorder_level'])
    sale=conn.execute("SELECT SUM(qty*selling) s, SUM(qty*(selling-mrp)) p FROM trans WHERE type='OUT'").fetchone()
    ts=sale['s'] or 0; tp=sale['p'] or 0
    conn.close()
    return render_template("dashboard.html",items=items,total=total,qty=qty,low=low,ts=ts,tp=tp,CURRENCY=CURRENCY)

@app.route('/add',methods=['GET','POST'])
@need
def add():
    if request.method=='POST':
        name=request.form['name']
        comp=request.form['company']
        r=int(request.form['reorder'])
        s=int(request.form['stock'])
        m=float(request.form['mrp'])
        se=float(request.form['selling'])
        conn=db()
        conn.execute("INSERT INTO items(name,company,reorder_level,stock,mrp,selling) VALUES(?,?,?,?,?,?)",(name,comp,r,s,m,se))
        idd=conn.execute("SELECT last_insert_rowid() id").fetchone()['id']
        if s>0:
            conn.execute("INSERT INTO trans(item_id,type,qty,mrp,selling,date) VALUES(?,?,?,?,?,?)",(idd,'IN',s,m,se,datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
        return redirect('/')
    return render_template("add_item.html")

@app.route('/update/<int:id>',methods=['GET','POST'])
@need
def up(id):
    conn=db()
    it=conn.execute("SELECT * FROM items WHERE id=?",(id,)).fetchone()
    if not it: return redirect('/')
    if request.method=='POST':
        q=int(request.form['qty'])
        m=float(request.form['mrp'])
        s=float(request.form['selling'])
        t=request.form['type']
        new=it['stock']
        if t=="IN": new+=q
        else:
            if q>it['stock']:
                flash("Not enough stock");return redirect(f'/update/{id}')
            new-=q
        conn.execute("UPDATE items SET stock=?,mrp=?,selling=? WHERE id=?",(new,m,s,id))
        conn.execute("INSERT INTO trans(item_id,type,qty,mrp,selling,date) VALUES(?,?,?,?,?,?)",(id,t,q,m,s,datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
        return redirect('/')
    conn.close()
    return render_template("update_stock.html",item=it,CURRENCY=CURRENCY)

@app.route('/history')
@need
def his():
    conn=db()
    rows=conn.execute("SELECT t.*,i.name item,i.company comp FROM trans t LEFT JOIN items i ON t.item_id=i.id ORDER BY date DESC").fetchall()
    conn.close()
    return render_template("history.html",rows=rows,CURRENCY=CURRENCY)

if __name__=='__main__':
    init()
    app.run(debug=True)
