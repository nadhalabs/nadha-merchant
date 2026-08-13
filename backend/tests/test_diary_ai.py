from datetime import datetime,timezone
import uuid
from app.database import SessionLocal
from app.models import Shop
NOW=lambda:datetime.now(timezone.utc).isoformat()
def test_product_free_business_diary_and_notes(client,owner):
    h,s=owner;base=f"/api/shops/{s['id']}";customer=client.post(base+'/customers',headers=h,json={'name':'Rahul'}).json();supplier=client.post(base+'/suppliers',headers=h,json={'name':'ABC'}).json()
    key=str(uuid.uuid4());sale={'type':'sale','amount':'1000','payment_method':'credit','customer_id':customer['id'],'occurred_at':NOW(),'idempotency_key':key,'items':[{'item_name':'Dettol','quantity':'2'}]};a=client.post(base+'/transactions',headers=h,json=sale);b=client.post(base+'/transactions',headers=h,json=sale);assert a.status_code==201 and a.json()['id']==b.json()['id']
    purchase={'type':'purchase','amount':'5000','payment_method':'credit','payment_state':'due','paid_amount':'0','supplier_id':supplier['id'],'occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),'items':[]};assert client.post(base+'/transactions',headers=h,json=purchase).status_code==201
    client.post(base+f"/customers/{customer['id']}/payments",headers=h,json={'amount':'400','payment_method':'cash','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())});client.post(base+f"/suppliers/{supplier['id']}/payments",headers=h,json={'amount':'1000','payment_method':'upi','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4())})
    client.post(base+'/transactions',headers=h,json={'type':'expense','amount':'50','payment_method':'cash','category':'Tea','occurred_at':NOW(),'idempotency_key':str(uuid.uuid4()),'items':[]})
    before=client.get(base+'/dashboard',headers=h).json();client.post(base+'/diary/notes',headers=h,json={'text':'Rahul will pay Friday','occurred_at':NOW()});after=client.get(base+'/dashboard',headers=h).json();assert before==after
    events=client.get(base+'/diary',headers=h).json();codes=[x['event_code'] for x in events];assert codes.count('sale.created')==1
    for code in ('purchase.created','expense.created','customer_payment.created','supplier_payment.created','note.created'):assert code in codes
    assert client.get(base+'/diary?search=Dettol',headers=h).json()[0]['event_code']=='sale.created'
def test_people_edit_diary_and_ai_tenant_entitlement(client,owner):
    h,s=owner;base=f"/api/shops/{s['id']}";c=client.post(base+'/customers',headers=h,json={'name':'Old'}).json();assert client.put(base+f"/customers/{c['id']}",headers=h,json={'name':'New','phone':'123','notes':'note'}).json()['name']=='New';assert any(x['event_code']=='customer.edited' for x in client.get(base+'/diary',headers=h).json())
    assert client.post(base+'/ai/ask',headers=h,json={'question':'Who owes me most?','language':'en'}).status_code==403
    token=client.post('/api/auth/register',json={'email':'diary-other@example.com','password':'password1','name':'Other'}).json()['access_token'];other={'Authorization':f'Bearer {token}'};assert client.get(base+'/diary',headers=other).status_code==404;assert client.post(base+'/ai/ask',headers=other,json={'question':'Show data','language':'en'}).status_code==404
    with SessionLocal() as db:shop=db.get(Shop,uuid.UUID(s['id']));shop.ai_enabled=True;db.commit()
    answer=client.post(base+'/ai/ask',headers=h,json={'question':'Who owes me most?','language':'en'});assert answer.status_code==200 and answer.json()['available'] is False
