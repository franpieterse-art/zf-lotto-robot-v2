"""SQLite cache. Set LOTTO_DB_PATH to a Render persistent disk path for durable storage."""
import os, sqlite3, threading
DB=os.getenv('LOTTO_DB_PATH','lotto_history.sqlite3')
LOCK=threading.RLock()
def connect():
    parent=os.path.dirname(os.path.abspath(DB));os.makedirs(parent,exist_ok=True)
    con=sqlite3.connect(DB,timeout=20)
    con.execute('CREATE TABLE IF NOT EXISTS draws(game TEXT NOT NULL, day TEXT NOT NULL, numbers TEXT NOT NULL, source TEXT NOT NULL, PRIMARY KEY(game,day))')
    return con
def load():
    with LOCK,connect() as con:
        result={'lotto':{},'plus1':{},'plus2':{}}
        for game,day,nums in con.execute('SELECT game,day,numbers FROM draws'):
            if game in result:result[game][day]=[int(x) for x in nums.split(',')]
        return result
def save(game,rows,source):
    if not rows:return 0
    with LOCK,connect() as con:
        for day,nums in rows.items():
            old=con.execute('SELECT numbers FROM draws WHERE game=? AND day=?',(game,day)).fetchone()
            value=','.join(map(str,nums))
            if old and old[0]!=value:raise ValueError('Conflicting '+game+' draw on '+day+'; existing record preserved')
        con.executemany('INSERT OR IGNORE INTO draws VALUES (?,?,?,?)',[(game,d,','.join(map(str,n)),source) for d,n in rows.items()])
    return len(rows)
