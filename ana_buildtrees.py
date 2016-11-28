#!/usr/bin/python                                                                                       
import os, shutil, subprocess

f = open("./runs.dat", 'r')
l = []
for l in f:
    if l[0] == "#":
        continue
    print("Analyzing  Run "+l.split()[0])
    tree = subprocess.Popen(["/home/edm/RootSorter14/core/bin/edda_ana", "-fin", "cluster:/data0/edm/li\
nks/run_"+l.split()[0], "-n", "run_"+l.split()[0], "-r ", l.split()[0], "-mode", "0", "-tree", "-abort"\
])
    tree.wait()
    shutil.copy2("run_"+l.split()[0]+"-tree.root", "/home/edm/Trees")
f.close
