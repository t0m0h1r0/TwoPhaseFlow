LATEXMK = LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 latexmk
TARGET = main
SOURCES = $(TARGET).tex bibliography.bib preamble.tex $(wildcard sections/*.tex)

.PHONY: all clean

all: $(TARGET).pdf

$(TARGET).pdf: $(SOURCES)
	$(LATEXMK) $(TARGET)

clean:
	$(LATEXMK) -C
