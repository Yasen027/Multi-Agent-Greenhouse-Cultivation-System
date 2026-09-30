import time,urllib.request,json
for _ in range(3):
 data=json.dumps({'temperature':35,'humidity':85,'soil_moisture':25,'ph':6.2}).encode(); urllib.request.urlopen(urllib.request.Request('http://localhost:8000/api/sensors/readings',data=data,headers={'Content-Type':'application/json'})); print(urllib.request.urlopen('http://localhost:8000/api/agents/run').read().decode()); time.sleep(2)
