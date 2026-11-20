from pathlib import Path
from html.parser import HTMLParser
from unittest.mock import patch
import importlib.util
import sys
import uuid
import os
from urllib.parse import urlparse
from pymongo import MongoClient

root = Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root), str(root/'test-deps')]
test_uri=os.environ.get('SHOP_TEST_MONGO_URI','mongodb://127.0.0.1:27129/?replicaSet=codexShop')
if urlparse(test_uri).hostname not in ('127.0.0.1','localhost','::1'):
    raise RuntimeError('Las pruebas solo admiten un MongoDB temporal en loopback.')
real_client=MongoClient(test_uri,serverSelectionTimeoutMS=5000)
real_client.admin.command('ping')
db=real_client['shop_test_'+uuid.uuid4().hex]
class ClientMapping:
    def __getitem__(self, name): return db
with patch('pymongo.MongoClient', return_value=ClientMapping()):
    spec=importlib.util.spec_from_file_location('shop_project',root/'app.py')
    project=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=project
    spec.loader.exec_module(project)
project.app.config['TESTING']=True

class Fields(HTMLParser):
    def __init__(self, html):
        super().__init__();self.fields={};self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='input' and 'name' in a:self.fields[a['name']]=a.get('value','')
def form(client,path):
    r=client.get(path);assert r.status_code==200,(path,r.status_code,r.get_data(as_text=True));return Fields(r.get_data(as_text=True)).fields
def register(name, credit=300, admin=False):
    c=project.app.test_client();csrf=form(c,'/acceso')['csrf']
    assert c.post('/acceso/registro',data={'csrf':csrf,'username':name,'email':name+'@example.com','password':'TestPassword123!','password_confirm':'TestPassword123!'}).status_code==303
    user=db.usuarios.find_one({'username_key':name.casefold()})
    if admin:db.usuarios.update_one({'_id':user['_id']},{'$set':{'role':'admin'}})
    c.get('/inicio');db.saldos.update_one({'_id':user['owner']},{'$set':{'balance':credit}})
    return c,user['owner']
def post(c,path,**extra):
    c.get('/tienda')
    token=c.get_cookie('uf_session').value
    from hashlib import sha256
    s=db.sesiones.find_one({'_id':sha256(token.encode()).hexdigest()})
    w=db.saldos.find_one({'_id':s['owner']})
    return c.post(path,data={'csrf':s['csrf'],'epoch':w.get('economy_epoch',0),**extra})
