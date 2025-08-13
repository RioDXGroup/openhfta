# Directories
SRC_DIR       := src
TEST_DIR      := test
OBJDIR_NATIVE := build/native
OBJDIR_WIN    := build/win

# Sources
SRC_FILES := $(wildcard $(SRC_DIR)/*.f90)

# Host platform
UNAME_S := $(shell uname -s 2>/dev/null || echo unknown)

# Compilers
FC_NATIVE ?= gfortran
CC_WIN    ?= i686-w64-mingw32-gcc
FC_WIN    ?= i686-w64-mingw32-gfortran

# C compilation flags
CSTD   ?= -std=c11
CFLAGS ?= -Og -g -Wall -Wextra -Wno-unused-parameter

# Fortran flags (identical between native and cross; see PORTING_NOTES.md)
FFLAGS_COMMON ?= -O0 -g -mfpmath=387 -fexcess-precision=fast -ffast-math -fno-associative-math -fno-reciprocal-math -fcheck=all -ffree-line-length-none
FFLAGS_NATIVE := $(FFLAGS_COMMON) -fPIC
FFLAGS_WIN    := $(FFLAGS_COMMON)

# Linking
LDLIBS_WIN ?= -lkernel32

ifeq ($(OS),Windows_NT)
NATIVE_LIB     := OpenYTWCore.dll
NATIVE_LDFLAGS := -shared
else ifeq ($(UNAME_S),Darwin)
NATIVE_LIB     := libOpenYTWCore.dylib
NATIVE_LDFLAGS := -dynamiclib
else
NATIVE_LIB     := libopenytwcore.so
NATIVE_LDFLAGS := -shared
endif

# Wine (only for 'make test')
WINEPATH  ?= /usr/i686-w64-mingw32/bin
WINEDEBUG ?= -all
RUN_ARGS  ?=

# Installation directories
PREFIX    ?= /usr/local
BINDIR    ?= $(PREFIX)/bin
LIBDIR    ?= $(PREFIX)/lib
DOCDIR    ?= $(PREFIX)/share/doc/hfta
DESTDIR   ?=

# Objects
OBJ_NATIVE := $(patsubst $(SRC_DIR)/%.f90,$(OBJDIR_NATIVE)/%.o,$(SRC_FILES))
OBJ_WIN    := $(patsubst $(SRC_DIR)/%.f90,$(OBJDIR_WIN)/%.o,$(SRC_FILES))

# Default target: native shared library build
all: $(NATIVE_LIB)

# Directory rules
$(OBJDIR_NATIVE) $(OBJDIR_WIN):
	mkdir -p $@

# Compile objects (native)
$(OBJDIR_NATIVE)/%.o: $(SRC_DIR)/%.f90 | $(OBJDIR_NATIVE)
	$(FC_NATIVE) $(FFLAGS_NATIVE) -c -o $@ $<

# Compile objects (Windows cross)
$(OBJDIR_WIN)/%.o: $(SRC_DIR)/%.f90 | $(OBJDIR_WIN)
	$(FC_WIN) $(FFLAGS_WIN) -c -o $@ $<

# Native shared library for real use on the host platform.
$(NATIVE_LIB): $(OBJ_NATIVE)
	$(FC_NATIVE) $(NATIVE_LDFLAGS) -o $@ $(OBJ_NATIVE)

# Windows DLL for testing (output in test/)
# Requires: test/OpenYTWCore.def (export file) and cross objects
$(TEST_DIR)/OpenYTWCore.dll: $(OBJ_WIN) $(TEST_DIR)/OpenYTWCore.def
	$(FC_WIN) $(FFLAGS_WIN) -shared -o $@ $(OBJ_WIN) \
	  -Wl,$(TEST_DIR)/OpenYTWCore.def -Wl,--out-implib,$(TEST_DIR)/libOpenYTWCore.a \
	  -static-libgfortran -static-libgcc

# C test harness (output in test/)
$(TEST_DIR)/test_ytw_harness.exe: $(TEST_DIR)/test_ytw_harness.c $(TEST_DIR)/ytw_addrs.h
	$(CC_WIN) $(CSTD) $(CFLAGS) \
	  -o $@ $(TEST_DIR)/test_ytw_harness.c $(LDLIBS_WIN)

# Core test target: run the differential harness when legacy DLLs are available.
test-core:
	@if [ ! -f "$(TEST_DIR)/YTWCore.dll" ] || [ ! -f "$(TEST_DIR)/DFORRT.DLL" ]; then \
	  echo "Skipping differential tests: missing legacy DLL dependencies."; \
	  echo "Place YTWCore.dll and DFORRT.DLL in test/ to enable them."; \
	else \
	  $(MAKE) test-core-differential; \
	fi

test-core-differential: $(TEST_DIR)/OpenYTWCore.dll $(TEST_DIR)/test_ytw_harness.exe
	cd $(TEST_DIR) && WINEPATH=$(WINEPATH) WINEDEBUG=$(WINEDEBUG) wine ./test_ytw_harness.exe $(RUN_ARGS)

# Test target: run both core tests and Python unit tests
test: test-core
	@echo "Running Python unit tests..."
	python3 -m unittest test_hfta -v

# Cleanup
clean:
	rm -rf $(OBJDIR_NATIVE) $(OBJDIR_WIN) $(NATIVE_LIB) \
	  $(TEST_DIR)/OpenYTWCore.dll $(TEST_DIR)/libOpenYTWCore.a $(TEST_DIR)/test_ytw_harness.exe

# Install target
install: $(NATIVE_LIB)
	@echo "Installing OpenHFTA to $(DESTDIR)$(PREFIX)..."
	install -d $(DESTDIR)$(BINDIR)
	install -d $(DESTDIR)$(LIBDIR)
	install -d $(DESTDIR)$(DOCDIR)
	install -m 755 hfta.py $(DESTDIR)$(BINDIR)/hfta
	install -m 755 $(NATIVE_LIB) $(DESTDIR)$(LIBDIR)/
	install -m 644 README.md $(DESTDIR)$(DOCDIR)/
	install -m 644 docs/*.md $(DESTDIR)$(DOCDIR)/
	@echo "Installation complete. Run 'hfta --help' to get started."

# Uninstall target
uninstall:
	@echo "Uninstalling OpenHFTA from $(DESTDIR)$(PREFIX)..."
	rm -f $(DESTDIR)$(BINDIR)/hfta
	rm -f $(DESTDIR)$(LIBDIR)/$(NATIVE_LIB)
	rm -rf $(DESTDIR)$(DOCDIR)
	@echo "Uninstall complete."

.PHONY: all test test-core test-core-differential clean install uninstall
