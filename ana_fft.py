#!/usr/bin/python                                                                                       
import os, subprocess

f = open("runs.dat", 'r')
l = []
for l in f:
    param = l.split()
    print(param)
    if (l[0] == "#") or (os.path.isfile("./data/run_%s_out.root" % param[0]) == True):
        continue
    out = False
    while out == False:
        fft = subprocess.Popen(["/home/edm/May15/FourierSpectra/FFTsMain", param[0]])
        #fft = subprocess.Popen(["./Sep2014Main", param[0], param[1], param[2], param[3], param[4], par\
am[5]] 1)                                                                                               
        fft.wait()
        out = os.path.isfile("./data/run_%s_out.root" % param[0])
f.close
