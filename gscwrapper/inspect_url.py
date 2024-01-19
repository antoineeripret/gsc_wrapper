import time 
import pandas as pd

class Inspect: 
    def __init__(self, service, webproperty):
        self.service = service
        self.webproperty = webproperty
        self.urls_to_inspect = []
        self.raw = {
            "inspectionUrl": "",
            "siteUrl": self.webproperty,
        }
        self.results = []
    
    def add_urls(self, urls):
        import validators
        
        for element in urls:
            #check that we have a valid URL 
            if not validators.url(element):
                raise ValueError(f'{element} is not a valid URL')
        self.urls_to_inspect.extend(urls)
        return self 
    
    
    def remove_urls(self, urls):
        self.urls_to_inspect = [url for url in self.urls_to_inspect if url not in urls]
        return self
    
    def len(self):
        return len(self.urls_to_inspect)
    
    def execute(self):
        import googleapiclient.errors
        from tqdm import tqdm
        
        urls_to_check = self.urls_to_inspect.copy()
        self.results = []
        try: 
            for url in tqdm(list(dict.fromkeys(urls_to_check))):
                time.sleep(1)
                self.raw = {
                        "inspectionUrl": url,
                        "siteUrl": self.webproperty,
                    }
                response = (
                    self.webproperty.service.urlInspection()
                    .index()
                    .inspect(body=self.raw)
                    .execute()
                )
                ret = response.get('inspectionResult')
                # Appending the URL inspected as it is not returned back from
                # the API and it will facilite bulk reporting
                ret.update({'inspectionUrl': self.raw.get('inspectionUrl')})
                self.results.append(ret)

        except googleapiclient.errors.HttpError as e:
            raise e
        return pd.json_normalize(self.results)