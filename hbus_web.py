#coding=utf-8

from bottle import route, run, template

@route('/')
@route('/index.html')
def index():
    
    return """
    
    <h1>HBUS server</h1>
    
    blablablablabla
    
    """
    
run(host='localhost',port=8000)
