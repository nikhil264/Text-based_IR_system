import time
from newQueryAuxiliary import raw_token_finder
from newQueryAuxiliary import stop_word_generator
from newQueryAuxiliary import remove_stop_words
from newQueryAuxiliary import matrix_creator
from newQueryAuxiliary import source_stop_words
from newQueryAuxiliary import vector_creator
from newQueryAuxiliary import df_idf_postings_creator
from newQueryAuxiliary import file_to_list
from newQueryAuxiliary import docnames
import numpy as np



#########Below this line are parameters for backend creation

# Config file used to connect to the MySQL database
config = {
	'user': 'root',
	'password': 'yourmom',
	'host': '127.0.0.1',
	'database': 'infer',
	'raise_on_warnings': True,
	'use_pure': False,
}

table_name_1 = "matrix"
table_name_2 = "docvectors"
table_name_3 = "docnames"


CMS_course_URL = "http://cms.bits-hyderabad.ac.in/moodle/course/view.php"

# The directory in which the corpus files are stored in .txt format
doc_directory = "./handoutstxt/"

# File containing metadata of each logical document
csv_file = "./Courses.csv"

# Path of the stopwords file
stop_words_path = "./stopwords.txt"

# Names of the documents in the corpus at above location must be
# in the form [doc_prefix+str(doc_number) for doc_number in range(1, no_of_docs+1)]
doc_prefix = "docs"

# Self-Explanatory
no_of_docs = 183

#########Above this line are parameters for backend creation



time_00 = time.time()

tokens, list_list = raw_token_finder(doc_directory, doc_prefix, no_of_docs, doc_directory)

time_01 = time.time()
print(str(len(tokens)) + " tokens found in " + str(time_01-time_00))

stop_words = source_stop_words(stop_words_path)

tokens, list_list = remove_stop_words(tokens, list_list, stop_words)

time_02 = time.time()
print("Stop Words removed in " + str(time_02-time_01))

matrix_creator(tokens, list_list, config, table_name_1)

time_04 = time.time()
print("Frequency matrix created in " + str(time_04 - time_02))

df_idf_postings_creator(tokens, no_of_docs, config, table_name_1)

time_05 = time.time()
print("df, idf and postings created in " + str(time_05 - time_04))

vector_creator(tokens, no_of_docs, config, table_name_1, table_name_2)

time_06 = time.time()
print("Doc Vectors created in " + str(time_06 - time_05))

docnames(csv_file, config, CMS_course_URL, table_name_3)
time_07 = time.time()
print(".csv file uploaded to the database in" + str(time_07 - time_06))

time_final = time.time()
print("\nTotal indexing time: " + str(time_final - time_00))
print("\n")