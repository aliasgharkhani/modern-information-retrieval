#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import json
import requests
import re
import sys
import time

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from elasticsearch import Elasticsearch


# In[2]:


paper_ids = []
paper_authors = {}


# In[48]:


def crawler(start_urls, limit):
    process = CrawlerProcess(get_project_settings())
    process.crawl('first', start_urls=start_urls, limit=limit)
    process.start()


# In[4]:


# start = time.time()
# crawler(start_urls = [
#             "https://www.semanticscholar.org/paper/The-Lottery-Ticket-Hypothesis%3A-Training-Pruned-Frankle-Carbin/f90720ed12e045ac84beb94c27271d6fb8ad48cf",
#             "https://www.semanticscholar.org/paper/Attention-is-All-you-Need-Vaswani-Shazeer/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
#             "https://www.semanticscholar.org/paper/BERT%3A-Pre-training-of-Deep-Bidirectional-for-Devlin-Chang/df2b0e26d0599ce3e70df8a9da02e51594e0e992"
#         ], limit=2000)
# print(time.time() - start)


# In[3]:


# res = requests.get('http://localhost:9200')
# print(res.content)


# In[3]:


# def es_iterate_all_documents(es, index, pagesize=350, **kwargs):
#     """
#     Helper to iterate ALL values from
#     Yields all the documents.
#     """
#     offset = 0
#     while True:
#         result = es.search(index=index, **kwargs, body={
#             "size": pagesize,
#             "from": offset
#         })
#         hits = result["hits"]["hits"]
#         # Stop after no more docs
#         if not hits:
#             break
#         # Yield each entry
#         yield from (hit['_source'] for hit in hits)
#         # Continue from there
#         offset += pagesize


# In[4]:


class Index:
    def __init__(self, host, port, data_dir):
        self.es = Elasticsearch([{'host': host, 'port': port}])
        with open(data_dir, encoding="utf8") as json_file:
            self.papers = json.load(json_file)
    def delete(self, index_name='paper_index'):
        self.es.indices.delete(index=index_name, ignore=[400, 404])
    
    def save_data(self, index_name='paper_index'):
        global paper_ids
        for paper in self.papers:
            paper_ids.append(paper['id'])
            paper_authors[paper['id']] = paper['authors']
            self.es.index(index=index_name, id=paper['id'], body=json.dumps({"paper":paper}))


# In[24]:


def calc_alpha(host, port, alpha, index_name='paper_index'):
    es = Elasticsearch([{'host': host, 'port': port}])
    global paper_ids
    p = np.zeros((len(paper_ids), len(paper_ids)))
    aux = np.ones((len(paper_ids), len(paper_ids))) * (1/len(paper_ids))
    for paper_idx, paper_id in enumerate(paper_ids):
        entry = es.get(index_name, id=paper_id)['_source']['paper']
        references = entry.get('references', False)
        if references:
            for reference_id in entry['references']:
                try:
                    reference_idx = paper_ids.index(reference_id)
                    p[reference_idx][paper_idx] = 1
                except ValueError:
                    pass

    sums = np.sum(p, axis=1, keepdims=True)
    p = ((sums > 0) * 1) * (((1 - alpha) * p) / (sums + (sums == 0) * 1) + (alpha * aux))  + ((sums == 0) * 1) * aux
    x = np.ones((len(paper_ids))) * (1/(len(paper_ids)))
    while True:
        aux = x @ p
        if np.all(np.abs(aux - x) < 0.00001):
            break
        x = aux
    p = 0
    aux = 0
    del p
    del aux
    for idx, paper_id in enumerate(paper_ids):
        body = es.get(index_name, id=paper_id)['_source']
        body['paper']['page_rank'] = x[idx]
        response = es.index(index=index_name, id=paper_id, body=body)


# In[90]:


def search(host, port, title, title_weight, abstract, abstract_weight, date, date_weight, use_page_rank, page_rank_weight=0):
    es = Elasticsearch([{'host': host, 'port': port}])
    if use_page_rank:
        search_param = {
            "query": {

                "function_score": {
#                   "query": {
#                       "match_all" : {}
#                   },
                  "functions": [
                    {
                      "filter": {
                        "match_phrase": {
                          "paper.title": title
                        }
                      },
                      "weight": title_weight
                    },
                    {
                      "filter": {
                        "match_phrase": {
                          "paper.abstract": abstract
                        }
                      },
                      "weight": abstract_weight
                    },
                    {
                      "filter": {
                        "range": {
                          "paper.date": {"gte": date}
                        }
                      },
                      "weight": date_weight
                    },
                    {
                        "script_score": {
                            "script": {
                                "source": "_score * saturation(doc['paper.page_rank'].value, 0.0001)"
                                
                            }
                        }
                    },
                  ],
                  "score_mode": "sum", 
                  "boost": "5",
                  "boost_mode": "multiply",

                }

            }  
        }
        response = es.search(index="paper_index", body=search_param, size=10)
        for idx, i in enumerate(response['hits']['hits']):
            paper = i['_source']['paper']
            print(idx, paper['title'], '\n', paper['abstract'], '\n', paper['authors'], '\n', paper['date'])
            print('-' * 60)
        print('*^'*60)
        search_param = {
            "query": {

                "function_score": {
#                   "query": {
#                       "match_all" : {}
#                   },
                  "functions": [
                    {
                      "filter": {
                        "match_phrase": {
                          "paper.title": title
                        }
                      },
                      "weight": title_weight
                    },
                    {
                      "filter": {
                        "match_phrase": {
                          "paper.abstract": abstract
                        }
                      },
                      "weight": abstract_weight
                    },
                    {
                      "filter": {
                        "range": {
                          "paper.date": {"gte": date}
                        }
                      },
                      "weight": date_weight
                    }
                  ],
                  "score_mode": "sum", 
                  "boost": "5",
                  "boost_mode": "multiply",

                }

            },
            "sort": [{ "_score": { "order": "desc" }}],
        }
        response = es.search(index="paper_index", body=search_param, size=10)
        for idx, i in enumerate(response['hits']['hits']):
            paper = i['_source']['paper']
            print(idx, paper['title'], '\n', paper['abstract'], '\n', paper['authors'], '\n', paper['date'])
            print('-' * 60)
    else:
        search_param = {
#             "from" : 0, "size" : 10,

            "query": {

                "function_score": {
#                   "query": {
#                       "match_all" : {}
#                   },
                  "functions": [
                    {
                      "filter": {
                        "match_phrase": {
                          "paper.title": title
                        }
                      },
                      "weight": title_weight
                    },
                    {
                      "filter": {
                        "match_phrase": {
                          "paper.abstract": abstract
                        }
                      },
                      "weight": abstract_weight
                    },
                    {
                      "filter": {
                        "range": {
                          "paper.date": {"gte": date}
                        }
                      },
                      "weight": date_weight
                    }
                  ],
                  "score_mode": "sum", 
                  "boost": "5",
                  "boost_mode": "multiply",

                }

            },
            "sort": [{ "_score": { "order": "desc" }}],   
        }
        response = es.search(index="paper_index", body=search_param, size=10)
        for i in response['hits']['hits']:
            paper = i['_source']['paper']
            print(paper['title'], '\n', paper['abstract'], '\n', paper['authors'], '\n', paper['date'])
            print('-' * 60)


# In[7]:


# index = Index('localhost', 9200, 'papers.json')


# In[25]:


# index.delete()


# In[26]:


# index.save_data()


# In[27]:


# calc_alpha('localhost', 9200, 0.1)


# In[28]:


# es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
# for id in paper_ids:
#     print(es.get(index='paper_index', id=id)['_source']['paper']['page_rank'])


# In[83]:


# search('localhost', 9200, title='Attention is All you Need', title_weight=10, abstract='We propose a novel neural attention', abstract_weight=15, date=2017, date_weight=5, use_page_rank=False)


# In[93]:


# search('localhost', 9200, title='Attention is All you Need', title_weight=10, abstract='We propose a novel neural attention', abstract_weight=15, date=2017, date_weight=5, use_page_rank=True)


# In[60]:


authors_link = {}
authority = {}
hub = {}


# In[65]:


def sort_by_HITS(host, port, authors_number):
    global paper_authors
    es = Elasticsearch([{'host': host, 'port': port}])
    for paper_id in paper_ids:
        paper = es.get('paper_index', paper_id)['_source']['paper']
        references = paper.get('references', False)
        if references:
            for reference_id in references:
                reference_authors = paper_authors.get(reference_id, False)
                if reference_authors:
                    for reference_author in reference_authors:
                        author = authors_link.get(reference_author, False)
                        if author:
                            authors_link[reference_author] = author.union(paper.get('authors', None))
                        else:
                            authors_link[reference_author] = set(paper.get('authors', None))
                            
    for i in range(5):
        for author, r_authors in authors_link.items():
            aux = authority.get(author, False)
            if not aux:
                authority[author] = 1
            for r_author in r_authors:
                authority[author] += hub.get(r_author, 1)
        for author, r_authors in authors_link.items():
            for r_author in r_authors:
                aux = hub.get(r_author, False)
                if not aux:
                    hub[r_author] = 1
                hub[r_author] += authority.get(author, 1)
    for k, v in sorted(authority.items(), key=lambda item: item[1], reverse=True)[:authors_number]:
        print(k, v)


# In[66]:


# sort_by_HITS('localhost', 9200, 10)


# In[78]:


while True:
    print('choose one of these:\n 1.crawl\n 2.indexing\n 3.evaluating papers\n 4.search\n 5.sort authors by HITS\n 6.exit')
    order = int(input())
    if order == 1:
        start_urls = []
        print('enter start urls one by one and then press enter')
        for i in range(3):
            print('url number {}'.format(i+1), end='')
            start_urls.append(input())
        print('enter number of papers you want to crawl')
        print('limit:', end='')
        crawl_limit = int(input())
        crawler(start_urls = start_urls, limit=crawl_limit)
    elif order == 2:
        print('enter address of json file')
        json_addr = input()
        print('first enter host address then enter port on which elasticsearch is running')
        print('host:', end='')
        host = input()
        print('port:', end='')
        port = int(input())
        index = Index(host, port, json_addr)
        while True:
            print('to save data in elasticsrach enter 1\nto delete data saved in elasticsearch press 2\nto exit this mode press 3')
            sub_order = int(input())
            if sub_order == 1:
                index.save_data()
            elif sub_order == 2:
                index.delete()
            elif sub_order == 3:
                break
    elif order == 3:
        print('enter host and port of server and then value of alpha you want to be applied')
        print('host:', end='')
        host = input()
        print('port:', end='')
        port = int(input())
        print('alpha:', end='')
        alpha = float(input())
        calc_alpha(host, port, alpha)
    elif order == 4:
        print('enter host and port of server and then weights and values of fields. At the end specify if you want page rank to have an effect on the results or not')
        print('host:', end='')
        host = input()
        print('port:', end='')
        port = int(input())
        print('title weight:', end='')
        title_weight = int(input())
        print('title:', end='')
        title = input()
        print('abstract weight:', end='')
        abstract_weight = int(input())
        print('abstract:', end='')
        abstract = input()
        print('date weight:', end='')
        date_weight = int(input())
        print('date:', end='')
        date = input()
        print('page rank effect: y or n', end='')
        use_page_rank = True if input() == 'y' else False
        search(host, port, title, title_weight, abstract, abstract_weight, date, date_weight, use_page_rank)
    elif order == 5:
        print('enter host and port of server and number of authors you want to be returned')
        print('host:', end='')
        host = input()
        print('port:', end='')
        port = int(input())    
        print('authors number:', end='')
        authors_number = int(input())   
        sort_by_HITS(host, port, authors_number)
    elif order == 6:
        break

