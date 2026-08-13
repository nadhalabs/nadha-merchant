from datetime import date,datetime,timezone
import uuid
NOW=lambda:datetime.now(timezone.utc).isoformat()
def test_complete_shop_workflow(client):
    token=client.post('/api/auth/register',json={'email':'demo@nadha.in','password':'demopass1','name':'Anita'}).json()['access_token'];h={'Authorization':f'Bearer {token}'};s=client.post('/api/shops',headers=h,json={'name':'Anita General Store'}).json();base=f"/api/shops/{s['id']}"
    def make_product(name,tracked=False):return client.post(base+'/products',headers=h,json={'name':name,'unit':'piece','buy_price':'100','sell_price':'130','inventory_enabled':tracked,'active':True}).json()
    def tx(body,p=None,quantity='1',price=None):
        payload={'occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),**body};payload['items']=[] if body['type']=='expense' else [{'product_id':(p or make_product(str(uuid.uuid4())))['id'],'quantity':quantity,'unit_price':price or body['amount'],'cost_price':'100'}]
        r=client.post(base+'/transactions',headers=h,json=payload);assert r.status_code==201,r.text;return r.json()
    tx({'type':'sale','amount':'500','payment_method':'cash'});tx({'type':'sale','amount':'300','payment_method':'upi'})
    customer=client.post(base+'/customers',headers=h,json={'name':'Ravi'}).json();tx({'type':'sale','amount':'800','payment_method':'credit','customer_id':customer['id']});client.post(base+f"/customers/{customer['id']}/payments",headers=h,json={'amount':'200','payment_method':'cash','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())})
    supplier=client.post(base+'/suppliers',headers=h,json={'name':'ABC Distributor'}).json();tracked=make_product('Sunflower Oil',True);purchase=tx({'type':'purchase','amount':'1000','payment_method':'credit','payment_state':'due','paid_amount':'0','supplier_id':supplier['id']},tracked,'10','100');client.post(base+f"/suppliers/{supplier['id']}/payments",headers=h,json={'amount':'250','payment_method':'cash','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())});tx({'type':'expense','amount':'100','payment_method':'cash','category':'Transport'})
    client.post(base+'/closings',headers=h,json={'date':date.today().isoformat(),'actual_cash':'400','idempotency_key':str(uuid.uuid4())});later=tx({'type':'sale','amount':'260','payment_method':'cash'},tracked,'2','130')
    assert client.get(base+'/inventory',headers=h).json()[0]['stock']==8;assert client.get(base+'/profit',headers=h).status_code==200;assert client.get(base+'/collect-today',headers=h).json()['priorities'];assert client.get(base+f"/products/{tracked['id']}/supplier-prices",headers=h).json();assert len(client.get(base+'/audit',headers=h).json())>=8
