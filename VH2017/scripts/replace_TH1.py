import ROOT,os

file_with_old_histo = "vhbb_Zmm-2017.root"
old_histo_name = "BDT_Zhf_low_Zuu_s_Top_CMS_bTagWeightDeepBLFStats1_13TeV_pt3_eta1Up"

file_with_replacing_histo = "vhbb_Zee-2017.root"
replacing_histo_name = "BDT_Zhf_high_Zee_ggZH_hbb_CMS_bTagWeightDeepBLFStats1_13TeV_pt4_eta2Down"


###################################
print ''
f_with_old_histo = ROOT.TFile(file_with_old_histo)
old_histo = f_with_old_histo.Get(old_histo_name)
print 'f_with_old_histo:',f_with_old_histo.GetName()
print 'old_histo:',old_histo.GetName()
print ''

f_with_replacing_histo = ROOT.TFile(file_with_replacing_histo) 
replacing_histo = f_with_replacing_histo.Get(replacing_histo_name)
print 'f_with_replacing_histo:',f_with_old_histo.GetName()
print 'replacing_histo:',replacing_histo.GetName()
print ''

replacing_histo.SetName(old_histo.GetName())
replacing_histo.SetTitle(old_histo.GetTitle())

os.system("cp "+file_with_old_histo+" "+file_with_old_histo.replace(".root","_replaced.root"))
f_with_replaced_histo = ROOT.TFile(file_with_old_histo.replace(".root","_replaced.root"),"UPDATE") 
replacing_histo.Write()
print 'f_with_replaced_histo:',f_with_old_histo.GetName()
print ''

f_with_replaced_histo.Write()
