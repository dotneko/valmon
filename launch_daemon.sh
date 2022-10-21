#!/bin/bash

PWD=$(pwd)
cd monitor && python daemon.py
cd $PWD
