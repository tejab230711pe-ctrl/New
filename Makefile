###############################################################################
################### MOOSE Application Standard Makefile #######################
###############################################################################

MOOSE_DIR          ?= /home/teja/projects/moose
LIBMESH_DIR        ?= /home/teja/miniforge3/envs/moose
WASP_DIR           ?= /home/teja/miniforge3/envs/moose
FRAMEWORK_DIR      := $(MOOSE_DIR)/framework
ADDITIONAL_CPPFLAGS += -Wall -Wextra -I$(CURDIR)/include -I$(CURDIR)/src
include $(FRAMEWORK_DIR)/build.mk
include $(FRAMEWORK_DIR)/moose.mk

################################## MODULES ####################################
ALL_MODULES               := no
CHEMICAL_REACTIONS        := no
CONTACT                   := yes
FLUID_PROPERTIES          := no
HEAT_TRANSFER             := yes
LINEAR_ELASTICITY         := no
MISC                      := no
NAVIER_STOKES             := no
PHASE_FIELD               := no
POROUS_FLOW               := no
SOLID_MECHANICS           := yes
XFEM                      := no
include $(MOOSE_DIR)/modules/modules.mk
###############################################################################

# dep apps
APPLICATION_DIR    := $(CURDIR)
APPLICATION_NAME   := rotating_disk_deposition
BUILD_EXEC         := yes
GEN_REVISION       := no
include            $(FRAMEWORK_DIR)/app.mk
