PDFS = exercise-list.pdf exercises.pdf

all: $(PDFS)

%.pdf: %.tex
	pdflatex -interaction=nonstopmode -halt-on-error $<
	pdflatex -interaction=nonstopmode -halt-on-error $<

check:
	./ecps/run-all.sh

clean:
	rm -f *.aux *.log *.out

.PHONY: all check clean
