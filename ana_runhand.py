#!/usr/bin/python
import getopt, sys, os, ROOT, math as m

def usage():
    """
    Usage function
    """
    print("""Usage: %s -R <Run#,fRF> -s <Start Time> -e <End Time> -S <Time Slice> -B -i <Iterations for Background Estimation> -f <Background Filter Order> -p <Data subpath>

-R   Run number, RF Frequency / kHz, default 3449,871.4278
-s   Start time for analysis, default 96.
-e   Optinonal end time for analysis, default determined by ROOT Hist
-S   Slice time for projection through FFT
-B   Use background substraction, see https://root.cern.ch/root/htmldoc/TSpectrum.html#TSpectrum:Background
-i   Number of iterations for background estimation, default 20
-f   Order of background clipping filter, default 2
-p   Optional path to data folder, default "/home/mey/Dropbox/promotion/beamtime/data/"
""" %sys.argv[0])


def writelines(ofile, text):
    f = open(ofile, 'r+')
    lines = []
    replaced = False
    try:
        for line in f:
            if line.split()[0] == text.split()[0]: #find duplicates
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


def sinfit(histLR, start, end):
    i = ROOT.TF1("i", "[0]", start - 10., start - .1)
    histLR.Fit(i, 'B R N')
    av_i = i.GetParameter(0)
    dav_i = i.GetParError(0)
    f = ROOT.TF1("f", "[0]", end-5., end+5.)
    histLR.Fit(f, 'B R N')
    av_f = f.GetParameter(0)
    dav_f = f.GetParError(0)
    #dampedsin = ROOT.TF1("dampedsin", "[0]*exp(-(x[0]-%f)/[1])*sin(2*pi*[2]*(1+[3]*(x[0]-%f))*(x[0]-%f)+[4])+[5]" % (start, start, start), start, end)
    dampedsin = ROOT.TF1("dampedsin", "[0] * exp(-(x[0]-%f)/[1]) * (sin(2*pi*[2]*(x[0]-%f)+[4])+sin(2*pi*([2]+[3])*(x[0]-%f)+[4]))+[5]" % (start, start, start), start, end)
    dampedsin.SetParameter(0, abs(av_f - av_i))
    dampedsin.SetParLimits(0, 0.001, 0.5)
    dampedsin.SetParameter(1, 1.)
    dampedsin.SetParLimits(1, 0., 100.)
    if fstart:
        dampedsin.SetParameter(2, fstart)
    else:
        dampedsin.SetParameter(2, 0.1)
    dampedsin.SetParLimits(2, 0.0001, 1.2)
    dampedsin.SetParameter(3, 0.0001)
    dampedsin.SetParLimits(3, 0., 0.1)
    dampedsin.SetParameter(4, 0.)
    dampedsin.SetParLimits(4, -m.pi, m.pi)
    dampedsin.SetParameter(5, av_f)
    dampedsin.SetParLimits(5, 0., -0.3)
    histLR.Draw()
    histLR.FitPanel()
    raw_input("Press ENTER to continue"+"\n")
    #histLR.Fit(dampedsin, 'B R')
    saves["i"] = i
    saves["f"] = f
    saves["dampedsin"] = dampedsin
    return (i, av_i, dav_i, f, av_f, dav_f, dampedsin)


def peakfit(hist, iter, window, filter):
    ctemp = ROOT.TCanvas("temp")
    lorentz = ROOT.TF1("lorentz", "[0]/(1+((x[0]-[1])/[2])^2)")
    lorentz.SetParameter(0, 0.1)
    lorentz.SetParLimits(0, 0., 0.5)
    if fstart:
        lorentz.SetParameter(1, fstart)
    else:
        lorentz.SetParameter(1, 0.3)
    lorentz.SetParLimits(1, 0., 2.)
    lorentz.SetParameter(2, 0.02)
    lorentz.SetParLimits(2, 0., 0.1,)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptFit(1)
    h = hist.Clone("h")
    hist.Draw()
    if bckg:
        h.ShowBackground(iter, '%s BackOrder%s nosmoothing nocompton same' % (window, filter))
        # BackSmoothing3
        h_b = ROOT.gDirectory.Get("h_background")
        h.Add(h_b, -1.)
        h.Draw('sames')
    ctemp.Update()
    h.FitPanel()
    raw_input("Press ENTER to continue"+"\n")
    saves["lorentz"] = lorentz
    return (h_b, h)


def fliph(hist):
    graph = ROOT.TGraphErrors()
    for i in xrange(hist.GetNbinsX()):
        graph.SetPoint(i, hist.GetBinContent(i), hist.GetXaxis().GetBinCenter(i))
        graph.SetPointError(i, hist.GetBinError(i), 0)
        i = i+1
    return graph


def flipf(f, res):
    graph = ROOT.TGraph()
    xmin = f.GetXmin()
    xmax = f.GetXmax()
    dx = (xmax-xmin)/res
    for i, x in enumerate([xmin+j*dx for j in xrange(0, res+1)]):
        graph.SetPoint(i, f.Eval(x), x)
    return graph


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
    outfile = path + "runs_fitted.dat"
    global saves
    saves = {}    
    run = 3449
    fRF = 871.4278
    global slice
    slice = ''
    global astart
    astart = ''
    global aend
    aend = ''
    global fstart
    fstart = ''
    global bckg
    bckg = ''
    bckgwindow = "BackDecreasingWindow"#"BackIncreasingWindow"
    bckgiter = 20
    bckgfilter = "2"
   
    # read in CMD arguments
    try:                                
        opts, args = getopt.getopt(argv, "hR:S:s:e:f:Bi:f:p:")
    except getopt.GetoptError as err:
        print(str(err) + "\n")
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-R":
            run = int(arg.split(",")[0])
            fRF = float(arg.split(",")[1])
        elif opt == "-S":
            slice = float(arg)
        elif opt == "-s":
            astart = float(arg)
        elif opt == "-e":
            aend = float(arg)
        elif opt == "-f":
            fstart = float(arg)
        elif opt == "-B":
            bckg = True
        elif opt == "-i":
            bckgiter = int(arg)
        elif opt == "-f":
            bckgfilter = str(arg)
        elif opt == "-p":
            path = arg

    f = ROOT.TFile(path + "run_%s_out.root" % run, 'UPDATE')

    h2 = f.Get("LeftRight/h2STFFT_hCR_LR_%s" %run)
    h2.SetTitle("Vertical Polarization Oscillation Frequency")
    maxi(h2, True)
    start = h2.GetXaxis().GetXmin()
    end = h2.GetXaxis().GetXmax()
    if slice:
        h2_at = h2.GetXaxis().FindBin(slice)
        h2_py = h2.ProjectionY("h2_py", h2_at, h2_at+1)
        h2_py.SetTitle("Projection at %.1f s" % slice)
        l = ROOT.TLine(slice, h2.GetYaxis().GetXmin(), slice, h2.GetYaxis().GetXmax())
    else:
        h2_py = f.Get("LeftRight/hFT_hCRLRWindow")
        h2_py.SetTitle("Projection")
    maxi(h2_py)
    #h2_py.GetXaxis().SetTitle("f / Hz")
    h2_py.GetYaxis().SetTitle("Amp.")
    h2_py_b, h2_py_clean = peakfit(h2_py, bckgiter, bckgwindow, bckgfilter)
    h1 = f.Get("LeftRight/hCR_LR_%s" % run)
    h1.SetTitle("Run %s: Vertical Polarization" % run)
    maxi(h1)
    h1.GetXaxis().SetRangeUser(start, end)
    
    c = ROOT.TCanvas("c", "Run %s Vertical Polarization" % run)
    c.SetWindowSize(1600, 900)
    ROOT.gStyle.SetNumberContours(99)
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptFit(11)
    ROOT.gStyle.SetTitleFontSize(0.07)
    ROOT.gStyle.SetLineScalePS(1)
    ROOT.gStyle.SetTitleSize(0.07, "xyz")
    ROOT.gStyle.SetLabelSize(0.07, "xyz")
    pad1 = ROOT.TPad("pad1", "CR",    0. , 0.5, 0.6, 1. )
    pad2 = ROOT.TPad("pad2", "Stats", 0.6, 0.5, 1. , 1. )
    pad3 = ROOT.TPad("pad3", "STFFT", 0. , 0. , 0.6, 0.5)
    pad4 = ROOT.TPad("pad4", "Slice", 0.6, 0. , 1. , 0.5)
    pad1.Draw()
    pad2.Draw()
    pad3.Draw()
    pad4.Draw()
    #c.Divide(2,2)
    
    #c.cd(1)
    pad1.cd()
    pad1.SetLeftMargin(0.15)
    pad1.SetBottomMargin(0.15)
    if astart: t0 = astart
    else: t0 = start + 0.75
    if aend: tf = aend
    else: tf = end - 1.
    results = sinfit(h1, t0, tf)
    dsin = h1.GetFunction("PrevFitTMP")
    dsin.SetParName(0, "Amplitude")
    dsin.SetParName(1, "Damping Time")
    dsin.SetParName(2, "Frequency")
    dsin.SetParName(3, "#deltaFrequency")
    dsin.SetParName(4, "Phase")
    dsin.SetParName(5, "Offset")
    sinf = dsin.GetParameter(2)
    dsinf = dsin.GetParError(2)
    fshift = dsin.GetParameter(3)
    dfshift = dsin.GetParError(3)
    h1.Draw('sames')
    h1.GetYaxis().SetRangeUser(-0.4,0.4);
    print("Initial avarage CR = %.3f +- %.3f" % (results[1], results[2]))
    print("Final avarage CR = %.3f +- %.3f" % (results[4], results[5]))
    print("Fitted f = (%.4f +- %.4f) Hz" % (sinf, dsinf))
    print("Fitted del f = (%.4f +- %.4f) Hz^2"  % (fshift, dfshift))

    #c.cd(3)
    pad3.cd()
    pad3.SetLeftMargin(0.15)
    pad3.SetBottomMargin(0.15)
    pad3.SetRightMargin(0.15)
    h2.Draw('ColZ')
    if slice:
        l.SetLineColor(ROOT.kRed)
        l.SetLineWidth(4)
        l.Draw()
                   
    #c.cd(4)
    pad4.cd()
    #pad4.SetLeftMargin(0.15)
    pad4.SetBottomMargin(0.15)
    peak = h2_py_clean.GetFunction("PrevFitTMP")
    peak.SetParName(0, "Height")
    peak.SetParName(1, "Center")
    peak.SetParName(2, "Width")
    chi2 = peak.GetChisquare()
    ndf = peak.GetNDF()
    mean = peak.GetParameter(1)
    dmean = peak.GetParError(1)
    print("FFT f_Py = (%.4f +- %.4f) Hz" % (mean, dmean))
    h2_py.SetFillColor(ROOT.kGray)
    h2_py.Draw('hbar')
    if bckg:
        f_h2_py_b = fliph(h2_py_b)
        f_h2_py_b.SetLineColor(ROOT.kGray+2)
        f_h2_py_b.SetLineWidth(2)
        f_h2_py_b.Draw('same')
        h2_py_clean.SetFillColor(ROOT.kBlue)
        h2_py_clean.Draw('hbar E1 sames')
    f_peak = flipf(peak, 100)
    f_peak.SetLineColor(ROOT.kRed)
    f_peak.SetLineWidth(2)
    f_peak.Draw('same')

    
    #c.cd(2)
    pad2.cd()
    t = ROOT.TLatex()
    t.SetTextSize(0.08)
    t.SetTextFont(42)
    t.DrawLatex(0.1, 0.8, "Final #LTCR_{LR}#GT = %.3f #pm %.3f" % (results[4], results[5]))
    t.DrawLatex(0.1, 0.6, "Fitted f_{P_{y}} = (%.4f #pm %.4f) Hz" % (sinf, dsinf))
    t.DrawLatex(0.1, 0.4, "Fitted #deltaf_{P_{y}} = (%.4f #pm %.4f) Hz" % (fshift, dfshift))
    t.DrawLatex(0.1, 0.2, "FFT f_{P_{y}} = (%.4f #pm %.4f) Hz" % (mean, dmean))
    c.Update()
    print("\t".join(map(str, [run, fRF, results[4], results[5], sinf, dsinf, mean, dmean])) +"\n")
    raw_input("Press ENTER to quit")
    writelines(outfile, "\t".join(map(str, [run, fRF, results[4], results[5], sinf, dsinf, mean, dmean])) +"\n")
#"\t".join(map(str, [run[0], run[7], results[4], results[5], results[7], results[8], mean, dmean])) +"\n")
    if slice:
        c.Print("./pdf/run_%s_%s_analysis" % (run, slice) + ".pdf")
        c.Print("./png/run_%s_%s_analysis" % (run, slice) + ".png")
    else:
        c.Print("./pdf/run_%s_analysis" % run + ".pdf")
        c.Print("./png/run_%s_analysis" % run + ".png")
    f.cd("Results")      
    h1.Write()
    h2_py_clean.Write("hFT_dhCRLRWindow")
    c.Write()
    f.Close()


if __name__ == "__main__":
    main(sys.argv[1:])
