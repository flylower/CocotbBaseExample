TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

VERILOG_SOURCES = $(PWD)/ram.v
TOPLEVEL = single_port_ram

MODULE := ram_tb

include $(shell cocotb-config --makefiel --makefiles)/Makefile.sim

