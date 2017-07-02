from __future__ import print_function
from __future__ import division
import math
import numpy as np,csv
import re
import mysql.connector
from nltk import word_tokenize
from nltk.stem.porter import PorterStemmer
import time
# -*- coding: ascii -*-

def file_to_list(doc_path):
	"""Returns '\n' separated lines as a list from given file"""
	with open(doc_path) as f:
		tokens = f.readlines()
		return [w.strip('\n') for w in tokens]


def file_tokenizer(doc_path):
	"""Returns a token list from a .txt file.
	
	Args:
		doc_path: The complete path to the plain text file from which to extract
			the tokens.
	
	Returns:
		A list of stemmed tokens in the order they occur in input file.
		Duplicates are not removed. Hyphens are same as spaces. Tokens without 
		any alphabet in them are omitted.
	"""
	with open(doc_path, 'r') as f:
		raw = f.read()
	stemmer = PorterStemmer()
	tokens = [w.lower() for w in word_tokenize(raw)]
	new_tokens = []
	for item in tokens:
		new_tokens.extend(stemmer.stem(w) for w in re.split('[^a-z0-9]', item))
	
	new_tokens = [w for w in new_tokens if re.search('[a-z]', w)]
	return new_tokens


def raw_token_finder(dir, pre, num_docs, log_path):
	"""Returns list of all tokens and list of lists of tokens in each document.

	Tokenizes all documents with names pre+str(1)+'.txt' to 
		pre+str(num_docs)+'.txt', combines all the tokens and populates the 
		argument tokens and returns the list of lists of tokens of all docs.
	Args:
		dir: The directory in which the documents exist.
		pre: The prefix with which all document names start. All document names
			are of the form pre# where # is the number of the document.
		num_docs: The total number of documents.
		log_path: Path to where tokens must be written
	Returns: Final token list and list of lists of tokens from all documents.
	"""
	list_list = []
	tokens = []
	for i in range(num_docs):
		path = dir + pre + str(i+1) + '.txt'
		doc_tokens = file_tokenizer(path)
		list_list.append(doc_tokens)
		tokens.extend(doc_tokens)
	tokens = np.unique(tokens)

	with open('log_path' + 'tokens.txt', "w") as f:
		for w in tokens:
			f.write('%s\n' % w)

	return tokens, list_list


def stop_word_generator(tokens, list_list, threshold):
	"""Gives a set of stop words from a list of lists of tokenized documents.
	
	Args:
		tokens: A lexicographically sorted list of all tokens
		list_list: A list of lists of tokens from each document.
		threshold: It is a fraction between 0 and 1. Words that appear in 
			atleast this fraction of documents are considered as stop words.
	Returns:
		A set of stopwords to be removed from given list of lists.
	"""
	stop_words = []
	num_docs = len(list_list)
	threshold *= num_docs
	set_list = [set(s) for s in list_list]
	for w in tokens:
		count = 0
		for s in set_list:
			if (w in s):
				count += 1
		if (count > threshold):
			stop_words.append(w)
	return stop_words


def source_stop_words(path):
	"""Returns set of words from file at input path

	Args:
		path: Path of the stopwords file. The file must contain all stopwords
		separated by newline characters.
	"""
	with open(path) as f:
		raw = f.readlines()
		return set(a.strip('\n') for a in raw)


def remove_stop_words(tokens, list_list, stop_words):
	"""Removes any stop words from tokens & list_list & returns them

	Args:
		tokens: List of stemmed tokens without stop words.
		list_list: List of lists of tokens from all documents.
		stop_words: List of all stopwords.
	"""
	tokens = [w for w in tokens if w not in stop_words]
	for l in list_list:
		l = [w for w in l if w not in stop_words]
	return tokens,list_list


def matrix_creator(tokens, list_list, config, table_name):
	"""Creates a frequency matrix in MySQL & fills it.

	Args:
		tokens: List of stemmed tokens without stop words.
		list_list: List of lists of tokens from all documents.
		config: Dictionary json used to connect to MySQL database.
		table_name: Table name that needs to be created.
	Returns:
		Nothing
	"""
	dbConnector = mysql.connector.connect(**config)
	c = dbConnector.cursor()

	query = "CREATE TABLE " + table_name + " ( `tokens` varchar(24) NOT NULL, PRIMARY KEY (tokens))"
	c.execute(query)

	for w in tokens:
		query = "INSERT INTO " + table_name + " VALUES(%s)"
		c.execute(query, (str(w),))
	
	print("    MySQL: Tokens Inserted")

	num_docs = len(list_list)
	for i in range(num_docs):
		column_name = "docs" + str(i+1)
		query = "ALTER TABLE matrix ADD COLUMN %s INT NOT NULL DEFAULT '0'" % (column_name)
		c.execute(query)
		for w in list_list[i]:
			query = "UPDATE matrix SET " + column_name + " = " + column_name + " + 1 where tokens = %s"
			c.execute(query, (str(w),))
		print("    MySQL: Document " + str(i+1) + " inserted")

	dbConnector.commit()


def df_idf_postings_creator(tokens, num_docs, config, table_name):
	"""Adds df, idf & postings columns to matrix table in MySQL DB

	Args:
		tokens: List of stemmed tokens without stop words.
		num_docs: Total number of documents.
		config: Dictionary json used to connect to MySQL database.
		table_name: Table name in which df, idf & postings need to be inserted.
	"""
	dbConnector = mysql.connector.connect(**config)
	c = dbConnector.cursor()
	no_handouts = num_docs

	query = "ALTER TABLE  " + table_name + " ADD COLUMN docfreq INT NOT NULL DEFAULT '-1'"
	c.execute(query)

	query = "ALTER TABLE  " + table_name + " ADD COLUMN invdocfreq FLOAT NOT NULL DEFAULT '-1'"
	c.execute(query)

	query = "ALTER TABLE  " + table_name + " ADD COLUMN postings VARCHAR(%s) NOT NULL DEFAULT ','"
	c.execute( query, ((5 * no_handouts + 2), ))

	
	for w in tokens:
		time_begin = time.time()
		postings = []
		doc_freq = 0
		inv_doc_freq = 0
		
		query = "SELECT * FROM " + table_name + " WHERE tokens = %s"
		c.execute(query, (str(w), ))
		rows = c.fetchall()

		for i in range(1, num_docs + 1):
			if (rows[0][i] > 0):
				doc_freq += 1
				postings.append(i)

		postings = np.unique(postings)
		
		postings = ",".join(str(i)  for i in postings)

		if (doc_freq != 0):
			inv_doc_freq = 1 + math.log10(num_docs / float(doc_freq))
		else:
			inv_doc_freq = 0

		query = "UPDATE " + table_name + " set docfreq = %s, invdocfreq = %s, postings = %s where tokens = %s"
		c.execute(query, (doc_freq, inv_doc_freq, postings, str(w)))

		
	
	dbConnector.commit()


def vector_creator(tokens, num_docs, config, table_name_1, table_name_2):
	"""Creates the document vectors (according to vector space model) table.

	Args:
		tokens: List of stemmed tokens without stop words.
		num_docs: Total number of documents.
		config: Dictionary json used to connect to MySQL database.
		table_name_1: Table from which tf and idf values are to be obtained.
		table_name_2: Table name that needs to be created.
	"""
	dbConnector = mysql.connector.connect(**config)
	c = dbConnector.cursor()

	query = "CREATE TABLE " + table_name_2 + " ( `tokens` varchar(24) NOT NULL, PRIMARY KEY (tokens))"
	c.execute(query)

	for w in tokens:
		query = "INSERT INTO " + table_name_2 + " VALUES(%s)"
		c.execute(query, (str(w), ))

	for i in range(num_docs):
		time_begin = time.time()
		column_name = 'doc' + str(i+1)
		
		query = "ALTER TABLE  " + table_name_2 + " ADD COLUMN %s FLOAT NOT NULL DEFAULT '-1'" % (column_name)
		c.execute(query)

		for w in tokens:
			query = "select `invdocfreq` from " + table_name_1 + " where `tokens` = %s"
			c.execute(query, (str(w), ))
			rows = c.fetchall()
			idf = rows[0][0]

			query = "select docs" + str(i + 1) + " from " + table_name_1 + " where `tokens` = %s"
			c.execute(query, (str(w), ))
			rows = c.fetchall()
			tf = rows[0][0]
			
			if (tf == 0):
				tfidf = 0
			else:
				tfidf = idf * (1 + math.log10(tf))

			query = "update " + table_name_2 + " set " + column_name + " = %s where `tokens` = %s"
			c.execute(query, (tfidf, str(w)))

		time_end = time.time()
		print("Doc" + str(i+1) + " Vector created in " + str(time_end - time_begin))
	dbConnector.commit()


def docnames(csv_path, config, CMS_course_URL, table_name):
	"""Creates the table that stores course information

	Args:
		csv_path: Path of the .csv file containing metadata of the documents
		config: Dictionary json used to connect to MySQL database.
		CMS_course_URL: URL of the generic CMS course view page
		table_name: Name of the table that needs to be created.
	"""

	dbConnector = mysql.connector.connect(**config)		
	c = dbConnector.cursor()

	# SQL query to create table is generated.
	query = "CREATE TABLE " + table_name + " ("
	query += "docno varchar(6) NOT NULL , "
	query += "courseid varchar(24) NOT NULL, "
	query += "coursename varchar(54) NOT NULL, "
	query += "urlid smallint NOT NULL default 1)"
	c.execute(query)

	# .csv file is read.
	with open(csv_path, 'rb') as f:
		reader = csv.reader(f)
		csv_list = list(reader)

	for w in csv_list:
		query = "INSERT INTO " + table_name + " VALUES(%s, %s, %s, %s)"
		w[0] = 'doc' + w[0]
		w[3] = int(w[3].split(CMS_course_URL + '?id=')[1])
		c.execute(query, tuple(w))
	dbConnector.commit()


def query_tokenizer(query_string, stemmer):
	"""Tokenizes given string and returns the list of tokens.
	
	Splits by spaces and '-' character and then stems using a given stemmer.
	Args:
		query_string: The query string to be tokenized
		stemmer: The stemmer to stem with. It must have a .stem method that
		takes a string and stems it.
	Returns: A list of obtained query tokens
	"""
	tokens = re.split('([f-h][0-9]{3})', query_string)
	tokens.extend([stemmer.stem(w).lower() for w in re.split('[\W]', query_string) ])
	return tokens


def postings_query_maker(table_name, query_tokens, query_length):
	"""Makes the postings retrieving query

	Assumes that the postings are stored in a MySQL database in the column
		named 'postings'
	Args:
		table_name: The table name inside which the postings reside
		query_tokens: The token list of the query
		query_length: Length of the list query_tokens
	Returns:
		query: The MySQL query string to execute to get postings
		t: The arguments tuple in the query
	"""
	t = ()
	query = "SELECT postings from matrix where tokens in ( %s"

	for i in range(0,query_length - 1):
		t += ((query_tokens[i], ))
		query += ", %s"

	t += ((query_tokens[query_length - 1], ))
	query += " )"
	return query, t


def relevance_query_maker(table_name, doc_name, query_tokens, query_length):
	"""Makes the MySQL query that retrieves the relevance of doc_name

	Args:
		table_name: The table name inside which the tf-idf values reside.
		doc_name: The column name for which relevance is desired.
		query_tokens: List of tokens in the query
		query_length: Length of the list query_tokens
	Returns:
		query: MySQL query that retrieves document relevance from database.
		t: The arguments tuple in the query
	"""
	t = ()
	query = "SELECT sum(" + doc_name + ") FROM " + table_name + " WHERE tokens in (%s"

	for i in range(0,query_length - 1):
		t += ((query_tokens[i], ))
		query += ", %s"

	t += ((query_tokens[query_length - 1], ))
	query += " )"
	return query, t