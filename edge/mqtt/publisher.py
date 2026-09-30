import json,time,random,urllib.request
def sample(): return {'temperature':round(random.uniform(20,35),1),'humidity':round(random.uniform(50,85),1),'soil_moisture':round(random.uniform(25,60),1),'ph':6.2}
if __name__=='__main__':
 while True:
  data=json.dumps(sample()).encode(); req=urllib.request.Request('http://localhost:8000/api/sensors/readings',data=data,headers={'Content-Type':'application/json'}); urllib.request.urlopen(req); time.sleep(5)
