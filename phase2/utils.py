from nltk.stem import WordNetLemmatizer
from functools import partial
import numpy as np
import numba as nb
import math
from numba import njit
import pickle
from tqdm import tqdm
import nltk
import re
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.stem import PorterStemmer

class TermPosition:
    title = "title"
    body = "body"

class Term:
    def __init__(self, term, doc_id, position, category):
        self.term = term
        self.posting_list = {doc_id:{position:1}}
        self.count_in_categories = {1:0, 2:0, 3:0, 4:0}
        self.count_in_categories[category] = 1
    def add_doc(self, doc_id, position, category):
        self.count_in_categories[category] += 1
        doc = self.posting_list.get(doc_id, False)
        if doc:
            tf = doc.get(position, False)
            if tf:
                doc[position] += 1
            else:
                doc[position] = 1
        else:
            self.posting_list[doc_id] = {position:1}


def insert_in_index(index, term, doc_id, position, category): 
    term_in_index = index.get(term, False)
    if not term_in_index:
        index[term] = Term(term, doc_id, position, category)
        return
    index[term].add_doc(doc_id, position, category) 


def save_pickle(file_name, data):
    with open(file_name, 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print('file saved')
    
    
def load_pickle(file_name):
    with open(file_name, 'rb') as handle:
        aux = pickle.load(handle)
    print('file loaded')
    return aux
    
    
def extract_terms(doc, doc_id, index, nltk_method_name='simple'):
    if nltk_method_name == 'stemming':
        ps = PorterStemmer()
        nltk_method = ps.stem
    elif nltk_method_name == 'lemmatization':
        lemmatizer = WordNetLemmatizer()
        nltk_method = partial(lemmatizer.lemmatize, pos ="v")
    elif nltk_method_name == 'stop_word_removal':
        nltk_method = lambda word : word if (not word in stopwords.words()) else None
    
    # punctuations="?:!.,;()"
    
    category = doc['category']
    body = doc['body']
    title = doc['title']
    body_words = re.findall(r"[\w']+", body)
    # body_words = nltk.word_tokenize(body)

    for word in body_words:
        # if word not in punctuations:
        if not nltk_method_name is 'simple':
            word = nltk_method(word)
            if word is None:
                continue
        insert_in_index(index, word, doc_id, TermPosition.body, category)
    
    # title_words = nltk.word_tokenize(title)
    title_words = re.findall(r"[\w']+", title)
    for word in title_words:
        # if word not in punctuations:
        if not nltk_method_name is 'simple':
            word = nltk_method(word)
            if word is None:
                continue
        insert_in_index(index, word, doc_id, TermPosition.title, category)
            
def autolabel(rects, ax):
    """
    Attach a text label above each bar displaying its height
    """
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
                '%.4f' % height,
                ha='center', va='bottom')
                
@njit(nb.float32[:,:](nb.float32[:,:], nb.float32[:,:]), fastmath=True)
def calc_cosine_similarities(train_matrix, val_matrix):
    return np.dot(train_matrix, val_matrix)
    
    
    
def calc_euclidean_distance(train_index, test_index, training_data_number, test_data_number, N):
    euclidean_scores = np.zeros((training_data_number, test_data_number))
    for test_term, test_term_data in tqdm(test_index.items(), total=len(test_index)):
        term_in_train = train_index.get(test_term, False)
        if term_in_train:
            df = len(term_in_train.posting_list)
            idf = math.log10(N / df)
            for train_doc_id, train_doc_data in term_in_train.posting_list.items():
                train_tf = train_doc_data.get('body', 0) + 2 * train_doc_data.get('title', 0)
                for test_doc_id, test_doc_data in test_term_data.posting_list.items():
                    test_tf = test_doc_data.get('body', 0) + 2 * test_doc_data.get('title', 0)
                    euclidean_scores[train_doc_id][test_doc_id] += (train_tf * idf - test_tf * idf) ** 2
    return euclidean_scores
    
    
def knn_cosine_similarity(train_matrix, test_matrix):
    normalized_train_matrix = train_matrix / norm(train_matrix, axis=1)[:, None]
    normalized_test_matrix = test_matrix / norm(test_matrix, axis=1)[:, None]
    cosine_similarity = calc_cosine_similarities(normalized_train_matrix, normalized_test_matrix.T)
    cosine_similarity_result_doc_id = cosine_similarity.argsort(axis=0)[-5:][::-1]
    return cosine_similarity_result_doc_id
    
def knn_euclidean_distance(train_index, test_index, training_data_number, test_data_number, N):
    euclidean_distance = calc_euclidean_distance(train_index, test_index, training_data_number, test_data_number, N)
    euclidean_distance_result_doc_id = euclidean_distance.argsort(axis=0)[-5:][::-1]
    return euclidean_distance_result_doc_id    