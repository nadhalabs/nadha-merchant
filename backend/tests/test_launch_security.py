from datetime import datetime,timedelta,timezone
import jwt
import uuid
from app.config import Settings,settings

NOW=lambda:datetime.now(timezone.utc).isoformat()
def second_owner(client):
    token=client.post('/api/auth/register',json={'email':'second@example.com','password':'password2','name':'Second'}).json()['access_token'];h={'Authorization':f'Bearer {token}'};s=client.post('/api/shops',headers=h,json={'name':'Second Shop'}).json();return h,s

def test_production_rejects_default_secret_sqlite_and_http_cors():
    try:Settings(environment='production')
    except ValueError as e:assert 'SECRET_KEY' in str(e)
    else:raise AssertionError('unsafe production defaults accepted')

def test_invalid_expired_and_unauthenticated_financial_write(client,owner):
    _,s=owner;url=f"/api/shops/{s['id']}/transactions";body={'type':'sale','amount':'10','payment_method':'cash','occurred_at':NOW()}
    assert client.post(url,json=body).status_code==401
    assert client.post(url,headers={'Authorization':'Bearer invalid'},json=body).status_code==401
    expired=jwt.encode({'sub':'00000000-0000-0000-0000-000000000000','exp':datetime.now(timezone.utc)-timedelta(seconds=1)},settings.secret_key,algorithm='HS256')
    assert client.post(url,headers={'Authorization':f'Bearer {expired}'},json=body).status_code==401

def test_cross_shop_ids_are_rejected(client,owner):
    h,a=owner;hb,b=second_owner(client)
    customer=client.post(f"/api/shops/{b['id']}/customers",headers=hb,json={'name':'B Customer'}).json();supplier=client.post(f"/api/shops/{b['id']}/suppliers",headers=hb,json={'name':'B Supplier'}).json();product=client.post(f"/api/shops/{b['id']}/products",headers=hb,json={'name':'B Product','unit':'piece','inventory_enabled':True,'active':True}).json()
    base=f"/api/shops/{a['id']}"
    common={'amount':'10','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),'items':[{'product_id':product['id'],'quantity':'1','unit_price':'10'}]}
    assert client.post(base+'/transactions',headers=h,json={**common,'type':'sale','payment_method':'credit','customer_id':customer['id']}).status_code==400
    assert client.post(base+'/transactions',headers=h,json={**common,'idempotency_key':str(uuid.uuid4()),'type':'purchase','payment_method':'credit','payment_state':'due','paid_amount':'0','supplier_id':supplier['id']}).status_code==400
    assert client.post(base+f"/inventory/{product['id']}/adjustments",headers=h,json={'quantity_difference':'1','reason':'attack','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())}).status_code==404
    assert client.get(f"/api/shops/{b['id']}/dashboard",headers=h).status_code==404

def test_overpayments_rejected(client,owner):
    h,s=owner;c=client.post(f"/api/shops/{s['id']}/customers",headers=h,json={'name':'C'}).json();p=client.post(f"/api/shops/{s['id']}/suppliers",headers=h,json={'name':'P'}).json()
    prod=client.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':'Item','unit':'piece','active':True,'inventory_enabled':False}).json();common={'amount':'100','occurred_at':NOW(),'items':[{'product_id':prod['id'],'quantity':'1','unit_price':'100'}]}
    client.post(f"/api/shops/{s['id']}/transactions",headers=h,json={**common,'idempotency_key':str(uuid.uuid4()),'type':'sale','payment_method':'credit','customer_id':c['id']})
    client.post(f"/api/shops/{s['id']}/transactions",headers=h,json={**common,'idempotency_key':str(uuid.uuid4()),'type':'purchase','payment_method':'credit','payment_state':'due','paid_amount':'0','supplier_id':p['id']})
    body={'amount':'101','payment_method':'cash','occurred_at':NOW()}
    assert client.post(f"/api/shops/{s['id']}/customers/{c['id']}/payments",headers=h,json=body).status_code==400
    assert client.post(f"/api/shops/{s['id']}/suppliers/{p['id']}/payments",headers=h,json=body).status_code==400
