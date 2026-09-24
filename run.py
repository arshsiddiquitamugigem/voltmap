"""Start the local demo; no internet or credentials used at runtime."""
import argparse
import webbrowser
from threading import Timer
import uvicorn
from voltmap.store import DATABASE, build

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);p.add_argument('--no-browser',action='store_true')
    args=p.parse_args()
    if not DATABASE.exists():build()
    if not args.no_browser:Timer(1.0,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    uvicorn.run('voltmap.api:app',host='127.0.0.1',port=args.port)
