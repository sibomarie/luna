MANPAGESPATH="/usr/share/man"
RSTFILES=$(shell find . -name '*.rst') 
all:
	set -e; \
	for RSTFILE in ${RSTFILES} ; do \
		RSTFILE=$${RSTFILE#*./}; \
		MANNAMESECT=$${RSTFILE%.*}; \
		MANNAME=$${MANNAMESECT%.*}; \
		MANSECT=$${MANNAMESECT#*.}; \
		MANFILEGZIP="$${MANNAMESECT}.gz"; \
		rst2man $${RSTFILE} | gzip > $${MANFILEGZIP}; \
	done
install:
	set -e; \
	for RSTFILE in ${RSTFILES} ; do \
		RSTFILE=$${RSTFILE#*./}; \
		MANNAMESECT=$${RSTFILE%.*}; \
		MANNAME=$${MANNAMESECT%.*}; \
		MANSECT=$${MANNAMESECT#*.}; \
		MANFILEGZIP="$${MANNAMESECT}.gz"; \
		install -m 0644 $${MANFILEGZIP} ${MANPAGESPATH}/man$${MANSECT}/$${MANFILEGZIP}; \
	done
clean:
	rm -rf ./*.gz
