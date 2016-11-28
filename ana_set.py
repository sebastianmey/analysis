#!/usr/bin/python
import getopt, sys, os, ROOT, math as m


def usage():
    """
    Usage function
    """
    print("""Usage: %s -F -R <"Run#1,Run#2,... RF Type Amplitude fqy"> -p <Data path>

-F   Loop over run file, default runs_results.dat
-R   Run Numbers in set + Type of RF device + Amplitude Scaling + Vertical betatron oscilaltion frequency
-p   Optional path to data folder, default "/home/mey/Dropbox/promotion/beamtime/data/"
""" %sys.argv[0])


def readlines(ifile):
    f = open(ifile, 'r')
    lines = []
    try:
        for line in f:
            if line[0] == "#":
                continue
            lines.append(line.split())
    finally:
        f.close()
        return lines


def findlines(ifile, runs):
    f = open(ifile, 'r')
    lines = []
    try:
        for line in f:
            for run in runs:
                if line.split()[0] == run:
                    lines.append(line.split())
    finally:
        f.close()
        return lines


def writelines(ofile, text):
    f = open(ofile, 'r+')
    lines = []
    replaced = False
    try:
        for line in f:
            if line.split()[0] == text.split()[0]: # find duplicates
                line = text
                lines.append(line)
                replaced = True
            else:
                lines.append(line)
        if replaced == False:
            lines.append(text)
        f.seek(0)
        f.truncate()
        f.writelines(lines)
    finally:
        f.close()

def graph(points):
    g = ROOT.TGraphErrors()
    for i, point in enumerate(points):
        g.SetPoint(i, float(point[1]) * 1000., float(point[6]))
        g.SetPointError(i, 0, float(point[7]))
    return g


def resfit(graph):
    pol2 = ROOT.TF1("scheitelpunktsform", "[0] * (x[0] - [1])^2 + [2]")
    pol2.SetParName(0, "Factor")
    pol2.SetParameter(0, 1.)
    #pol2.SetParLimits(0, 0., 10.)
    pol2.SetParName(1, "Minimum")
    pol2.SetParameter(1, 871429)
    pol2.SetParLimits(1, 871420., 871430.)
    pol2.SetParName(2, "Offset")
    pol2.SetParameter(2, graph.GetYaxis().GetXmin())
    pol2.SetParLimits(2, 0., 1.)
    graph.Draw('ap')
    graph.FitPanel()
    #graph.Fit(pol2, 'B Minuit2 Simplex')
    raw_input("Press ENTER to continue"+"\n")
    saves["pol2"] = pol2
    return pol2

def maxi(hist, zaxis=False, size = 0.08):
    hist.SetTitleSize(0.07,'t') 
    hist.GetXaxis().SetTitleOffset(0.8)
    hist.GetXaxis().SetTitleSize(size)
    hist.GetXaxis().SetLabelSize(size)
    hist.GetXaxis().SetNdivisions(505)
    hist.GetYaxis().SetTitleOffset(0.6)
    hist.GetYaxis().SetTitleSize(size)
    hist.GetYaxis().SetLabelSize(size)
    hist.GetYaxis().SetNdivisions(505)
    if zaxis != False:
        hist.GetZaxis().SetTitleOffset(0.7)
        hist.GetZaxis().SetTitleSize(size)
        hist.GetZaxis().SetLabelSize(size)
        hist.GetZaxis().SetNdivisions(505)

def main(argv):
    # default values
    path = os.path.expanduser("~mey") + os.sep + "Dropbox" + os.sep + "promotion" + os.sep + "beamtime" + os.sep + "2014-09" + os.sep + "data" + os.sep
    #os.path.expanduser("~mey") + os.sep + "beamtime" + os.sep + "fft" + os.sep + "data" + os.sep + "4s" + os.sep
    runfile = path + "runs_fitted.dat"
    outfile = path + "runs_results.dat"
    global saves
    saves = {}
    set = [0, "RF-Device", 0., 0.]
  
    # read in CMD arguments
    try:                                
        opts, args = getopt.getopt(argv, "hFR:t:f:p:")
    except getopt.GetoptError as err:
        print(str(err) + "\n")
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-F":
            set = readlines(outfile)
        elif opt == "-R":
            set = [arg.split()]
        elif opt == "-p":
            path = arg

    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptFit(1)
    ROOT.gStyle.SetLineScalePS(1)
    ROOT.gStyle.SetTitleFontSize(0.07)
    ROOT.gStyle.SetTitleSize(0.07, "xyz")
    ROOT.gStyle.SetLabelSize(0.07, "xyz")

    for settings in set:
        type = settings[1]
        scaling = settings[2]
        fqy = float(settings[3])
        qy = fqy/750.603
        dfqy = 1.
        dqy = 1./750.603
        runs = settings[0]
        data = findlines(runfile, runs.split(","))
        g1 = graph(data)
        g1.GetXaxis().SetNdivisions(1008)
        g1.GetXaxis().SetTitle("f_{rev}(1-#gamma G) / Hz")
        g1.GetYaxis().SetTitle("f_{Py} / Hz")

        c = ROOT.TCanvas("c", "%s at %s, Runs %s" % (type, scaling, runs))
        c.SetWindowSize(1600, 900)
        c.SetLeftMargin(0.15)
        c.SetBottomMargin(0.15)

        resfit(g1)
        pol2 = g1.GetFunction("PrevFitTMP")
        pol2.SetParName(0, "Factor")
        pol2.SetParName(1, "Minimum")
        pol2.SetParName(2, "Offset")
        fPymin = pol2.GetParameter(2)
        dfPymin = pol2.GetParError(2)
        g1.SetTitle("%s @ Q_{y} = %.3f:  f_{Py min} = (%.3f #pm %.3f) Hz" % (type, qy, fPymin, dfPymin))
        g1.SetMarkerStyle(2)
#        g1.GetXaxis().SetTitleOffset(1.)
        g1.GetXaxis().SetNdivisions(1002)
#        g1.GetYaxis().SetTitleOffset(1.)
#        g1.GetYaxis().SetNdivisions(505)

        g1.Draw('ap')

        c.Update()
        raw_input("Press ENTER to continue")
        c.Print("pdf/run_%s_results" % runs + ".pdf")
        c.Print("png/run_%s_results" % runs + ".png")
        text = "\t".join(map(str, [runs, type, scaling, fqy, dfqy, qy, dqy, fPymin, dfPymin]))+"\n"
        print(text)
        writelines(outfile, text)#"\t".join(map(str, [runs, type, scaling, fqy, dfqy, qy, dqy, fPymin, dfPymin]))+"\n")   

if __name__ == "__main__":
    main(sys.argv[1:])
