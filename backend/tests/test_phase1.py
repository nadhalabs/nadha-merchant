from datetime import datetime, timezone

def tx(client, headers, shop, **values):
    body = {'type':'sale','amount':'100.00','payment_method':'cash','occurred_at':datetime.now(timezone.utc).isoformat(), **values}
    return client.post(f"/api/shops/{shop['id']}/transactions", headers=headers, json=body)

def person(client, headers, shop, kind, name):
    return client.post(f"/api/shops/{shop['id']}/{kind}", headers=headers, json={'name':name}).json()

def test_auth_and_tenant_isolation(client, owner):
    headers, shop = owner
    assert client.get(f"/api/shops/{shop['id']}").status_code == 401
    token = client.post('/api/auth/register', json={'email':'other@example.com','password':'password1','name':'Other'}).json()['access_token']
    other = {'Authorization': f'Bearer {token}'}
    assert client.get(f"/api/shops/{shop['id']}", headers=other).status_code == 404
    assert tx(client, other, shop).status_code == 404

def test_all_transaction_types_and_edit(client, owner):
    headers, shop = owner
    customer = person(client, headers, shop, 'customers', 'Ravi')
    supplier = person(client, headers, shop, 'suppliers', 'Wholesale Co')
    for method in ('cash','upi'):
        assert tx(client,headers,shop,payment_method=method).status_code == 201
    assert tx(client,headers,shop,payment_method='credit',customer_id=customer['id']).status_code == 201
    assert tx(client,headers,shop,payment_method='mixed',customer_id=customer['id'],cash_amount='30',upi_amount='20').status_code == 201
    for state, paid in [('paid','100'),('due','0'),('partial','40')]:
        assert tx(client,headers,shop,type='purchase',payment_method='cash',payment_state=state,paid_amount=paid,supplier_id=supplier['id']).status_code == 201
    expense = tx(client,headers,shop,type='expense',category='Rent',payment_method='cash')
    assert expense.status_code == 201
    body = {**expense.json(), 'amount':'125.00'}
    for key in ('id','shop_id','created_at','updated_at'): body.pop(key)
    result = client.put(f"/api/shops/{shop['id']}/transactions/{expense.json()['id']}",headers=headers,json=body)
    assert result.json()['amount'] == '125.00'

def test_customer_ledger_and_transaction_rebuild(client, owner):
    headers, shop = owner
    customer = person(client,headers,shop,'customers','Meera')
    sale = tx(client,headers,shop,amount='500',payment_method='credit',customer_id=customer['id']).json()
    url = f"/api/shops/{shop['id']}/customers/{customer['id']}"
    assert client.get(url,headers=headers).json()['balance'] == 500
    client.post(url+'/payments',headers=headers,json={'amount':'150','occurred_at':datetime.now(timezone.utc).isoformat()})
    detail=client.get(url,headers=headers).json()
    assert detail['balance']==350 and detail['entries'][-1]['running_balance']==350
    body={k:v for k,v in sale.items() if k not in ('id','shop_id','created_at','updated_at')};body['amount']='400'
    client.put(f"/api/shops/{shop['id']}/transactions/{sale['id']}",headers=headers,json=body)
    assert client.get(url,headers=headers).json()['balance']==250

def test_supplier_ledger_dashboard_and_closing(client, owner):
    headers, shop = owner
    supplier=person(client,headers,shop,'suppliers','Dealer')
    tx(client,headers,shop,type='purchase',amount='600',payment_method='cash',payment_state='partial',paid_amount='200',supplier_id=supplier['id'])
    url=f"/api/shops/{shop['id']}/suppliers/{supplier['id']}"
    assert client.get(url,headers=headers).json()['balance']==400
    client.post(url+'/payments',headers=headers,json={'amount':'100','occurred_at':datetime.now(timezone.utc).isoformat()})
    assert client.get(url,headers=headers).json()['balance']==300
    tx(client,headers,shop,amount='1000',payment_method='cash')
    assert client.get(f"/api/shops/{shop['id']}/dashboard",headers=headers).json()['sales']==1000
    today=datetime.now().date().isoformat()
    assert client.post(f"/api/shops/{shop['id']}/closings",headers=headers,json={'date':today,'actual_cash':'800'}).status_code==201
    assert len(client.get(f"/api/shops/{shop['id']}/closings",headers=headers).json())==1
