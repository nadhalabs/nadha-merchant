from datetime import datetime,timezone

NOW=lambda:datetime.now(timezone.utc).isoformat()
def transaction(client,h,s,type='sale',amount='100'):
    body={'type':type,'amount':amount,'payment_method':'cash','occurred_at':NOW()}
    if type=='purchase':body['payment_state']='paid';body['paid_amount']=amount
    return client.post(f"/api/shops/{s['id']}/transactions",headers=h,json=body).json()
def product(client,h,s,name='Milk',**extra):
    return client.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':name,'unit':'piece','active':True,'inventory_enabled':False,**extra})

def test_product_crud_duplicate_and_shop_isolation(client,owner):
    h,s=owner;p=product(client,h,s,buy_price='20',sell_price='30').json();assert p['name']=='Milk'
    assert product(client,h,s).status_code==409
    changed={k:v for k,v in p.items() if k not in ('id','shop_id','created_at','updated_at')};changed['active']=False
    assert client.put(f"/api/shops/{s['id']}/products/{p['id']}",headers=h,json=changed).json()['active'] is False
    token=client.post('/api/auth/register',json={'email':'p2other@example.com','password':'password1','name':'Other'}).json()['access_token'];other={'Authorization':f'Bearer {token}'}
    assert client.get(f"/api/shops/{s['id']}/products",headers=other).status_code==404

def test_late_itemization_snapshots_partial_and_reuse(client,owner):
    h,s=owner;tx=transaction(client,h,s,amount='420');assert client.get(f"/api/shops/{s['id']}/transactions/{tx['id']}/items",headers=h).json()['items']==[]
    p=product(client,h,s,'Rice',buy_price='40',sell_price='60').json();url=f"/api/shops/{s['id']}/transactions/{tx['id']}/items"
    attached=client.put(url,headers=h,json=[{'product_id':p['id'],'quantity':'2','unit_price':'60','cost_price':'40'}]).json();assert attached['difference']==300
    edit={k:v for k,v in p.items() if k not in ('id','shop_id','created_at','updated_at')};edit['buy_price']='55';edit['sell_price']='75';client.put(f"/api/shops/{s['id']}/products/{p['id']}",headers=h,json=edit)
    old=client.get(url,headers=h).json()['items'][0];assert old['unit_price']=='60.00' and old['cost_price']=='40.00'
    tx2=transaction(client,h,s,amount='75');assert client.put(f"/api/shops/{s['id']}/transactions/{tx2['id']}/items",headers=h,json=[{'product_id':p['id'],'quantity':'1'}]).json()['complete']

def test_inventory_ledger_rebuild_and_manual_adjustment(client,owner):
    h,s=owner;p=product(client,h,s,'Tracked',buy_price='10',sell_price='20',inventory_enabled=True).json();purchase=transaction(client,h,s,'purchase','100');sale=transaction(client,h,s,'sale','40')
    client.put(f"/api/shops/{s['id']}/transactions/{purchase['id']}/items",headers=h,json=[{'product_id':p['id'],'quantity':'10','unit_price':'10','cost_price':'10'}])
    sale_url=f"/api/shops/{s['id']}/transactions/{sale['id']}/items";client.put(sale_url,headers=h,json=[{'product_id':p['id'],'quantity':'2','unit_price':'20','cost_price':'10'}])
    stock=lambda:client.get(f"/api/shops/{s['id']}/inventory",headers=h).json()[0]['stock']
    assert stock()==8
    client.put(sale_url,headers=h,json=[{'product_id':p['id'],'quantity':'1','unit_price':'40','cost_price':'10'}]);assert stock()==9
    client.put(sale_url,headers=h,json=[]);assert stock()==10
    client.post(f"/api/shops/{s['id']}/inventory/{p['id']}/adjustments",headers=h,json={'quantity_difference':'-2','reason':'Damaged goods','occurred_at':NOW()});assert stock()==8
    transaction(client,h,s,'sale','50');assert stock()==8

def test_profit_exact_estimated_and_no_data(client,owner):
    h,s=owner
    assert client.get(f"/api/shops/{s['id']}/profit",headers=h).json()['label']=='Estimated Profit'
    p=product(client,h,s,'Biscuit',buy_price='6',sell_price='10').json();sale=transaction(client,h,s,'sale','100');url=f"/api/shops/{s['id']}/transactions/{sale['id']}/items"
    client.put(url,headers=h,json=[{'product_id':p['id'],'quantity':'10','unit_price':'10','cost_price':'6'}]);exact=client.get(f"/api/shops/{s['id']}/profit",headers=h).json();assert exact['is_exact'] and exact['profit']==40 and exact['coverage_percent']==100
    transaction(client,h,s,'sale','100');estimated=client.get(f"/api/shops/{s['id']}/profit",headers=h).json();assert not estimated['is_exact'] and estimated['coverage_percent']==50
    money=client.get(f"/api/shops/{s['id']}/money-map",headers=h).json();assert money['profit']['label']=='Estimated Profit' and 'href' in money['estimated_stock_value']
