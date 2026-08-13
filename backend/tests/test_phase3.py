from datetime import date,datetime,timezone
import uuid
NOW=lambda:datetime.now(timezone.utc).isoformat()
def tx(c,h,s,**extra):
    body={'type':'sale','amount':'100','payment_method':'cash','occurred_at':NOW(),**extra}
    body['idempotency_key']=str(uuid.uuid4())
    if body['type']!='expense':
        p=c.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':f'Item {uuid.uuid4()}','unit':'piece','active':True,'inventory_enabled':False}).json();body['items']=[{'product_id':p['id'],'quantity':'1','unit_price':body['amount']}]
    return c.post(f"/api/shops/{s['id']}/transactions",headers=h,json=body)
def customer(c,h,s,name='Ravi'):return c.post(f"/api/shops/{s['id']}/customers",headers=h,json={'name':name}).json()
def supplier(c,h,s,name='ABC Distributor'):return c.post(f"/api/shops/{s['id']}/suppliers",headers=h,json={'name':name,'payment_terms':'30 days'}).json()
def product(c,h,s,name='Oil'):return c.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':name,'unit':'litre','active':True,'inventory_enabled':True,'buy_price':'100','sell_price':'130'}).json()

def test_missing_money_exact_shortage_excess_and_recalculation(client,owner):
    h,s=owner;today=date.today().isoformat();tx(client,h,s,amount='500')
    closing=client.post(f"/api/shops/{s['id']}/closings",headers=h,json={'date':today,'actual_cash':'500','idempotency_key':str(uuid.uuid4())}).json()
    review=lambda:client.get(f"/api/shops/{s['id']}/cash-review?period=today",headers=h).json()['dates'][0]
    assert review()['difference']==0
    client.put(f"/api/shops/{s['id']}/closings/{closing['id']}",headers=h,json={'date':today,'actual_cash':'450'});assert review()['difference']==-50
    client.put(f"/api/shops/{s['id']}/closings/{closing['id']}",headers=h,json={'date':today,'actual_cash':'550'});assert review()['difference']==50
    tx(client,h,s,type='expense',amount='50',payment_method='cash',category='Delivery');assert review()['difference']==100
    sale=tx(client,h,s,amount='100').json();assert review()['difference']==0;body={k:v for k,v in sale.items() if k not in ('id','shop_id','created_at','updated_at')};body['amount']='200';client.put(f"/api/shops/{s['id']}/transactions/{sale['id']}",headers=h,json=body);assert review()['difference']==-100

def test_credit_sale_excluded_health_and_collect_today(client,owner):
    h,s=owner;c=customer(client,h,s);tx(client,h,s,amount='800',payment_method='credit',customer_id=c['id']);client.post(f"/api/shops/{s['id']}/customers/{c['id']}/payments",headers=h,json={'amount':'200','occurred_at':NOW()})
    today=date.today().isoformat();client.post(f"/api/shops/{s['id']}/closings",headers=h,json={'date':today,'actual_cash':'200'})
    health=client.get(f"/api/shops/{s['id']}/shop-health?period=today",headers=h).json();assert health['sales']==800 and health['money_received']==200 and health['cash_review']['dates'][0]['difference']==0
    recovery=client.get(f"/api/shops/{s['id']}/collect-today",headers=h).json();assert recovery['priorities'][0]['outstanding']==600 and recovery['priorities'][0]['why_prioritized']

def test_supplier_price_memory_renames_and_footprint(client,owner):
    h,s=owner;sup=supplier(client,h,s);p=product(client,h,s);url=f"/api/shops/{s['id']}/transactions"
    for price in ('1180','1260'):
        client.post(url,headers=h,json={'type':'purchase','amount':price,'payment_method':'cash','payment_state':'paid','paid_amount':price,'supplier_id':sup['id'],'occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),'items':[{'product_id':p['id'],'quantity':'1','unit_price':price,'cost_price':price}]})
    history=client.get(f"/api/shops/{s['id']}/products/{p['id']}/supplier-prices",headers=h).json();assert [x['unit_price'] for x in history]==[1180,1260] and history[0]['supplier_name_snapshot']=='ABC Distributor'
    changed={k:v for k,v in p.items() if k not in ('id','shop_id','created_at','updated_at')};changed['name']='Sunflower Oil';client.put(f"/api/shops/{s['id']}/products/{p['id']}",headers=h,json=changed)
    client.put(f"/api/shops/{s['id']}/suppliers/{sup['id']}",headers=h,json={'name':'ABC Wholesale','payment_terms':'30 days'});footprint=client.get(f"/api/shops/{s['id']}/suppliers/{sup['id']}/footprint",headers=h).json();assert footprint['products'][0]['previous_price']==1180 and footprint['products'][0]['change']==80 and footprint['supplier']['name']=='ABC Wholesale' and footprint['products'][0]['prices'][0]['supplier_name_snapshot']=='ABC Distributor'

def test_lost_sales_insights_and_audit(client,owner):
    h,s=owner
    for _ in range(3):client.post(f"/api/shops/{s['id']}/lost-sales",headers=h,json={'requested_product':'2L Cooking Oil','quantity':'1','occurred_at':NOW()})
    aggregate=client.get(f"/api/shops/{s['id']}/lost-sales",headers=h).json();assert aggregate[0]['request_count']==3
    generated=client.post(f"/api/shops/{s['id']}/insights/generate",headers=h).json();lost=[x for x in generated if x['type']=='lost_sale'];assert lost and lost[0]['explanation'] and lost[0]['references_json']
    tx(client,h,s);audit=client.get(f"/api/shops/{s['id']}/audit",headers=h).json();assert any(x['entity']=='transaction' and x['after_json'] for x in audit)

def test_phase3_tenant_isolation(client,owner):
    h,s=owner;token=client.post('/api/auth/register',json={'email':'phase3other@example.com','password':'password1','name':'Other'}).json()['access_token'];other={'Authorization':f'Bearer {token}'}
    for path in ('shop-health','cash-review','collect-today','lost-sales','insights','audit'):assert client.get(f"/api/shops/{s['id']}/{path}",headers=other).status_code==404
