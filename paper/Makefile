LATEXMK = latexmk
TARGET = main
SOURCES = $(TARGET).tex bibliography.bib preamble.tex $(wildcard sections/*.tex)

.PHONY: all clean

all: $(TARGET).pdf

$(TARGET).pdf: $(SOURCES)
	$(LATEXMK) $(TARGET)

clean:
	$(LATEXMK) -C