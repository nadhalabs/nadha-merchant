from datetime import datetime,timezone
import uuid
NOW=lambda:datetime.now(timezone.utc).isoformat()
def product(client,h,s,name='Milk',**extra):return client.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':name,'unit':'piece','active':True,'inventory_enabled':False,**extra})
def transaction(client,h,s,p,type='sale',amount='100',quantity='1',price=None,**extra):
    body={'type':type,'amount':amount,'payment_method':'cash','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),'items':[{'product_id':p['id'],'quantity':quantity,'unit_price':price or amount,'cost_price':p.get('buy_price')}],**extra}
    if type=='purchase':body.update(payment_state='paid',paid_amount=amount)
    r=client.post(f"/api/shops/{s['id']}/transactions",headers=h,json=body);assert r.status_code==201,r.text;return r.json()
def test_product_crud_duplicate_and_shop_isolation(client,owner):
    h,s=owner;p=product(client,h,s,buy_price='20',sell_price='30').json();assert p['name']=='Milk';assert product(client,h,s).status_code==409
    changed={k:v for k,v in p.items() if k not in ('id','shop_id','created_at','updated_at')};changed['active']=False;assert client.put(f"/api/shops/{s['id']}/products/{p['id']}",headers=h,json=changed).json()['active'] is False
def test_atomic_items_are_finalized_and_snapshotted(client,owner):
    h,s=owner;p=product(client,h,s,'Rice',buy_price='40',sell_price='60').json();tx=transaction(client,h,s,p,amount='120',quantity='2',price='60');url=f"/api/shops/{s['id']}/transactions/{tx['id']}/items";summary=client.get(url,headers=h).json();assert summary['complete'] and summary['items'][0]['cost_price']=='40.00';assert client.put(url,headers=h,json=[]).status_code==409
def test_inventory_atomic_and_manual_adjustment(client,owner):
    h,s=owner;p=product(client,h,s,'Tracked',buy_price='10',sell_price='20',inventory_enabled=True).json();transaction(client,h,s,p,'purchase','100','10','10');transaction(client,h,s,p,'sale','40','2','20');stock=lambda:client.get(f"/api/shops/{s['id']}/inventory",headers=h).json()[0]['stock'];assert stock()==8
    key=str(uuid.uuid4());body={'quantity_difference':'-2','reason':'Damaged goods','occurred_at':NOW(),'idempotency_key':key};client.post(f"/api/shops/{s['id']}/inventory/{p['id']}/adjustments",headers=h,json=body);client.post(f"/api/shops/{s['id']}/inventory/{p['id']}/adjustments",headers=h,json=body);assert stock()==6
def test_profit_exact_and_estimated(client,owner):
    h,s=owner;p=product(client,h,s,'Biscuit',buy_price='6',sell_price='10').json();transaction(client,h,s,p,'sale','100','10','10');exact=client.get(f"/api/shops/{s['id']}/profit",headers=h).json();assert exact['is_exact'] and exact['profit']==40
    p2=product(client,h,s,'Unknown',sell_price='100').json();transaction(client,h,s,p2,'sale','100');assert not client.get(f"/api/shops/{s['id']}/profit",headers=h).json()['is_exact']
