#!/usr/bin/python
import getopt, sys, os, ROOT, math as m


def usage():
    """
    Usage function
    """
    print("""Usage: %s -R <Run#,fRF> -F -s <StartTime> -e <EndTime> -S <Time Slice> -B -i <Iterations for Background Estimation> -f <Background Filter Order> -p <Data path>

-R   Single Run Number,RF Frequency / kHz, default 3449,871.4278
-F   Loop over run file, default runs.dat with
     [RUN #    StartTime    EndTime    DT    fPxStart    fPxEnd    fRF    fPy_start]
-s   Start time for analysis, default 96.
-e   Optinonal end time for analysis, default determined by ROOT Hist
-S   Slice time in case of projection through FFT
-B   Use background substraction, see https://root.cern.ch/root/htmldoc/TSpectrum.html#TSpectrum:Background
-i   Number of iterations for background estimation, default 20
-f   Order of background clipping filter, default 2
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


def writelines(ofile, text):
    f = open(ofile, 'r+')
    lines = []
    replaced = False
    try:
        for line in f:
            if line.split()[0] == text.split()[0]: # find duplicate runs
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
    #dampedsin = ROOT.TF1("dampedsin", "[0] * exp(-(x[0]-%f)/[1]) * sin(2*pi*[2]*(1+[3]*(x[0]-%f))*(x[0]-%f)+[4])+[5]" % (start, start, start), start, end)
    dampedsin = ROOT.TF1("dampedsin", "[0] * exp(-(x[0]-%f)/[1]) * (sin(2*pi*[2]*(x[0]-%f)+[4])+sin(2*pi*([2]+[3])*(x[0]-%f)+[4]))+[5]" % (start, start, start), start, end)
    #dampedsin = ROOT.TF1("dampedsin", "(16+[0]*(2*pi*[1]*(x[0]-%f))^2)^(-0.25) * exp(-[2]+[3]/(16+[0]*(2*pi*[1]*(x[0]-%f))^2)) * cos(2*pi*[1]*(x[0]-%f)-[4]*2*pi*[1]*(x[0]-%f)/(16+[0]*(2*pi*[1]*(x[0]-%f))^2)-0.5*atan([5]*2*pi*[1]*(x[0]-%f)))-[6]" % (start, start, start, start, start, start), start, end)
    dampedsin.SetParName(0, "Aplitude")
    dampedsin.SetParameter(0, abs(av_f - av_i))
    dampedsin.SetParLimits(0, 0.001, 0.5)
    dampedsin.SetParName(1, "Damping Time")
    dampedsin.SetParameter(1, 1.)
    dampedsin.SetParLimits(1, 0., 100.)
    dampedsin.SetParName(2, "Frequency")
    if fstart:
        dampedsin.SetParameter(2, fstart)
    else:
        dampedsin.SetParameter(2, 0.1)
    dampedsin.SetParLimits(2, 0.0001, 1.2)
    dampedsin.SetParName(3, "#delta Freq.")
    dampedsin.SetParameter(3, 0.0001)
    dampedsin.SetParLimits(3, 0., 0.1)
    dampedsin.SetParName(4, "Phase")
    dampedsin.SetParameter(4, 0.)
    dampedsin.SetParLimits(4, -m.pi, m.pi)
    dampedsin.SetParName(5, "Offset")
    dampedsin.SetParameter(5, av_f)
    dampedsin.SetParLimits(5, 0., -0.3)
    histLR.Fit(dampedsin, 'B R')
    sinf = dampedsin.GetParameter(2)
    dsinf = dampedsin.GetParError(2)
    fshift = dampedsin.GetParameter(3)
    dfshift = dampedsin.GetParError(3)
    saves["i"] = i
    saves["f"] = f
    saves["dampedsin"] = dampedsin
    return (i, av_i, dav_i, f, av_f, dav_f, dampedsin, sinf, dsinf, fshift, dfshift)


def peakfit(hist):
    #peak = ROOT.TF1("lorentz", "[0]/(1+((x[0]-[1])/[2])^2)", hist.GetXaxis().GetXmin(), hist.GetXaxis().GetXmax())
    peak = ROOT.TF1("gauss", 'gaus', hist.GetXaxis().GetXmin(), hist.GetXaxis().GetXmax())
    peak.SetParName(0, "Height")
    peak.SetParameter(0, 0.1)
    peak.SetParLimits(0, 0., 0.5)
    peak.SetParName(1, "Center")
    if fstart:
        peak.SetParameter(1, fstart)
    else:
        peak.SetParameter(1, 0.3)
    peak.SetParLimits(1, 0., 2.)
    peak.SetParName(2, "Width")
    peak.SetParameter(2, 0.02)
    peak.SetParLimits(2, 0., 0.1)
    hist.Fit(peak, 'B R')
    center = peak.GetParameter(1)
    dcenter = peak.GetParError(1)
    saves["peak"] = peak
    return (peak, center, dcenter)


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


def main(argv):
    # default values
    path = os.path.expanduser("~mey") + os.sep + "Dropbox" + os.sep + "promotion" + os.sep + "beamtime" + os.sep + "2014-09" + os.sep + "data" + os.sep
    #os.path.expanduser("~mey") + os.sep + "beamtime" + os.sep + "fft" + os.sep + "data" + os.sep + "4s" + os.sep
    runfile = path + "runs.dat"
    outfile = path + "runs_fitted.dat"
    global saves
    saves = {}
    runs = [[3449, 0, 0, 0, 0, 0, 0, 871.4278, 0]]
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
        opts, args = getopt.getopt(argv, "hR:FS:s:e:f:Bi:f:p:")
    except getopt.GetoptError as err:
        print(str(err) + "\n")
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt == "-R":
            runs = [[arg.split(",")[0], 0, 0, 0, 0, 0, 0, arg.split(",")[1], 0]]
        elif opt == "-F":
            runs = readlines(runfile)
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


    for run in runs:
        f = ROOT.TFile(path + "run_%s_out.root" % run[0], 'UPDATE')
        h2 = f.Get("LeftRight/h2STFFT_hCR_LR_%s" % run[0])
        h2.SetTitle("Vertical Polarization Oscillation Frequency")
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
        h2_py.GetYaxis().SetTitle("Amp.")
        h2_py.GetXaxis().SetTitle("f / Hz")
        h1 = f.Get("LeftRight/hCR_LR_%s" % run[0])
        h1.GetXaxis().SetRangeUser(start, end)
        h1.SetTitle("Run %s: Vertical Polarization" % run[0])

        ROOT.gStyle.SetNumberContours(99)
        ROOT.gStyle.SetOptStat(0)
        ROOT.gStyle.SetOptFit(11)
        c = ROOT.TCanvas("c", "Run %s Vertical Polarization" % run[0])
        c.SetWindowSize(1600, 900)
        c.SetFrameFillColor(0)
        c.SetFrameFillStyle(0)
        c.SetFrameBorderMode(0)
        pad1 = ROOT.TPad("pad1", "CR",    0. , 0.5, 0.6, 1. )
        pad2 = ROOT.TPad("pad2", "Stats", 0.6, 0.5, 1. , 1. )
        pad3 = ROOT.TPad("pad3", "STFFT", 0. , 0. , 0.6, 0.5)
        pad4 = ROOT.TPad("pad4", "Slice", 0.6, 0. , 1. , 0.5)
        pad1.Draw()
        pad2.Draw()
        pad3.Draw()
        pad4.Draw()
    
        pad1.cd()
        if astart: t0 = astart
        else: t0 = start + 0.75
        if aend: tf = aend
        else: tf = end - 1.
        if run[8]: fstart = float(run[8])
        results = sinfit(h1, t0, tf)
        h1.Draw('sames')
        print("Initial avarage CR = %.3f +- %.3f" % (results[1], results[2]))
        print("Final avarage CR = %.3f +- %.3f" % (results[4], results[5]))
        print("Fitted f = (%.4f +- %.4f) Hz" % (results[7], results[8]))
        print("Fitted del f = (%.4f +- %.4f) Hz"  % (results[9], results[10]))
        fstart = results[7]

        pad3.cd()
        h2.Draw('ColZ')
        if slice:
            l.SetLineColor(ROOT.kRed)
            l.SetLineWidth(4)
            l.Draw()
                   
        pad4.cd()
        h = h2_py.Clone("h")
        if bckg:
            h.ShowBackground(bckgiter, '%s BackOrder%s nosmoothing nocompton same' % (bckgwindow, bckgfilter))
            # BackSmoothing3
            h_b = ROOT.gDirectory.Get("h_background")
            h.Add(h_b, -1.)
        peak = peakfit(h)
        print("FFT f_Py = (%.4f +- %.4f) Hz" % (peak[1], peak[2]))
        h2_py.SetFillColor(ROOT.kGray)
        h2_py.Draw('hbar')
        if bckg:
            f_h2_py_b = fliph(h_b)
            f_h2_py_b.SetLineColor(ROOT.kGray+2)
            f_h2_py_b.SetLineWidth(2)
            f_h2_py_b.Draw('same')
            h.SetFillColor(ROOT.kBlue)
            h.Draw('hbar E1 sames')
        f_peak = flipf(peak[0], 100)
        f_peak.SetLineColor(ROOT.kRed)
        f_peak.SetLineWidth(2)
        f_peak.Draw('same')
    
        pad2.cd()
        t = ROOT.TLatex()
        t.DrawLatex(0.1, 0.8, "Final #LT CR #GT = %.3f #pm %.3f" % (results[4], results[5]))
        t.DrawLatex(0.1, 0.6, "Fitted f_{P_{y}} = (%.4f #pm %.4f) Hz" % (results[7], results[8]))
        t.DrawLatex(0.1, 0.4, "Fitted #delta f_{P_{y}} = (%.4f #pm %.4f) Hz" % (results[9], results[10]))
        t.DrawLatex(0.1, 0.2, "FFT f_{P_{y}} = (%.4f #pm %.4f) Hz" % (peak[1], peak[2]))

        c.Update()
        #raw_input("Press ENTER to continue")
        writelines(outfile, "\t".join(map(str, [run[0], run[7], results[4], results[5], results[7], results[8], peak[1], peak[2]])) +"\n")
        if slice:
            c.Print("pdf/run_%s_%s_analysis" % (run[0], slice) + ".pdf")
            c.Print("png/run_%s_%s_analysis" % (run[0], slice) + ".png")
        else:
            c.Print("pdf/run_%s_analysis" % run[0] + ".pdf")
            c.Print("png/run_%s_analysis" % run[0] + ".png")    
        f.cd("Results")      
        h1.Write()
        h.Write("hFT_dhCRLRWindow")
        c.Write()
        f.Close()


if __name__ == "__main__":
    main(sys.argv[1:])
