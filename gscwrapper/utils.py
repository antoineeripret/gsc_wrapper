from datetime import datetime, timedelta
import requests
import xml.etree.ElementTree as ET
import validators


#function to get a response code 
def get_response_code(url):
    try:
        response = requests.head(url)
        return response.status_code
    except: 
        return 'Impossible to get the response code'

def get_date_days_ago(days=30):
    today = datetime.now()
    thirty_days_ago = today - timedelta(days)
    return thirty_days_ago.date()
    
#function to get the date X days before another date 
def get_date_days_before(date, days):
    date = datetime.strptime(date, '%Y-%m-%d')
    #get the date X days before date 
    new_date = date - timedelta(days)
    return new_date.strftime('%Y-%m-%d')

def create_n_grams(text, n=2):
    words = text.split()
    n_grams = zip(*[words[i:] for i in range(n)])
    return [' '.join(n_gram) for n_gram in n_grams]

def fetch_sitemap_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Error fetching the sitemap: {e}")
        return None

def parse_sitemap(content):
    # Parse the XML content
    root = ET.fromstring(content)
    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    # Check if it's a sitemap index
    if root.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex':
        # Extract sitemap links from the index
        sitemap_links = [elem.text for elem in root.findall('sitemap:sitemap/sitemap:loc', namespace)]
        urls = []
        for link in sitemap_links:
            sitemap_content = fetch_sitemap_content(link)
            if sitemap_content:
                urls.extend(parse_sitemap(sitemap_content))
        return urls
    else:
        # Extract URLs from the regular sitemap
        return [url.text for url in root.findall('sitemap:url/sitemap:loc', namespace)]

def get_urls_from_sitemap(sitemap_url):
    sitemap_content = fetch_sitemap_content(sitemap_url)
    if sitemap_content:
        return parse_sitemap(sitemap_content)
    else:
        return []
    

#function to ensure that we have a proper value for the sitemap url 
def check_sitemap_url(sitemap_url):
    #check that we have an URL
    if validators.url(sitemap_url) == False:
        raise ValueError('Please provide a valid URL.')
    if not sitemap_url.endswith('.xml'):
        raise ValueError('The sitemap URL provided is not valid. Only XML files are supported.')
    return True 


def are_dates_parsable(date_list, date_format="%Y-%m-%d"):
    parsable_dates = []
    for date_str in date_list:
        try:
            # Try to parse the date
            datetime.strptime(date_str, date_format)
            parsable_dates.append(True)
        except ValueError:
            # If parsing fails, the date is not parsable
            parsable_dates.append(False)
    return parsable_dates


##### DATAFORSEO #####
from http.client import HTTPSConnection
from base64 import b64encode
from json import loads
from json import dumps
import pandas as pd 
import time 

class RestClient:
    domain = "api.dataforseo.com"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def request(self, path, method, data=None):
        connection = HTTPSConnection(self.domain)
        try:
            base64_bytes = b64encode(
                ("%s:%s" % (self.username, self.password)).encode("ascii")
                ).decode("ascii")
            headers = {'Authorization' : 'Basic %s' %  base64_bytes, 'Content-Encoding' : 'gzip'}
            connection.request(method, path, headers=headers, body=data)
            response = connection.getresponse()
            return loads(response.read().decode())
        finally:
            connection.close()

    def get(self, path):
        return self.request(path, 'GET')

    def post(self, path, data):
        if isinstance(data, str):
            data_str = data
        else:
            data_str = dumps(data)
        return self.request(path, 'POST', data_str)


def return_chunks(keywords):
    clean_keywords = []
    #loop list of keywords 
    for keyword in keywords:
        #basic check otherwise we can't get search volume 
        if len(keyword) <= 80 and len(keyword.split(" ")) <= 10:
            #remove special characters 
            for symbol in ["–",":","n°","-","’","&",",","!","@","%","^","(",")","=","{","}",";","~","`","<",">","?","\\","|","―"]:
                keyword = keyword.replace(symbol, "")
            clean_keywords.append(keyword)
    #convert clean_keywords into chunks of 1000 keywords 
    return [clean_keywords[i:i+1000] for i in range(0, len(clean_keywords), 1000)]

def create_jobs_and_get_ids(chunks, tag, location, client):
    print('loading data ... ')
    dataforseo_data = []
    task_ids = []
    for chunk in chunks:
        post_data = dict()
        # simple way to set a task
        post_data[len(post_data)] = dict(
            keywords=chunk,
            tag=tag, 
            location=location
        )
        dataforseo_data.append(post_data)

    for post_data in dataforseo_data:
        # POST /v3/keywords_data/google_ads/search_volume/task_post
        response = client.post("/v3/keywords_data/google_ads/search_volume/task_post", post_data)
        # you can find the full list of the response codes here https://docs.dataforseo.com/v3/appendix/errors
        if response["status_code"] == 20000:
            task_ids.append(response["tasks"][0]["id"])
            pass
        else:
            print("error. Code: %d Message: %s" % (response["status_code"], response["status_message"]))
    
    return task_ids

def get_search_volume(jobs_id, client):
    #boolean to control the wile loop 
    all_available = False 
    #wait a couple of seconds before checking if the data is available
    print('Waiting a couple of seconds before checking if the data is available...')
    time.sleep(15)
    while all_available == False:
        #get all available data 
        response = client.get("/v3/keywords_data/google_ads/search_volume/tasks_ready")
        #get the data as a dataframe
        response_df = pd.DataFrame(response["tasks"][0]['result'])
        #check if we have all IDs we created before 
        if all(element in response_df.id.unique() for element in jobs_id):
            all_available = True
        else:
            #if that's not the case, wait a couple of seconds before trying again 
            print('data not available yet. Will try again in 15 seconds! Do not stop the execution.')
            time.sleep(15)
                
    #download the data 
    print('') 
    print('downloading data...')
    results = []
    for task in response['tasks']:
        if (task['result'] and (len(task['result']) > 0)):
            for resultTaskInfo in task['result']:
                if(resultTaskInfo['id']):
                    results.append(client.get("/v3/keywords_data/google_ads/search_volume/task_get/" + resultTaskInfo['id']))

        #get the data as a dataframe 
        df = pd.DataFrame()
        for result in results:
            df = pd.concat([df,pd.DataFrame(result['tasks'][0]['result'])])
            
    return df 

