# The per-object compile step of the opt-in build (`make OBJ=1`; test batch 3, A1). Run by the main Makefile's ROM recipe as
#   $(MAKE) -f tools/dev/objs.mk -j$(OBJJOBS) OBJD=<dir> FLAGS='<lcc flags>' SRCS='<every C file, in the one-shot lcc order>' [LCC=lcc ...]
# Each C file is compiled to its own object <OBJD>/<name>.o with `lcc -c` (the same sdcc command the one-shot lcc call runs for it) and a
# header dependency file <name>.d (sdcc's -MMD), so a header edit recompiles only the objects that include it. This file knows nothing of the
# generators (they ran before, in the main Makefile), so `make -B` cannot make it re-run them in parallel. OBJD belongs to one build
# (one ROM variant in one BUILD directory): no object is ever shared between builds. The link order is NOT decided here: the main
# Makefile links the objects in the order of its own fixed list (SRC, then GEN), never in the order the jobs finish.

LCC ?= lcc
HUGE_INC ?= third_party/hugedriver/include
BUILD ?= build
NAMES := $(foreach s,$(SRCS),$(basename $(notdir $(s))))
OBJS  := $(addprefix $(OBJD)/,$(addsuffix .o,$(NAMES)))

.PHONY: all
all: $(OBJS)

# $(call one,<source>): the rule for one object. The flags stamp (written by the main Makefile only when the flags change) is a prerequisite,
# so a changed flag recompiles everything. The compiler's output goes to <name>.log (shown only when the compile fails); lcc's scratch
# files (.asm .lst .sym .adb) are removed, as the one-shot call removes them.
define one
$(OBJD)/$(basename $(notdir $(1))).o: $(1) $(STAMP)
	@echo "  CC $(1)"
	@$(LCC) $(FLAGS) -I$(BUILD) -Isrc -I$(HUGE_INC) -Wf-MMD -c -o $$@ $(1) > $(OBJD)/$(basename $(notdir $(1))).log 2>&1; rc=$$$$?; \
	  rm -f $(OBJD)/$(basename $(notdir $(1))).asm $(OBJD)/$(basename $(notdir $(1))).lst $(OBJD)/$(basename $(notdir $(1))).sym $(OBJD)/$(basename $(notdir $(1))).adb; \
	  test $$$$rc -eq 0 || { cat $(OBJD)/$(basename $(notdir $(1))).log; rm -f $$@; false; }
endef
$(foreach s,$(SRCS),$(eval $(call one,$(s))))

# a header that was deleted or renamed after a .d file named it must not stop the build: an empty rule "makes" it, and the object is recompiled
%.h: ;
-include $(OBJS:.o=.d)
