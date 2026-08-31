PDF = exercise-list.pdf

all: $(PDF)

$(PDF): exercise-list.tex
	pdflatex -interaction=nonstopmode -halt-on-error $<
	pdflatex -interaction=nonstopmode -halt-on-error $<

clean:
	rm -f exercise-list.aux exercise-list.log exercise-list.out

.PHONY: all clean
