#!/usr/bin/python
import getopt, sys, os, ROOT, math as m


def usage():
    """
    Usage function
    """
    print("""Usage: %s -p <Data path>

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


def findlines(ifile, device):
    f = open(ifile, 'r')
    lines = []
    try:
        for line in f:
            if line[0] == "#":
                continue
            if line.split()[1] == device:
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
            print(line)
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
        g.SetPoint(i, float(point[1]), float(point[3]))
        g.SetPointError(i, float(point[2]), float(0.01))#float(point[4]))
    saves["moneyplot"] = g
    return g


def hypfit(graph):
    hyp = ROOT.TF1("hyperbola", "fabs([0] + [1]/([2] -x[0]))")
    hyp.SetParName(0, "Offset")
    hyp.SetParameter(0, 0.)
    hyp.SetParLimits(0, 0., 0.05)
    hyp.SetParName(1, "Factor")
    hyp.SetParameter(1, 0.0001)
    hyp.SetParLimits(1, 0., 0.01)
    hyp.SetParName(2, "Resonance")
    hyp.SetParameter(2, 0.839)
    hyp.SetParLimits(2, 0.835, 0.845)
    hyp.SetNpx(10000)
    #graph.Draw('ap')
    #graph.FitPanel()
    graph.Fit(hyp, 'B')
    #raw_input("Press ENTER to continue"+"\n")
    saves["hyp"] = hyp
    return hyp


def main(argv):
    # default values
    path = os.path.expanduser("~mey") + os.sep + "Dropbox" + os.sep + "promotion" + os.sep + "beamtime" + os.sep + "2014-09" + os.sep + "data" + os.sep
    #os.path.expanduser("~mey") + os.sep + "beamtime" + os.sep + "fft" + os.sep + "data" + os.sep + "4s" + os.sep
    runfile = path + "runs_results.dat"
#    outfile = path + "runs_results.dat"
    global saves
    saves = {}
  
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
        elif opt == "-p":
            path = arg

    devices = [findlines(runfile, "RF-Solenoid"), findlines(runfile, "RF-Wien"), findlines(runfile, "RF-Dipole")]
    devicedata = []
    for device in devices:
        data = []
        for tune in device:
            if tune[1] == "RF-Solenoid":
                norm = 0.2
            else:
                norm = 0.3
            qy = float(tune[3])/750.603 -3
            dqy = 1./750.603
            fqy = 750.603*(2 - qy)
            dfqy = 1.
            runs = tune[0]
            resst = float(tune[7]) * norm / float(tune[2])#/ 750.603
            dresst = float(tune[8]) * norm / float(tune[2])#/750.603
            data.append([tune[1], qy, dqy, resst, dresst])
        devicedata.append(data)

    c = ROOT.TCanvas("c", "All Runs together")
    c.SetWindowSize(1600,900)
    c.SetTopMargin(0.16)
    c.SetBottomMargin(0.15)
    c.SetLeftMargin(0.11)
    c.SetRightMargin(-1.)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetTitleFontSize(0.05)
    ROOT.gStyle.SetLineScalePS(1)
    ROOT.gStyle.SetTitleSize(0.05, "xyz")
    ROOT.gStyle.SetLabelSize(0.05, "xyz")
    
    gdipole = graph(devicedata[2])  
    dipolefit = hypfit(gdipole)
    #hyperbola = gdipole.GetFunction("PrevFitTMP")
    #hyperbola.SetParName(0, "Offset")
    #hyperbola.SetParName(1, "Factor")
    #hyperbola.SetParName(2, "Resonance")
#    gdipole.GetFunction("hyperbola").SetLineStyle(3)
    gdipole.GetFunction("hyperbola").SetLineWidth(2)
    gdipole.SetMarkerStyle(33)
    gdipole.SetMarkerColor(ROOT.kRed)
    gdipole.SetLineColor(ROOT.kRed)
    gdipole.SetMarkerSize(1.5)
#    gdipole.SetLineWidth(2)

    gsol = graph(devicedata[0])    
    gsol.Fit('pol0', 'B')
    gsol.GetFunction('pol0').SetLineColor(ROOT.kBlue)
    gsol.GetFunction('pol0').SetLineStyle(3)
    gsol.GetFunction('pol0').SetLineWidth(2)
    gsol.SetMarkerStyle(22)
    gsol.SetMarkerColor(ROOT.kBlue)
    gsol.SetLineColor(ROOT.kBlue)
    gsol.SetMarkerSize(1.5)
#    gsol.SetLineWidth(2)

    gwien = graph(devicedata[1])    
    gwien.Fit('pol0', ' B')
    gwien.GetFunction('pol0').SetLineColor(ROOT.kRed+3)
    gwien.GetFunction('pol0').SetLineStyle(2)
    gwien.GetFunction('pol0').SetLineWidth(2)
    gwien.SetMarkerStyle(23)
    gwien.SetMarkerColor(ROOT.kRed+3)
    gwien.SetLineColor(ROOT.kRed+3)
    gwien.SetMarkerSize(1.5)
#    gwien.SetLineWidth(2)

    gdipole.GetXaxis().SetTitle("q_{y}")
    gdipole.GetXaxis().CenterTitle()
    gdipole.GetYaxis().SetTitle("f_{Py} / Hz")
    gdipole.GetYaxis().SetTitleOffset(0.7)
    gdipole.GetYaxis().SetNdivisions(505)
    gdipole.Draw('ap same')
    gsol.Draw('p same')
    gwien.Draw('p same')

    l = ROOT.TLine(2-871.429/750.603, gdipole.GetYaxis().GetXmin(), 2-871.429/750.603, gdipole.GetYaxis().GetXmax())#ROOT.gPad.GetUymax())
    l.SetLineColor(ROOT.kGray+2)
    l.SetLineWidth(2)
    l.Draw()

    c.Update()
    fcalc = ROOT.TF1("fcalc", "750.603 * (2 - x)", 750.603*(2-0.53), 750.603*(2-0.91))
    faxis = ROOT.TGaxis(ROOT.gPad.GetUxmin(), ROOT.gPad.GetUymax(), ROOT.gPad.GetUxmax(), ROOT.gPad.GetUymax(), "fcalc", 510, "-")
    faxis.SetLabelFont(42)
    faxis.SetTitleFont(42)
    faxis.SetTitle("f_{rev}(2-q_{y}) / kHz")
#    faxis.SetTitleOffset(1.2)
    faxis.SetTitleSize(0.05)
    faxis.SetLabelSize(0.05)
    faxis.CenterTitle()
    faxis.Draw()

#   c.Update()
    raw_input("Press ENTER to continue")
    c.Print("pdf/moneyplot.pdf")
    c.Print("png/moneyplot.png")
    c.SaveAs("moneyplot.root")
    #text = "\t".join(map(str, [runs, type, fqy, dfqy, qy, dqy, fPymin, dfPymin]))+"\n"
    #writelines(outfile, text)#"\t".join(map(str, [runs, type, fqy, dfqy, qy, dqy, fPymin, dfPymin]))+"\n")   

if __name__ == "__main__":
    main(sys.argv[1:])
