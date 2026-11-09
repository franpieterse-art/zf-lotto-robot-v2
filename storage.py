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


def save_lesson(day,lesson):
    import json
    with LOCK,connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS lessons(day TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        con.execute('INSERT OR REPLACE INTO lessons(day,payload) VALUES (?,?)',(day,json.dumps(lesson)))

def load_lessons(before_day):
    import json
    with LOCK,connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS lessons(day TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        return [dict(json.loads(payload),day=day) for day,payload in con.execute('SELECT day,payload FROM lessons WHERE day < ? ORDER BY day',(before_day,))]

def count_lessons():
    with LOCK,connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS lessons(day TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        return con.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
