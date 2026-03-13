LATEXMK = latexmk
TARGET = main

.PHONY: all clean

all: $(TARGET).pdf

$(TARGET).pdf:
	$(LATEXMK) -xelatex $(TARGET)

clean:
	$(LATEXMK) -C