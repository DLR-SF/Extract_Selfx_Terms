'''
Simple tool to extract terms from
PDF files and count & collect their 
references

Author: Inga Miadowicz
License: GNU General Public License v3.0
Version: 1.0
'''


import PyPDF2
import re
import os
import pandas as pd
import logging
import configparser


class Main():

    def __init__(self):
        # init logging
        self.initialize_logging()

        # init configuration
        self.initialize_config()

        # -> internal counters & list
        self.list_of_files = []
        self.list_of_selfx = []
        self.list_of_counters_uses_in_paper = []
        self.counter_all_selfx = 0
        self.counter_all_selfx_without_duplicates = 0
        self.counter_root_lvls = 0
        self.counter_files = 0
        self.list_paper_with_matches = []
        self.list_paper_with_matches_selfx = []
        self.list_paper_with_matches_count_selfx = []
        self.list_raw_selfx = []
        self.list_raw_selfx_len = []

    '''
    Initialize configuration and provide it
    as class variable as a dictionary
    '''
    def initialize_config(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")

    '''
    Parse list from configuration into dictionary
    Clean content:
    - all to lowercase
    - remove spaces
    - remove newlines
    - break list by ','
    '''
    def parse_list_from_config(self, section, property_name):
        return ''.join(self.config[section][property_name].lower().
                       replace(' ', '').splitlines()).split(",")

    '''
    check if common word exists with another ending using regex
    from configuration. If yes unify it by given word form from
    configuration.
    '''
    def unify_word(self, cleaned_match):
        # parse regex and replacement terms from configuration as list without space or \n
        unify_words_regex = self.parse_list_from_config("parse", "unify_words_regex")
        unify_words_replacement = self.parse_list_from_config("parse", "unify_words_replacement")

        # unify terms using regex
        regex_counter = 0
        for regex in unify_words_regex:
            regex_counter = regex_counter + 1
            # search for regex in self-x term
            if re.search(regex, cleaned_match):
                # replace with common word if similar
                # index of unified word = regex_counter - 1
                cleaned_match = unify_words_replacement[(regex_counter - 1)]

        return cleaned_match

    '''
    initialize logging class
    '''
    def initialize_logging(self):
        # filehandler
        logger = logging.getLogger('Beispiel_Log')
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('selfx.log', 'w', 'utf-8')
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # logging to console
        logging.basicConfig(
                level="DEBUG",
                format="%(asctime)s - %(name)s - [ %(message)s ]",
                datefmt='%d-%b-%y %H:%M:%S',
                force=True,
                handlers=[
                    logging.FileHandler('selfx.log', 'w', 'utf-8'),
                    logging.StreamHandler()
                ]
        )

    '''
    append or create self-x string
    '''
    def set_string_selfx_matches(self, string_selfx_matches, unified_match):
        # first term has no comma
        if len(string_selfx_matches) == 0:
            string_selfx_matches = unified_match
        # other terms can be appended comma
        else:
            if unified_match not in string_selfx_matches:
                string_selfx_matches += ", " + unified_match

        return string_selfx_matches

    '''
    Check if term has a forbidden ending
    '''
    def check_special_ending(self, match):
        excluded_endings = self.parse_list_from_config("parse", "excluded_endings")
        for substr in excluded_endings:
            if match.endswith(substr):
                return False

        return True

    '''
    Check if term not included in ingore words, 
    has special ending or is too long
    '''
    def check_exclusion_criteria(self, cleaned_match): 
        ending_allowed = self.check_special_ending(cleaned_match)
        length_allowed = len(cleaned_match) <= int(self.config["parse"]["max_length_term"])
        if ending_allowed and length_allowed:
            excluded_selfx = self.parse_list_from_config("parse", "excluded_selfx")
            if cleaned_match not in excluded_selfx:
                return True

        return False

    '''
    Handle processing of already existing self-x term
    - increase counter for term
    - add as a new paper as it doesn't exist
    '''
    def handle_already_existing_term(self, unified_match, file):
        # get index of word and check corresponding paper
        index = self.list_of_selfx.index(unified_match)
        papers = self.list_of_files[index]
        paper_list = papers.split(", ")

        # if paper does not exists add paper to files and increase counter
        if file not in paper_list:
            self.list_of_files[index] = papers + ", " + file
            new_file_count = self.list_of_counters_uses_in_paper[index] + 1
            self.list_of_counters_uses_in_paper[index] = new_file_count

        return unified_match

    '''
    Handle processing of new self-x term
    - add to list of papers and files
    - increase counter
    '''
    def handle_new_word_and_paper(self, unified_match, file):
        logging.info("-> " + unified_match)
        self.list_of_files.append(file)
        self.list_of_selfx.append(unified_match)
        self.list_of_counters_uses_in_paper.append(1)
        self.counter_all_selfx_without_duplicates = self.counter_all_selfx_without_duplicates + 1

    '''
    handle a file
    - extract self-x term from pds    
    '''
    def extract_term_from_pdf(self, root, file):
        # variable for all matches per author
        string_selfx_matches = ""

        # read paper and parse page by page
        filepath = os.path.join(root, file)
        reader = PyPDF2.PdfReader(filepath)
        for page in reader.pages:
            # extract text from page
            text = page.extract_text() 

            # search self-x in page via regex
            # -> Upper / Lowercase will be ignored
            # -> self-term can have spaces between "-" because of pdf-parsing
            # -> a self-term could be broken into two line using "-\n"
            search_term = r'(self {0,1}\- {0,1}[A-Za-z]+|self {0,1}\- {0,1}\n {0,1}[A-Za-z]+)'
            matches_search = re.findall(search_term, text, re.IGNORECASE)

            # handle each match 
            for match in matches_search:
                # clean match (transform to lowercase and remove \n and space)
                cleaned_match = ''.join(match.lower().replace(" ", "").splitlines())

                # apply exclusion criteria
                if self.check_exclusion_criteria(cleaned_match):

                    # save raw result
                    self.list_raw_selfx.append(cleaned_match)
                    self.list_raw_selfx_len.append(len(cleaned_match))
                    self.counter_all_selfx = self.counter_all_selfx + 1

                    # first check if common word exists in similar form and unify
                    unified_match = self.unify_word(cleaned_match)

                    # save paper with matches for reference if author is not already in list
                    if matches_search and file not in self.list_paper_with_matches:
                        self.list_paper_with_matches.append(file)

                    # handle new and existing terms in lists
                    if unified_match in self.list_of_selfx:
                        unified_match = self.handle_already_existing_term(unified_match, file)
                    else:
                        self.handle_new_word_and_paper(unified_match, file)

                    # add to selfx string
                    string_selfx_matches = self.set_string_selfx_matches(string_selfx_matches, unified_match)

        # parsed all pages of paper -> add string to list of matches for author
        if string_selfx_matches != "":
            # count number of (distinct) self-x per author
            list_selfx_paper = string_selfx_matches.split(", ")
            self.list_paper_with_matches_count_selfx.append(len(list_selfx_paper))

            # add to list
            self.list_paper_with_matches_selfx.append(string_selfx_matches)

    '''
    print statistics after termination
    '''
    def print_statistics(self):
        logging.info("")
        logging.info("Searched in {} files.".format(self.counter_files))
        logging.info("Found:")
        logging.info("- {} all self-x matches (without excluded or too long words)".format(self.counter_all_selfx))
        logging.info("- {} self-x matches unified and without duplicates".format(
            self.counter_all_selfx_without_duplicates))
        logging.info("- {} papers had matches".format(len(self.list_paper_with_matches)))

    '''
    write results to output files
    - selfx to excel sheet
    - papers with matches to txt file
    '''
    def export_results(self):
        # write selected selfx to excel
        rootdir = self.config["outputfiles"]["rootdir_output"]
        self.df.reset_index(inplace=True, drop=True) 
        self.df.to_excel(os.path.join(rootdir, self.config["outputfiles"]["output_selfx"]),
                         sheet_name='selfx_prettified', index=True)

        # write papers and selfx-namings to excel
        self.df_selfx.to_excel(os.path.join(rootdir, self.config["outputfiles"]["output_paper"]),
                               sheet_name='selfx_prettified', index=True)

        # write raw self-x matches to excel
        self.df.reset_index(inplace=True, drop=True) 
        self.df_raw.to_excel(os.path.join(rootdir, self.config["outputfiles"]["output_raw"]),
                             sheet_name='selfx_raw', index=True)

    '''
    delete old excel files for a fresh start
    '''
    def remove_old_files(self):
        if os.path.isfile(self.config["outputfiles"]["output_selfx"]):
            os.remove(self.config["outputfiles"]["output_selfx"])
        if os.path.isfile(self.config["outputfiles"]["output_paper"]):
            os.remove(self.config["outputfiles"]["output_paper"])

    '''
    Save results from lists as dataframes and name columns
    '''
    def save_results_as_df(self):
        # save selfx data as df 
        self.df = pd.DataFrame({'selfx': self.list_of_selfx, 'file_counts': self.list_of_counters_uses_in_paper,
                                'file': self.list_of_files})
        self.df.file_counts = self.df.file_counts.astype(int)

        # save papers and selfx as df 
        self.df_selfx = pd.DataFrame({'papers': self.list_paper_with_matches, 
                                      'selfx_count': self.list_paper_with_matches_count_selfx,
                                      'matches': self.list_paper_with_matches_selfx})

        # save raw results as df
        self.df_raw = pd.DataFrame({'selfx': self.list_raw_selfx, 'length': self.list_raw_selfx_len})

    '''
    Main execution login
    '''
    def main(self):

        # 1) start script
        logging.info("--- START ---")
        logging.info("")
        logging.info("1) Initialized script and start to process file location {}".format(
            self.config["inputfiles"]["rootdir_papers"]))
        logging.info("")

        # 2) clean output file if exists
        logging.info("2) Remove old output files with same name if they exist")
        self.remove_old_files()

        # 3) recusively iterate through files, parse pdfs and extract self-x-capabilities
        logging.info("")
        logging.info("3) Recursively process files {}".format(self.config["inputfiles"]["rootdir_papers"]))
        for root, subdirs, files in os.walk(self.config["inputfiles"]["rootdir_papers"]):

            # Only iterate relevant folders (-> relevant_folders)
            current_folder = os.path.basename(os.path.normpath(root))
            relevant_folders = self.config["inputfiles"]["relevant_folders"].split(", ")
            if current_folder in relevant_folders:

                # print folder level
                self.counter_root_lvls = self.counter_root_lvls + 1
                logging.info("")
                logging.info("--")
                logging.info('Parsing folder level {}: {}'.format(self.counter_root_lvls, root))
                logging.info("--")
                logging.info("")

                # process files in folder level
                for file in files:
                    self.counter_files = self.counter_files + 1
                    logging.info("")
                    logging.info('{}. file: {}'.format(self.counter_files, file))

                    # extract text from pdf
                    self.extract_term_from_pdf(root, file)

        # save selfx data as df
        self.save_results_as_df()

        # 4) Check minimal number of references
        logging.info("4) Check minimal number of references")
        self.df = self.df[self.df.file_counts >= int(self.config["parse"]["nr_references"])]
        self.df.sort_values('file_counts')

        # export results
        self.export_results()

        # statistics
        self.print_statistics()

        logging.info("--- Done ---")


if __name__ == '__main__':
    main = Main()
    main.main()