import os
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np
import re
import pickle

class VectorLexicon:
    def __init__(self, filepath=None):
        # Initialize a dictionary to simulate VectorDB and vectorizer
        self.db = {}
        self.alias_terms = {}
        self.filepath = filepath
        if self.filepath != None:
            self.load(filepath)


    def add_term(self, term, definition, references=None):
        if term not in self.db:
            self.db[term] = {'definitions': [], 'references': []}
        self.db[term]['definitions'].append(definition)
        if references:
            self.db[term]['references'].extend(references)


    def add_alias(self, alias, term):
        """ Adds an alias that refers to another term. """
        if alias not in self.alias_terms:
            self.alias_terms[alias] = []
        self.alias_terms[alias].append(term)        
   

    def find_relevant_terms(self, prompt):
        # Initialize the output dictionary.
        output = {}

        # Compile a regular expression pattern to match whole words, taking into account multi-word terms.
        pattern = r'\b(?:' + '|'.join(re.escape(term) for term in self.db) + r')\b'
        matches = re.findall(pattern, prompt)

        # Handle matches of full terms.
        for match in matches:
            if match in self.db:
                output[match] = [{'term': match, 'meaning': meaning} for meaning in self.db[match]['definitions']]
                # Include references as separate keys.
                for ref in self.db[match].get('references', []):
                    if ref in self.db:
                        output[ref] = [{'term': ref, 'meaning': ref_meaning} for ref_meaning in self.db[ref]['definitions']]

        # Handle aliases separately.
        for alias, terms in self.alias_terms.items():
            # Check if the alias is present as a whole word in the prompt.
            if re.search(r'\b' + re.escape(alias) + r'\b', prompt):
                output[alias] = []
                for term in terms:
                    output[alias].extend([{'term': term, 'meaning': meaning} for meaning in self.db[term]['definitions']])

        return output


    def request_disambiguate_term(self, term, potential_meanings):
        print("Disambiguation: When you say '%s', which are you referring to?" % term)
        while True:
            for i in range(0,len(potential_meanings)):
                definition = potential_meanings[i]['meaning']
                core_term = potential_meanings[i]['term']

                if core_term != term:
                    print(f"{i+1}. {term}: {core_term} - {definition}")
                else:
                    print(f"{i+1}. {term} - {definition}")
            try:
                selection = int(input("> "))
                if selection > len(potential_meanings):
                    print("Invalid Selection - Try Again")
                    continue
                return potential_meanings[selection - 1]
            except:
                print("Invalid Selction - Try Again")

    
    def enrich_prompt(self, prompt, user_clarification=False):
        relevant_terms = self.find_relevant_terms(prompt)
        terms_to_add = []
        for term in relevant_terms.keys():  
            if len(relevant_terms[term]) == 1:
                terms_to_add.append({'term':term,'name':relevant_terms[term][0]['term'],'meaning':relevant_terms[term][0]['meaning']})
            else:
                # If User clarification, we'll clear these up.
                if user_clarification:
                    selected_term = self.request_disambiguate_term(term,relevant_terms[term])
                    terms_to_add.append({'term':term,'name':selected_term['term'],'meaning':selected_term['meaning']})      
                # Otherwise, we'll put them all up and let the llm decide.
                else:
                    for current_match in relevant_terms[term]:
                        terms_to_add.append({'term':term,'name':current_match['term'],'meaning':current_match['meaning']})

        # Now, update our prompt
        enriched_prompt = prompt
        for entry in terms_to_add:
            if entry['term'] != entry['name']:
                enriched_prompt += f" [{entry['term']}: {entry['name']} - {entry['meaning']}]"
            else:
                enriched_prompt += f" [{entry['term']}: {entry['meaning']}]"                  
        return enriched_prompt    

    def save(self, filepath):
        """ Saves the current state of the lexicon and vectorizer to a file. """
        with open(filepath, 'wb') as file:
            pickle.dump((self.db, self.vectorizer, self.index, self.alias_terms, self.terms_index), file)

    def load(self, filepath):
        """ Loads the lexicon and vectorizer state from a file. """
        if not os.path.exists(filepath):
            return False        
        with open(filepath, 'rb') as file:
            self.db, self.vectorizer, self.index, self.alias_terms, self.terms_index = pickle.load(file)    

def new_test():
    pass
if __name__ == "__main__":
    new_test()