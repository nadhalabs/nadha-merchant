from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timezone
import uuid
NOW=lambda:datetime.now(timezone.utc).isoformat()
def product(c,h,s,name='Tracked'):return c.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':name,'unit':'piece','active':True,'inventory_enabled':True,'buy_price':'10','sell_price':'20'}).json()
def person(c,h,s,kind,name):return c.post(f"/api/shops/{s['id']}/{kind}",headers=h,json={'name':name}).json()
def transaction(c,h,s,body):return c.post(f"/api/shops/{s['id']}/transactions",headers=h,json={'occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),**body})
def concurrent(call):
    with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(lambda _:call(),range(2)))
def seed_stock(c,h,s,p,count):
    supplier=person(c,h,s,'suppliers',f'S {uuid.uuid4()}');r=transaction(c,h,s,{'type':'purchase','amount':str(count*10),'payment_method':'cash','payment_state':'paid','paid_amount':str(count*10),'supplier_id':supplier['id'],'items':[{'product_id':p['id'],'quantity':str(count),'unit_price':'10'}]});assert r.status_code==201
def test_last_stock_item_and_duplicate_request(client,owner):
    h,s=owner;p=product(client,h,s);seed_stock(client,h,s,p,1);key=str(uuid.uuid4());body={'type':'sale','amount':'20','payment_method':'cash','occurred_at':NOW(),'idempotency_key':key,'items':[{'product_id':p['id'],'quantity':'1','unit_price':'20'}]};url=f"/api/shops/{s['id']}/transactions"
    results=concurrent(lambda:client.post(url,headers=h,json=body));assert all(r.status_code==201 for r in results);assert results[0].json()['id']==results[1].json()['id'];assert client.get(f"/api/shops/{s['id']}/inventory",headers=h).json()[0]['stock']==0
    p2=product(client,h,s,'Last Item');seed_stock(client,h,s,p2,1);body2={**body,'idempotency_key':str(uuid.uuid4()),'items':[{'product_id':p2['id'],'quantity':'1','unit_price':'20'}]};body3={**body2,'idempotency_key':str(uuid.uuid4())}
    with ThreadPoolExecutor(max_workers=2) as pool:r=[pool.submit(client.post,url,headers=h,json=payload) for payload in (body2,body3)];r=[x.result() for x in r]
    assert sorted(x.status_code for x in r)==[201,409];stocks={x['product_id']:x['stock'] for x in client.get(f"/api/shops/{s['id']}/inventory",headers=h).json()};assert stocks[p2['id']]==0
def test_supplier_and_customer_overpayment_races(client,owner):
    h,s=owner;p=product(client,h,s,'Untracked');pbody={'items':[{'product_id':p['id'],'quantity':'1','unit_price':'1000'}]};supplier=person(client,h,s,'suppliers','Supplier');customer=person(client,h,s,'customers','Customer')
    transaction(client,h,s,{'type':'purchase','amount':'1000','payment_method':'credit','payment_state':'due','paid_amount':'0','supplier_id':supplier['id'],**pbody});transaction(client,h,s,{'type':'sale','amount':'1000','payment_method':'credit','customer_id':customer['id'],**pbody})
    def race(kind,id):
        url=f"/api/shops/{s['id']}/{kind}/{id}/payments";return concurrent(lambda:client.post(url,headers=h,json={'amount':'800','payment_method':'cash','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())}))
    assert sorted(x.status_code for x in race('suppliers',supplier['id']))==[201,400];assert client.get(f"/api/shops/{s['id']}/suppliers/{supplier['id']}",headers=h).json()['balance']==200
    assert sorted(x.status_code for x in race('customers',customer['id']))==[201,400];assert client.get(f"/api/shops/{s['id']}/customers/{customer['id']}",headers=h).json()['balance']==200
def test_stock_adjustment_vs_sale_and_day_close(client,owner):
    h,s=owner;p=product(client,h,s);seed_stock(client,h,s,p,5);sale={'type':'sale','amount':'60','payment_method':'cash','items':[{'product_id':p['id'],'quantity':'3','unit_price':'20'}]};adjust={'quantity_difference':'-3','reason':'Count correction','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())};url=f"/api/shops/{s['id']}"
    with ThreadPoolExecutor(max_workers=2) as pool:a=pool.submit(transaction,client,h,s,sale);b=pool.submit(client.post,url+f"/inventory/{p['id']}/adjustments",headers=h,json=adjust);results=[a.result(),b.result()]
    assert sorted(x.status_code for x in results)==[201,400] or sorted(x.status_code for x in results)==[201,409];assert client.get(url+'/inventory',headers=h).json()[0]['stock']==2
    closing={'date':date.today().isoformat(),'actual_cash':'0','idempotency_key':str(uuid.uuid4())};closed=concurrent(lambda:client.post(url+'/closings',headers=h,json=closing));assert all(x.status_code==201 for x in closed);assert len(client.get(url+'/closings',headers=h).json())==1
