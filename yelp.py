# imports
from flask import Flask, render_template, request, session, flash, redirect, url_for, g
app = Flask(__name__)
from yelpapi import YelpAPI
from textblob import TextBlob
import os
import sys
import urllib2
from bs4 import BeautifulSoup
from textblob import TextBlob
from textblob.np_extractors import ConllExtractor
import requests
import json
import requests
import json
import thread


class ZeusClient():
    def __init__(self, user_token, server):
        self.token = user_token
        if not server.startswith('http://'):
            self.server = 'http://' + server
        else:
            self.server = server

    def _sendRequest(self, method, path, data):
        if method == 'POST':
            r = requests.post(self.server + path, data=data)
        elif method == 'GET':
            r = requests.get(self.server + path, params=data)

        return r.status_code, r.json()

    def sendLog(self, log_name, logs):
        data = {'logs': json.dumps(logs)}
        return self._sendRequest('POST', '/logs/' + self.token + '/' + log_name + '/', data)

    def sendMetric(self, metric_name, metrics):
        data = {'metrics': json.dumps(metrics)}
        return self._sendRequest('POST', '/metrics/' + self.token + '/' + metric_name + '/', data)

    def getLog(self, log_name, pattern=None, from_date=None, to_date=None, offset=None, limit=None):
        data = {"log_name": log_name}
        if pattern:
            data['pattern'] = pattern
        if from_date:
            data['from'] = from_date
        if to_date:
            data['to'] = to_date
        if offset:
            data['offset'] = offset
        if limit:
            data['limit'] = limit

        return self._sendRequest('GET', '/logs/' + self.token + '/', data)

    def getMetric(self, metric_name=None, from_date=None, to_date=None, aggregator=None, group_interval=None, filter_condition=None, limit=None):
        data = {}
        if metric_name:
            data['metric_name'] = metric_name
        if from_date:
            data['from'] = from_date
        if to_date:
            data['to'] = to_date
        if aggregator:
            # EG. 'sum'
            data['aggregator_function'] = aggregator
        if group_interval:
            # EG. '1m'
            data['group_interval'] = group_interval
        if filter_condition:
            # EG. '"Values" < 33'
            data['filter_condition'] = filter_condition
        if limit:
            data['limit'] = limit

        return self._sendRequest('GET', '/metrics/' + self.token + '/_values/', data)

    def getMetricNames(self, metric_name=None, limit=None):
        data = {}
        if metric_name:
            data['metric_name'] = metric_name
        if limit:
            data['limit'] = limit

        return self._sendRequest('GET', '/metrics/' + self.token + '/_names/', data)

token = "8d94a705"
ZEUS_API = "http://api.ciscozeus.io"
def get_data(cuisine,exact):
	extractor = ConllExtractor()
	z = ZeusClient(token, ZEUS_API)

	results = z.getLog(log_name=cuisine,pattern=exact,limit=1000)
	print results

	final = {}
	for a in results[1]["result"]:
		temp = a["message"].encode('utf-8')
		temp = temp.decode('utf-8')
		try:
			msg = json.loads(temp)
			temp = msg["review"]
			blob = TextBlob(temp)
			sum = 0
			for sentence in blob.sentences:
				if(exact in sentence):
					tempBlob = TextBlob(str(sentence), np_extractor=extractor)
					sum = sum + sentence.sentiment.polarity
			if msg["place"] in final:
				final[msg["place"]] = final[msg["place"]] + sum
			else:
				final[msg["place"]] = sum
		except:
			msg = json.loads(temp)
			print "EXCEPTION "+ temp
	
	highest = -1
	result = ""
	if(final == {}):
		return ""
	for a in final:
		if final[a] > highest:
			highest = final[a]
			result = a
	return a

def push_data(cuisine):
	extractor = ConllExtractor()
	yelp_api = YelpAPI("0pRydQVhN7EVGgVZxF0CYw", "cgCgl6pXU04_Bya3jSYTkQ7L9xg", "ra80mM7vutSmCR-Mu4_R3q6cc1IUadfV", "YB5nl71NKh7pFRrFPCLuDKFADFg")
	z = ZeusClient(token, ZEUS_API)
	response = yelp_api.search_query(term=cuisine, location='San Jose, CA', sort=2, limit=10)
	for business in response['businesses']:
	    name = str(business["name"])
	    print name
	    name = name.replace(" ","-")
	    name = name + "-san-jose"
	
	    url = "http://www.yelp.com/biz/" + name
	    print url
	    user_agent = "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)" # Or any valid user agent from a real browser
	    headers = {"User-Agent": user_agent}
	    try:
	        req = urllib2.Request(url, headers=headers)
	        res = urllib2.urlopen(req)
	    except:
	        continue
	    parsed_html = BeautifulSoup(res.read())
	    for x in parsed_html.find_all('div', {"class":"page-of-pages"}):
	        print x.text
	        temp = x.text.strip()
	        temp.strip()
	        temp  = temp.split(" ")
	        pages = temp[len(temp)-1]
	        print pages
	    count = 0
	    rating = -1
	    for i in range(int(pages)):
	        urltemp = url + "?start=" + str(i*40)
	        print urltemp
	        user_agent = "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)" # Or any valid user agent from a real browser
	        headers = {"User-Agent": user_agent}
	        req = urllib2.Request(urltemp, headers=headers)
	        res = urllib2.urlopen(req)
	        parsed_html = BeautifulSoup(res.read())
	     
	        for x in parsed_html.find_all("p", itemprop="description"): 
	            temp = x.text.replace("'","")
	            temp = temp.replace('"',"")
	            messages = [{"message":'{"review":"'+temp+'","place":"'+business["name"]+'"}'}]
	            print str(z.sendLog(cuisine, messages))
	            
@app.route('/', methods=['GET','POST'])
def get_resturant():
	print request.method
	if request.method == 'POST':
		cuisine = request.form["cuisine"]
		thread.start_new_thread(push_data,(cuisine,))
		dish = request.form['pass']  
		result = get_data(cuisine,dish).replace("}","")
		return render_template('result.html',message=result)
	else:
		return render_template('landing.html')

if __name__ == '__main__': 
	app.debug = True
	app.run(host='0.0.0.0',port = 5000)
