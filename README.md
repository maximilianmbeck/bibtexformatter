BibTeX Formatter
=================

A small utility script that cleans and normalizes BibTeX entries for consistent formatting. It takes a source .bib file and writes a cleaned output .bib file.

Quick usage
-----------

Run the formatter by providing the input and output paths:

python ./bibtexformatter/clean_bib.py ./bibs_source/references_phd_thesis.bib ./references.bib

python ./bibtexformatter/clean_bib.py ./bibs_source/references_phd_thesis.bib ./references.bib --remove-note --remove-note-ignore "Version" --remove-month --remove-number-doi-issn --remove-pages --remove-integer-volume

python ./bibtexformatter/clean_bib.py ./bibs_source/mlstm_scaling.bib ./mlstm_scaling_clean.bib --remove-note --remove-note-ignore "Version" --remove-month --remove-number-doi-issn --remove-pages --remove-integer-volume

Repository layout
-----------------

- bibtexformatter/clean_bib.py: formatting script
- bibs_source/: source .bib files
- references.bib: example formatted output
