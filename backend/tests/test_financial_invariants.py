from datetime import datetime,timezone,timedelta
import uuid

NOW=lambda:datetime.now(timezone.utc).isoformat()
def add(client,h,s,body):
    body={"occurred_at":NOW(),**body,"idempotency_key":str(uuid.uuid4())}
    if body['type']!='expense':
        p=client.post(f"/api/shops/{s['id']}/products",headers=h,json={'name':f'Item {uuid.uuid4()}','unit':'piece','active':True,'inventory_enabled':False}).json();body['items']=[{'product_id':p['id'],'quantity':'1','unit_price':body['amount']}]
    r=client.post(f"/api/shops/{s['id']}/transactions",headers=h,json=body);assert r.status_code==201,r.text;return r.json()
def person(client,h,s,kind,name):return client.post(f"/api/shops/{s['id']}/{kind}",headers=h,json={"name":name}).json()
def dash(client,h,s,day=None):return client.get(f"/api/shops/{s['id']}/dashboard"+(f"?day={day}" if day else ""),headers=h).json()

def test_release_invariants_credit_sale_and_later_collections(client,owner):
    h,s=owner;c=person(client,h,s,"customers","Rahul")
    add(client,h,s,{"type":"sale","amount":"1000","payment_method":"credit","customer_id":c["id"]})
    d=dash(client,h,s);assert d["sales_total"]==1000 and d["money_received"]==0 and d["credit_given"]==1000
    assert client.get(f"/api/shops/{s['id']}/customers/{c['id']}",headers=h).json()["balance"]==1000
    url=f"/api/shops/{s['id']}/customers/{c['id']}/payments";body={"amount":"400","payment_method":"cash","occurred_at":NOW(),"idempotency_key":"collect-rahul-400"}
    assert client.post(url,headers=h,json=body).status_code==201;assert client.post(url,headers=h,json=body).status_code==201
    d=dash(client,h,s);assert d["sales_total"]==1000 and d["money_received"]==400 and d["credit_collected"]==400
    assert client.get(f"/api/shops/{s['id']}/customers/{c['id']}",headers=h).json()["balance"]==600
    assert client.post(url,headers=h,json={"amount":"600","payment_method":"upi","occurred_at":NOW(),"idempotency_key":"collect-final"}).status_code==201
    assert client.get(f"/api/shops/{s['id']}/customers/{c['id']}",headers=h).json()["balance"]==0

def test_release_invariants_unpaid_partial_purchase_and_supplier_payment(client,owner):
    h,s=owner;p=person(client,h,s,"suppliers","ABC")
    add(client,h,s,{"type":"purchase","amount":"5000","payment_state":"due","paid_amount":"0","payment_method":"credit","supplier_id":p["id"]})
    d=dash(client,h,s);assert d["purchase_total"]==5000 and d["money_paid"]==0 and d["cash_paid"]==0
    assert client.get(f"/api/shops/{s['id']}/suppliers/{p['id']}",headers=h).json()["balance"]==5000
    pay={"amount":"2000","payment_method":"cash","occurred_at":NOW(),"idempotency_key":"supplier-2000"};client.post(f"/api/shops/{s['id']}/suppliers/{p['id']}/payments",headers=h,json=pay)
    d=dash(client,h,s);assert d["purchase_total"]==5000 and d["supplier_payments"]==2000 and d["money_paid"]==2000
    assert client.get(f"/api/shops/{s['id']}/suppliers/{p['id']}",headers=h).json()["balance"]==3000

def test_sales_mix_and_partial_purchase(client,owner):
    h,s=owner;c=person(client,h,s,"customers","Meera");p=person(client,h,s,"suppliers","Dealer")
    add(client,h,s,{"type":"sale","amount":"1000","payment_method":"cash"});add(client,h,s,{"type":"sale","amount":"2000","payment_method":"upi"});add(client,h,s,{"type":"sale","amount":"3000","payment_method":"credit","customer_id":c["id"]})
    add(client,h,s,{"type":"purchase","amount":"10000","payment_state":"partial","paid_amount":"4000","payment_method":"upi","supplier_id":p["id"]})
    d=dash(client,h,s);assert d["sales_total"]==6000 and d["money_received"]==3000 and d["credit_given"]==3000
    assert d["purchase_total"]==10000 and d["upi_paid"]==4000 and client.get(f"/api/shops/{s['id']}/suppliers/{p['id']}",headers=h).json()["balance"]==6000

def test_ist_business_date_boundary(client,owner):
    h,s=owner
    add(client,h,s,{"type":"sale","amount":"10","payment_method":"cash","occurred_at":"2026-08-12T18:29:00Z"})
    add(client,h,s,{"type":"sale","amount":"20","payment_method":"cash","occurred_at":"2026-08-12T18:31:00Z"})
    assert dash(client,h,s,"2026-08-12")["sales_total"]==10
    assert dash(client,h,s,"2026-08-13")["sales_total"]==20
