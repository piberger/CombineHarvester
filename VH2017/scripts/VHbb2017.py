#!/usr/bin/env python

import CombineHarvester.CombineTools.ch as ch
import CombineHarvester.VH2017.systematics as systs
import ROOT as R
import glob
import numpy as np
import os
import sys
import argparse

def adjust_shape(proc,nbins):
  new_hist = proc.ShapeAsTH1F();
  new_hist.Scale(proc.rate())
  for i in range(1,new_hist.GetNbinsX()+1-nbins):
    new_hist.SetBinContent(i,0.)
  proc.set_shape(new_hist,True)

def drop_zero_procs(chob,proc):
  null_yield = not (proc.rate() > 0.)
  if(null_yield):
    chob.FilterSysts(lambda sys: matching_proc(proc,sys)) 
  return null_yield

def drop_znnqcd(chob,proc):
  drop_process =  proc.process()=='QCD' and proc.channel()=='Znn' and proc.bin_id()==5
  if(drop_process):
    chob.FilterSysts(lambda sys: matching_proc(proc,sys)) 
  return drop_process


def drop_zero_systs(syst):
  null_yield = (not (syst.value_u() > 0. and syst.value_d()>0.) ) and syst.type() in 'shape'
  if(null_yield):
    print 'Dropping systematic ',syst.name(),' for region ', syst.bin(), ' ,process ', syst.process(), '. up norm is ', syst.value_u() , ' and down norm is ', syst.value_d()
    #chob.FilterSysts(lambda sys: matching_proc(proc,sys)) 
  return null_yield


def matching_proc(p,s):
  return ((p.bin()==s.bin()) and (p.process()==s.process()) and (p.signal()==s.signal()) 
         and (p.analysis()==s.analysis()) and  (p.era()==s.era()) 
         and (p.channel()==s.channel()) and (p.bin_id()==s.bin_id()) and (p.mass()==s.mass()))

def remove_norm_effect(syst):
  syst.set_value_u(1.0)
  syst.set_value_d(1.0)

def symm(syst,nominal):
  print 'Symmetrising systematic ', syst.name(), ' in region ', syst.bin(), ' for process ', syst.process()
  hist_u = syst.ShapeUAsTH1F()
  hist_u.Scale(nominal.Integral()*syst.value_u())
  hist_d = nominal.Clone()
  hist_d.Scale(2)
  hist_d.Add(hist_u,-1)
  syst.set_shapes(hist_u,hist_d,nominal)
  
  
def symmetrise_syst(chob,proc,sys_name):
  nom_hist = proc.ShapeAsTH1F()
  nom_hist.Scale(proc.rate())
  chob.ForEachSyst(lambda s: symm(s,nom_hist) if (s.name()==sys_name and matching_proc(proc,s)) else None)

def increase_bin_errors(proc):
  print 'increasing bin errors for process ', proc.process(), ' in region ', proc.bin()
  new_hist = proc.ShapeAsTH1F();
  new_hist.Scale(proc.rate())
  for i in range(1,new_hist.GetNbinsX()+1):
    new_hist.SetBinError(i,np.sqrt(2)*new_hist.GetBinError(i))
  proc.set_shape(new_hist,False)

  

parser = argparse.ArgumentParser()
parser.add_argument(
 '--channel', default='all', help="""Which channels to run? Supported options: 'all', 'Znn', 'Zee', 'Zmm', 'Zll', 'Wen', 'Wmn','Wln'""")
parser.add_argument(
 '--output_folder', default='vhbb2017', help="""Subdirectory of ./output/ where the cards are written out to""")
parser.add_argument(
 '--auto_rebin', action='store_true', help="""Rebin automatically?""")
parser.add_argument(
 '--bbb_mode', default=1, type=int, help="""Sets the type of bbb uncertainty setup. 0: no bin-by-bins, 1: autoMCStats""")
parser.add_argument(
 '--zero_out_low', action='store_true', help="""Zero-out lowest SR bins (purely for the purpose of making yield tables""")
parser.add_argument(
 '--Zmm_fwk', default='AT', help="""Framework the Zmm inputs were produced with. Supported options: 'Xbb', 'AT'""")
parser.add_argument(
 '--Zee_fwk', default='AT', help="""Framework the Zee inputs were produced with. Supported options: 'Xbb', 'AT'""")
parser.add_argument(
 '--Wmn_fwk', default='AT', help="""Framework the Wmn inputs were produced with. Supported options: 'Xbb', 'AT'""")
parser.add_argument(
 '--Wen_fwk', default='AT', help="""Framework the Wen inputs were produced with. Supported options: 'Xbb', 'AT'""")
parser.add_argument(
 '--Znn_fwk', default='AT', help="""Framework the Znn inputs were produced with. Supported options: 'Xbb', 'AT'""")
parser.add_argument(
 '--year', default='2017', help="""Year to produce datacards for (2017 or 2016)""")
parser.add_argument(
 '--extra_folder', default='', help="""Additional folder where cards are""")
parser.add_argument(
 '--rebinning_scheme', default='v2-whznnh-hf-dnn', help="""Rebinning scheme for CR and SR distributions""")
parser.add_argument(
 '--doVV', default=False, help="""if True assume we are running the VZ(bb) analysis""")
parser.add_argument(
 '--mjj',  default=False, help="""if True assume we are running the mjj analysis""")
parser.add_argument(
 '--decorrelateZjNLO', action='store_true', default=False) 
parser.add_argument(
 '--multi', action='store_true', default=False) 
parser.add_argument(
 '--decorrelateWlnZnnWjets', action='store_true', default=False) 


args = parser.parse_args()

if args.multi and 'multi' not in args.rebinning_scheme:
    args.rebinning_scheme = ''
    print "\x1b[31mINFO: multi DNN selected and rebinning turned off!!!\x1b[0m"

cb = ch.CombineHarvester()

# uncomment to play with negative bins or large error bins with bin.error > bin.content
# cb.SetFlag('zero-negative-bins-on-import', 1)
# cb.SetFlag('check-large-weights-bins-on-import', 1)
# cb.SetFlag('reduce-large-weights-bins-on-import', 1)

shapes = os.environ['CMSSW_BASE'] + '/src/CombineHarvester/VH2017/shapes/'

mass = ['125']

chns = []

if args.channel=="all":
  chns = ['Wen','Wmn','Znn','Zee','Zmm']

if args.channel == 'ZllCombined':
    chns.append(args.channel)
else:
    if 'Zll' in args.channel or 'Zmm' in args.channel:
      chns.append('Zmm')
    if 'Zll' in args.channel  or 'Zee' in args.channel:
      chns.append('Zee')

if 'Wln' in args.channel or 'Wmn' in args.channel or ('Znn' in args.channel and (not args.multi or not args.decorrelateWlnZnnWjets)):
  chns.append('Wmn')
if 'Wln' in args.channel or 'Wen' in args.channel or ('Znn' in args.channel and (not args.multi or not args.decorrelateWlnZnnWjets)):
  chns.append('Wen')
if 'Znn' in args.channel:
  chns.append('Znn')

year = args.year
if year is not "2016" and not "2017":
  print "Year ", year, " not supported! Choose from: '2016', '2017'"
  sys.exit()

input_fwks = {
  'Wen' : args.Wen_fwk, 
  'Wmn' : args.Wmn_fwk,
  'Zee' : args.Zee_fwk,
  'Zmm' : args.Zmm_fwk,
  'Znn' : args.Znn_fwk
}

for chn in chns:
  if not input_fwks[chn]=='Xbb' and not input_fwks[chn]=='AT':
    print "Framework ", input_fwks[chn], "not supported! Choose from: 'Xbb','AT'"
    sys.exit()

folder_map = {
  'Xbb' : 'Xbb/'+args.extra_folder,
  'AT'  : 'AT/'+args.extra_folder
}

input_folders = {
  'Wen' : folder_map[input_fwks['Wen']],
  'Wmn' : folder_map[input_fwks['Wmn']],
  'Zee' : folder_map[input_fwks['Zee']],
  'Zmm' : folder_map[input_fwks['Zmm']],
  'Znn' : folder_map[input_fwks['Znn']] 
}

if not args.doVV:
  bkg_procs = {
    'Wen' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVHF','VVLF','Zj0b','Zj1b','Zj2b'],
    'Wmn' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVHF','VVLF','Zj0b','Zj1b','Zj2b'],
    'Zmm' : ['s_Top','TT','VVLF','VVHF','Zj0b','Zj1b','Zj2b'],
    'Zee' : ['s_Top','TT','VVLF','VVHF','Zj0b','Zj1b','Zj2b'],
    'Znn' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVHF','VVLF','Zj0b','Zj1b','Zj2b','QCD']
    #'Znn' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVHF','VVLF','Zj0b','Zj1b','Zj2b']
  }
else:
  bkg_procs = {
    'Wen' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVLF','Zj0b','Zj1b','Zj2b','WH_hbb','ZH_hbb'],
    'Wmn' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVLF','Zj0b','Zj1b','Zj2b','WH_hbb','ZH_hbb'],
    'Zmm' : ['s_Top','TT','VVLF','Zj0b','Zj1b','Zj2b','ZH_hbb','ggZH_hbb'],
    'Zee' : ['s_Top','TT','VVLF','Zj0b','Zj1b','Zj2b','ZH_hbb','ggZH_hbb'],
    'Znn' : ['s_Top','TT','Wj0b','Wj1b','Wj2b','VVLF','Zj0b','Zj1b','Zj2b','QCD','WH_hbb','ZH_hbb','ggZH_hbb']
  }

if not args.doVV:
  sig_procs = {
    'Wen' : ['WH_hbb','ZH_hbb'],
    'Wmn' : ['WH_hbb','ZH_hbb'],
    'Zmm' : ['ZH_hbb','ggZH_hbb'],
    'Zee' : ['ZH_hbb','ggZH_hbb'],
    'Znn' : ['ZH_hbb','ggZH_hbb','WH_hbb']
  }

  sig_procs_ren = {
    'Wen' : ['WH_lep','ZH_hbb'],
    'Wmn' : ['WH_lep','ZH_hbb'],
    'Zmm' : ['ZH_hbb','ggZH_hbb'],
    'Zee' : ['ZH_hbb','ggZH_hbb'],
    'Znn' : ['ZH_hbb','ggZH_hbb','WH_lep']
  }
else:
  sig_procs = {
    'Wen' : ['VVHF'],
    'Wmn' : ['VVHF'],
    'Zmm' : ['VVHF'],
    'Zee' : ['VVHF'],
    'Znn' : ['VVHF']
  }

if args.mjj:
    # don't fit QCD anywhere for Mjj!
    bkg_procs['Znn'].remove('QCD')

  #sig_procs_ren = {
  #  'Wen' : ['WH_lep','ZH_hbb'],
  #  'Wmn' : ['WH_lep','ZH_hbb'],
  #  'Zmm' : ['ZH_hbb','ggZH_hbb'],
  #  'Zee' : ['ZH_hbb','ggZH_hbb'],
  #  'Znn' : ['ZH_hbb','ggZH_hbb','WH_lep']
 # }

if not args.mjj:
    cats = {
      'Zee' : [
        (1, 'SR_high_Zee'), (2, 'SR_low_Zee'), (3, 'Zlf_high_Zee'), (4,'Zlf_low_Zee'),
        (5, 'Zhf_high_Zee'), (6, 'Zhf_low_Zee'), (7,'ttbar_high_Zee'), (8,'ttbar_low_Zee')
      ],
      'Zmm' : [
        (1, 'SR_high_Zuu'), (2, 'SR_low_Zuu'), (3, 'Zlf_high_Zuu'), (4,'Zlf_low_Zuu'),
        (5, 'Zhf_high_Zuu'), (6, 'Zhf_low_Zuu'), (7,'ttbar_high_Zuu'), (8,'ttbar_low_Zuu')
      ],
      'Znn' : [
        (1, 'Znn_13TeV_Signal'), (3, 'Znn_13TeV_Zlight'), (5, 'Znn_13TeV_Zbb'), (7,'Znn_13TeV_TT')
      ],
     'Wen' : [
        (1, 'WenHighPt'), (3,'wlfWen'), (5,'whfWenHigh'), (6,'whfWenLow'), (7,'ttWen')
      ],
     'Wmn' : [
        (1, 'WmnHighPt'), (3,'wlfWmn'), (5,'whfWmnHigh'), (6,'whfWmnLow'), (7,'ttWmn')
      ]

    }
    
    if args.Zmm_fwk == 'Xbb':
        cats['Zmm'] = [(1, 'Zuu_BDT_highpt'), (2, 'Zuu_BDT_lowpt'), (3, 'Zuu_CRZlight_highpt'), (4,'Zuu_CRZlight_lowpt'),
                       (5, 'Zuu_CRZb_highpt'), (6, 'Zuu_CRZb_lowpt'), (7,'Zuu_CRttbar_highpt'), (8,'Zuu_CRttbar_lowpt')]
        cats['Zee'] = [(1, 'Zee_BDT_highpt'), (2, 'Zee_BDT_lowpt'), (3, 'Zee_CRZlight_highpt'), (4,'Zee_CRZlight_lowpt'),
                       (5, 'Zee_CRZb_highpt'), (6, 'Zee_CRZb_lowpt'), (7,'Zee_CRttbar_highpt'), (8,'Zee_CRttbar_lowpt')]
        cats['Znn'] = [(1, 'Znn_13TeV_Signal'), (3, 'Znn_13TeV_Zlight'), (5, 'Znn_13TeV_Zbb'), (7,'Znn_13TeV_TT')]
    if args.Wen_fwk == 'Xbb':
        cats['Wen'] = [(1, 'Wen_13TeV_Signal'), (3,'Wen_13TeV_Wlight'), (5,'Wen_13TeV_Wbb_highM'), (6,'Wen_13TeV_Wbb_lowM'), (7,'Wen_13TeV_TT')]
    if args.Wmn_fwk == 'Xbb':
        cats['Wmn'] = [(1, 'Wun_13TeV_Signal'), (3,'Wun_13TeV_Wlight'), (5,'Wun_13TeV_Wbb_highM'), (6,'Wun_13TeV_Wbb_lowM'), (7,'Wun_13TeV_TT')]

    if args.rebinning_scheme == 'v2-wh-hf-dnn' or args.rebinning_scheme.startswith('v2-whznnh-hf-dnn'):
        if args.Wen_fwk == 'Xbb':
            cats['Wen'] = [(1, 'Wen_13TeV_Signal'), (3,'Wen_13TeV_Wlight'), (6,'Wen_13TeV_Wbb'), (7,'Wen_13TeV_TT')]
        else:
            cats['Wen'] = [ (1, 'WenHighPt'), (3,'wlfWen'), (6,'whfWenLow'), (7,'ttWen') ]
        if args.Wmn_fwk == 'Xbb':
            cats['Wmn'] = [(1, 'Wun_13TeV_Signal'), (3,'Wun_13TeV_Wlight'), (6,'Wun_13TeV_Wbb'), (7,'Wun_13TeV_TT')]
        else:
            cats['Wmn'] = [ (1, 'WmnHighPt'), (3,'wlfWmn'), (6,'whfWmnLow'), (7,'ttWmn') ]

    if args.multi and args.Znn_fwk == 'Xbb':
        cats['Znn'] = [(1, 'Znn_13TeV_Signal'), (5, 'Znn_13TeV_Background')]

    if args.multi and args.Wen_fwk == 'Xbb':
        cats['Wen'] = [(1, 'Wen_13Tev_Multi_Signal'), (5, 'Wen_13Tev_Multi_Background')]

    if args.multi and args.Wmn_fwk == 'Xbb':
        cats['Wmn'] = [(1, 'Wun_13Tev_Multi_Signal'), (5, 'Wun_13Tev_Multi_Background')]

    if args.multi and args.Zee_fwk == 'Xbb':
        cats['Zee'] = [(1, 'Zee_highpt_Signal'), (2, 'Zee_lowpt_Signal'), (3, 'Zee_highpt_Backgrounds'), (4, 'Zee_lowpt_Backgrounds')]
    if args.multi and args.Zmm_fwk == 'Xbb':
        cats['Zmm'] = [(1, 'Zuu_highpt_Signal'), (2, 'Zuu_lowpt_Signal'), (3, 'Zuu_highpt_Backgrounds'), (4, 'Zuu_lowpt_Backgrounds')]

else:
    cats = {
      'Zee' : [
        (1, 'SRHIZee_mjj0'), (2, 'SRLOZee_mjj0'), (3, 'SRHIZee_mjj1'), (4, 'SRLOZee_mjj1'), 
        (5, 'SRHIZee_mjj2'), (6, 'SRLOZee_mjj2'), (7, 'SRHIZee_mjj3'), (8, 'SRLOZee_mjj3'), 
        (9, 'Zlf_high_Zee'), (10,'Zlf_low_Zee'), (11,'ttbar_high_Zee'),(12,'ttbar_low_Zee'),
        (13, 'Zhf_high_Zee'), (14, 'Zhf_low_Zee') 
      ],
      'Zmm' : [
        (1, 'SRHIZmm_mjj0'), (2, 'SRLOZmm_mjj0'), (3, 'SRHIZmm_mjj1'), (4, 'SRLOZmm_mjj1'), 
        (5, 'SRHIZmm_mjj2'), (6, 'SRLOZmm_mjj2'), (7, 'SRHIZmm_mjj3'), (8, 'SRLOZmm_mjj3'), 
        (9, 'Zlf_high_Zuu'), (10,'Zlf_low_Zuu'), (11,'ttbar_high_Zuu'),(12,'ttbar_low_Zuu'),
        (13, 'Zhf_high_Zuu'), (14, 'Zhf_low_Zuu') 
      ],
      'Znn' : [
        (1, 'Znn_13TeV_Signal_mjj0'), (2, 'Znn_13TeV_Signal_mjj1'), 
        (3, 'Znn_13TeV_Signal_mjj2'), (4, 'Znn_13TeV_Signal_mjj3'), 
        (5, 'Znn_13TeV_Zlight'), (6, 'Znn_13TeV_Zbb'), (7,'Znn_13TeV_TT')
      ],
     'Wen' : [
        (1, 'WenHighPt_mjj0'), (2, 'WenHighPt_mjj1'), (3, 'WenHighPt_mjj2'),(4, 'WenHighPt_mjj3'),  
        (5,'wlfWen'), (6,'whfWenLow'), (7,'ttWen')
      ],
     'Wmn' : [
        (1, 'WmnHighPt_mjj0'), (2, 'WmnHighPt_mjj1'), (3, 'WmnHighPt_mjj2'),(4, 'WmnHighPt_mjj3'),  
        (5,'wlfWmn'), (6,'whfWmnLow'), (7,'ttWmn')
      ]
    }

    if args.Zmm_fwk == 'Xbb':
        #cats['Zmm'] = [(1, 'Zuu_mjj_BDT0_highpt'), (2, 'Zuu_mjj_BDT0_lowpt'), (3, 'Zuu_mjj_BDT1_highpt'), (4, 'Zuu_mjj_BDT1_lowpt'), (9, 'Zuu_CRZlight_highpt'), (10,'Zuu_CRZlight_lowpt'), (11, 'Zuu_CRZb_highpt'), (12, 'Zuu_CRZb_lowpt'), (13,'Zuu_CRttbar_highpt'), (14,'Zuu_CRttbar_lowpt')]
        cats['Zmm'] = [(1, 'Zuu_mjj_BDT0_highpt'), (2, 'Zuu_mjj_BDT0_lowpt'), (3, 'Zuu_mjj_BDT1_highpt'), (4, 'Zuu_mjj_BDT1_lowpt'), (5, 'Zuu_mjj_BDT2_highpt'), (6, 'Zuu_mjj_BDT2_lowpt'),  (7, 'Zuu_mjj_BDT3_highpt'), (8, 'Zuu_mjj_BDT3_lowpt'), (9, 'Zuu_CRZlight_highpt'), (10,'Zuu_CRZlight_lowpt'), (11, 'Zuu_CRZb_highpt'), (12, 'Zuu_CRZb_lowpt'), (13,'Zuu_CRttbar_highpt'), (14,'Zuu_CRttbar_lowpt')]

    if args.Zee_fwk == 'Xbb':
        #cats['Zee'] = [(1, 'Zee_mjj_BDT0_highpt'), (2, 'Zee_mjj_BDT0_lowpt'), (3, 'Zee_mjj_BDT1_highpt'), (4, 'Zee_mjj_BDT1_lowpt'), (9, 'Zee_CRZlight_highpt'), (10,'Zee_CRZlight_lowpt'), (11, 'Zee_CRZb_highpt'), (12, 'Zee_CRZb_lowpt'), (13,'Zee_CRttbar_highpt'), (14,'Zee_CRttbar_lowpt')]
        cats['Zee'] = [(1, 'Zee_mjj_BDT0_highpt'), (2, 'Zee_mjj_BDT0_lowpt'), (3, 'Zee_mjj_BDT1_highpt'), (4, 'Zee_mjj_BDT1_lowpt'), (5, 'Zee_mjj_BDT2_highpt'), (6, 'Zee_mjj_BDT2_lowpt'),  (7, 'Zee_mjj_BDT3_highpt'), (8, 'Zee_mjj_BDT3_lowpt'), (9, 'Zee_CRZlight_highpt'), (10,'Zee_CRZlight_lowpt'), (11, 'Zee_CRZb_highpt'), (12, 'Zee_CRZb_lowpt'), (13,'Zee_CRttbar_highpt'), (14,'Zee_CRttbar_lowpt')] 

#cb.cp().channel(['Zee','Zmm']).RenameSystematic(cb,'VVHFCMS_vhbb_LHE_weights_scale_muR_VVHFUp','VVHFCMS_LHE_weights_scale_muR_VVHFUp')

for chn in chns:
  cb.AddObservations( ['*'], ['vhbb'], ['13TeV'], [chn], cats[chn])
  cb.AddProcesses( ['*'], ['vhbb'], ['13TeV'], [chn], bkg_procs[chn], cats[chn], False)
  cb.AddProcesses( ['*'], ['vhbb'], ['13TeV'], [chn], sig_procs[chn], cats[chn], True)

#cb.FilterProcs(lambda x: x.bin_id()==7 and x.channel()=='Znn' and x.process()=='Zj1b')
cb.FilterProcs(lambda x: x.bin_id()==1 and x.channel()=='Znn' and x.process()=='QCD')
if args.multi:
    cb.FilterProcs(lambda x: x.bin_id()==5 and x.channel()=='Znn' and x.process()=='QCD')

systs.AddCommonSystematics(cb)
if year=='2016':
  systs.AddSystematics2016(cb)
if year=='2017':
  systs.AddSystematics2017(cb)

if args.multi and args.decorrelateWlnZnnWjets:
  cb.cp().channel(['Znn']).process(['Wj0b']).AddSyst(cb, 'SF_Wj0b_Znn_2017', 'rateParam', ch.SystMap('bin_id')(range(1,8),1.0))
  cb.cp().channel(['Znn']).process(['Wj1b']).AddSyst(cb, 'SF_Wj1b_Znn_2017', 'rateParam', ch.SystMap('bin_id')(range(1,8),1.0))
  cb.cp().channel(['Znn']).process(['Wj2b']).AddSyst(cb, 'SF_Wj2b_Znn_2017', 'rateParam', ch.SystMap('bin_id')(range(1,8),1.0))
  #cb.GetParameter('SF_Wj0b_Znn_2017').set_range(-1.0,5.0)
  #cb.GetParameter('SF_Wj1b_Znn_2017').set_range(-1.0,5.0)
  #cb.GetParameter('SF_Wj2b_Znn_2017').set_range(-1.0,5.0)

if args.bbb_mode==0:
  cb.AddDatacardLineAtEnd("* autoMCStats -1")
elif args.bbb_mode==1:
  cb.AddDatacardLineAtEnd("* autoMCStats 0")



for chn in chns:
  file = shapes + input_folders[chn] + "/vhbb_"+chn+"-"+year+".root"
  if input_fwks[chn] == 'Xbb':
    cb.cp().channel([chn]).backgrounds().ExtractShapes(
      file, '$BIN/$PROCESS', '$BIN/$PROCESS$SYSTEMATIC')
    cb.cp().channel([chn]).signals().ExtractShapes(
      file, '$BIN/$PROCESS', '$BIN/$PROCESS$SYSTEMATIC')
      #file, '$BIN/$PROCESS$MASS', '$BIN/$PROCESS$MASS_$SYSTEMATIC')
  elif input_fwks[chn] == 'AT':
    cb.cp().channel([chn]).backgrounds().ExtractShapes(
      file, 'BDT_$BIN_$PROCESS', 'BDT_$BIN_$PROCESS_$SYSTEMATIC')
    cb.cp().channel([chn]).signals().ExtractShapes(
      file, 'BDT_$BIN_$PROCESS', 'BDT_$BIN_$PROCESS_$SYSTEMATIC')

# play with rebinning (and/or cutting) of the shapes
if args.rebinning_scheme == 'v1': # Zll only: 1bin in TT/LF, 2bins in HF
    binning=np.linspace(0.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for channels',['Zee','Zmm']
    cb.cp().channel(['Zee','Zmm']).bin_id([3,4,7,8]).VariableRebin(binning)
    binning=np.linspace(0.0,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for channels',['Zee','Zmm']
    cb.cp().channel(['Zee','Zmm']).bin_id([5,6]).VariableRebin(binning)

elif args.rebinning_scheme == 'v2': # all channels: 1bin in TT/LF, 2bins in HF
    binning=np.linspace(0.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([3,4,7,8]).VariableRebin(binning)
    binning=np.linspace(0.0,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([5,6]).VariableRebin(binning)
    
elif args.rebinning_scheme == 'v2-wh-hf-dnn': # all channels: 1bin in TT/LF, 2bins in HF + DNN for WH HF
    binning=np.linspace(0.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([3,4,7,8]).VariableRebin(binning)
    binning=np.linspace(0.0,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for all Zll and Znn channels'
    cb.cp().channel(['Zee','Zmm','Znn']).bin_id([5,6]).VariableRebin(binning)
    binning=np.linspace(0.0,5.0,num=6)
    print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    cb.cp().channel(['Wmn','Wen']).bin_id([5,6]).VariableRebin(binning) 
   
elif args.rebinning_scheme in ['v2-whznnh-hf-dnn','v2-whznnh-hf-dnn-droplowpt']: # all channels: 1bin in TT/LF, 2bins in HF + DNN for WH and ZH HF
    binning=np.linspace(0.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([3,4,7,8]).VariableRebin(binning)
    binning=np.linspace(0.0,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for all Zll and Znn channels'
    cb.cp().channel(['Zee','Zmm']).bin_id([5,6]).VariableRebin(binning)
    binning=np.linspace(0.0,5.0,num=6)
    print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    if args.multi:
        cb.cp().channel(['Wmn','Wen']).bin_id([5,6]).VariableRebin(binning) 
    else:
        cb.cp().channel(['Wmn','Wen','Znn']).bin_id([5,6]).VariableRebin(binning) 
   
elif args.rebinning_scheme == 'v2-whznnh-hf-dnn-10': # all channels: 1bin in TT/LF, 2bins in HF
    binning=np.linspace(0.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().channel(['Zee','Zmm','Wmn','Wen']).bin_id([3,4,7,8]).VariableRebin(binning)
    binning=np.linspace(0.0,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for all Zll and Znn channels'
    cb.cp().channel(['Zee','Zmm']).bin_id([5,6]).VariableRebin(binning)
    #binning=np.linspace(0.0,5.0,num=11)
    #print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    #cb.cp().channel(['Wmn','Wen','Znn']).bin_id([5,6]).VariableRebin(binning) 
   
elif args.rebinning_scheme == 'v3': # all channels: 1bin in TT/LF, no rebin in HF
    binning=np.linspace(0.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([3,4,7,8]).VariableRebin(binning)
    
elif args.rebinning_scheme == 'v4': # all channels: 1bin in TT/LF, no rebin in HF
    binning=np.linspace(0.0,1.0,num=3)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([3,4,7,8]).VariableRebin(binning)
    binning=np.linspace(0.0,1.0,num=5)
    print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    cb.cp().bin_id([5,6]).VariableRebin(binning)
    
elif args.rebinning_scheme == 'sr_mva_cut_2bins': # HIG-16-044 style
    binning=np.linspace(0.2,1.0,num=13)
    print 'binning in SR for fitting variable:',binning
    cb.cp().bin_id([1,2]).VariableRebin(binning)

elif args.rebinning_scheme == 'v2-whznnh-hf-dnn-massAnalysis': # all channels: 1bin in TT/LF, 2bins in HF
    binning=np.linspace(0.,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().channel(['Zee','Zmm']).bin_id([9,10,11,12]).VariableRebin(binning)
    cb.cp().channel(['Wen','Wmn']).bin_id([5,7]).VariableRebin(binning)
    cb.cp().channel(['Znn']).bin_id([5,7]).VariableRebin(binning)
    binning=np.linspace(0.,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for all Zll and Znn channels'
    cb.cp().channel(['Zee','Zmm']).bin_id([13,14]).VariableRebin(binning)
    binning=np.linspace(0.0,5.0,num=6)
    print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    cb.cp().channel(['Wen','Wmn']).bin_id([6]).VariableRebin(binning)
    cb.cp().channel(['Znn']).bin_id([6]).VariableRebin(binning)
    print 'binning in SR for all channels'
    binning=np.linspace(60,150,num=5)
    binning=np.append(binning,[160.])
    cb.cp().channel(['Zee','Zmm']).bin_id([1,2,3,4,5,6,7,8]).VariableRebin(binning)
    cb.cp().channel(['Wen','Wmn','Znn']).bin_id([1,2,3,4]).VariableRebin(binning)
elif args.rebinning_scheme == 'v2-whznnh-hf-dnn-massAnalysis-2016': # all channels: 1bin in TT/LF, 2bins in HF
    binning=np.linspace(-1.0,1.0,num=2)
    print 'binning in CR for LF,TT fitting variable:',binning,'for all the channels'
    cb.cp().channel(['Zee','Zmm']).bin_id([9,10,11,12]).VariableRebin(binning)
    cb.cp().channel(['Wen','Wmn']).bin_id([5,7]).VariableRebin(binning)
    cb.cp().channel(['Znn']).bin_id([5,7]).VariableRebin(binning)
    binning=np.linspace(0.,1.0,num=3)
    print 'binning in CR for HF fitting variable:',binning,'for all Zll and Znn channels'
    cb.cp().channel(['Zee','Zmm']).bin_id([13,14]).VariableRebin(binning)
    binning=np.linspace(0.0,5.0,num=6)
    print 'binning in CR for HF fitting variable:',binning,'for all the channels'
    cb.cp().channel(['Wen','Wmn']).bin_id([6]).VariableRebin(binning)
    cb.cp().channel(['Znn']).bin_id([6]).VariableRebin(binning)
    print 'binning in SR for all channels'
    binning=np.linspace(60,150,num=5)
    binning=np.append(binning,[160.])
    cb.cp().channel(['Zee','Zmm']).bin_id([1,2,3,4,5,6,7,8]).VariableRebin(binning)
    cb.cp().channel(['Wen','Wmn','Znn']).bin_id([1,2,3,4]).VariableRebin(binning)

cb.FilterProcs(lambda x: drop_zero_procs(cb,x))
cb.FilterSysts(lambda x: drop_zero_systs(x))
#Drop QCD in Z+HF CR
cb.FilterProcs(lambda x: drop_znnqcd(cb,x))

if year=='2016':
    cb.cp().syst_name(["CMS_res_j_13TeV_2016"]).ForEachProc(lambda x:symmetrise_syst(cb,x,'CMS_res_j_13TeV_2016'))
if year=='2017':
    cb.cp().syst_name(["CMS_res_j_13TeV"]).ForEachProc(lambda x:symmetrise_syst(cb,x,'CMS_res_j_13TeV'))

if year=='2017':
    cb.cp().ForEachSyst(lambda x: remove_norm_effect(x) if x.name()=='CMS_vhbb_puWeight' else None)


if args.doVV:
    cb.FilterSysts(lambda x: x.name() in "CMS_vhbb_VV")

if year=='2017':
    #cb.cp().process(['Wj0b']).ForEachProc(lambda x: increase_bin_errors(x))
    cb.cp().channel(['Wen','Wmn']).process(['VVHF','VVLF']).ForEachProc(lambda x: increase_bin_errors(x))


if args.decorrelateWlnZnnWjets:
    cb.cp().channel(['Znn']).RenameSystematic(cb,'SF_Wj0b_Wln_2017','SF_Wj0b_Znn_2017')
    cb.cp().channel(['Znn']).RenameSystematic(cb,'SF_Wj1b_Wln_2017','SF_Wj1b_Znn_2017')
    cb.cp().channel(['Znn']).RenameSystematic(cb,'SF_Wj2b_Wln_2017','SF_Wj2b_Znn_2017')

cb.cp().channel(['Wen','Wmn','Znn']).process(['Wj0b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_W0b_vhbb_vjetnlodetajjrw_13TeV')
cb.cp().channel(['Wen','Wmn','Znn']).process(['Wj1b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_W1b_vhbb_vjetnlodetajjrw_13TeV')
cb.cp().channel(['Wen','Wmn','Znn']).process(['Wj2b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_W2b_vhbb_vjetnlodetajjrw_13TeV')
#cb.cp().channel(['Zee','Zmm','Znn','Wen','Wmn']).process(['Zj0b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z0b_vhbb_vjetnlodetajjrw_13TeV')
#cb.cp().channel(['Zee','Zmm','Znn','Wen','Wmn']).process(['Zj1b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z1b_vhbb_vjetnlodetajjrw_13TeV')
#cb.cp().channel(['Zee','Zmm','Znn','Wen','Wmn']).process(['Zj2b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z2b_vhbb_vjetnlodetajjrw_13TeV')
if not args.decorrelateZjNLO:
    cb.cp().channel(['Zee','Zmm','Znn']).process(['Zj0b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z0b_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Zee','Zmm','Znn']).process(['Zj1b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z1b_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Zee','Zmm','Znn']).process(['Zj2b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z2b_vhbb_vjetnlodetajjrw_13TeV')
else:
    print "\x1b[31mdecorrelate Zj LO to NLO weight between 0 and 2 lepton channel\x1b[0m"
    cb.cp().channel(['Zee','Zmm']).process(['Zj0b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z0b_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Zee','Zmm']).process(['Zj1b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z1b_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Zee','Zmm']).process(['Zj2b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z2b_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Znn']).process(['Zj0b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z0bNuNu_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Znn']).process(['Zj1b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z1bNuNu_vhbb_vjetnlodetajjrw_13TeV')
    cb.cp().channel(['Znn']).process(['Zj2b']).RenameSystematic(cb,'CMS_vhbb_vjetnlodetajjrw_13TeV','CMS_Z2bNuNu_vhbb_vjetnlodetajjrw_13TeV')

cb.cp().signals().RenameSystematic(cb,'CMS_res_j_reg_13TeV','CMS_signal_resolution_13TeV')
cb.cp().channel(['Wen','Wmn','Znn']).RenameSystematic(cb,'CMS_res_j_reg_13TeV','CMS_NoKinFit_res_j_reg_13TeV')
cb.cp().channel(['Zee','Zmm']).RenameSystematic(cb,'CMS_res_j_reg_13TeV','CMS_KinFit_res_j_reg_13TeV')


#if year=='2017':
#    cb.cp().ForEachSyst(lambda x: remove_norm_effect(x) if 'vhbb_vjetnlodetajjrw_13TeV' in x.name() else None)

#if year=='2017' and all([v=='Xbb' for k,v in input_fwks.items()]):
#    cb.cp().ForEachSyst(lambda x: remove_norm_effect(x) if 'NoKinFit_res_j_reg' in x.name() else None)
#    print '\x1b[34mXBB: remove normalization effect for NoKinFit_res_j_reg!\x1b[0m'

cb.SetGroup('signal_theory',['pdf_Higgs.*','BR_hbb','QCDscale_ggZH','QCDscale_VH','CMS_vhbb_boost.*','.*LHE_weights.*ZH.*','.*LHE_weights.*WH.*','.*LHE_weights.*ggZH.*'])
cb.SetGroup('bkg_theory',['pdf_qqbar','pdf_gg','CMS_vhbb_VV','CMS_vhbb_ST','.*LHE_weights.*TT.*','.*LHE_weights.*VV.*','.*LHE_weights.*Zj0b.*','LHE_weights.*Zj1b.*','LHE_weights.*Zj2b.*','LHE_weights.*Wj0b.*','LHE_weights.*Wj1b.*','LHE_weights.*Wj2b.*','LHE_weights.*s_Top.*','LHE_weights.*QCD.*'])
cb.SetGroup('sim_modelling',['CMS_vhbb_ptwweights.*','CMS_vhbb_vjetnlodetajjrw.*'])
cb.SetGroup('jes',['CMS_scale_j.*'])
cb.SetGroup('jer',['CMS_res_j.*','CMS_signal_resolution.*'])
cb.SetGroup('btag',['.*bTagWeight.*JES.*','.*bTagWeight.*HFStats.*','.*bTagWeight.*LF_.*','.*bTagWeight.*cErr.*'])
cb.SetGroup('mistag',['.*bTagWeight.*LFStats.*','.*bTagWeight.*HF_.*'])
cb.SetGroup('lumi',['lumi_13TeV','.*puWeight.*'])
cb.SetGroup('lep_eff',['.*eff_e.*','.*eff_m.*'])
cb.SetGroup('met',['.*MET.*'])
cb.SetGroup('autoMCStats',['prop_bin.*'])



#To rename processes:
#cb.cp().ForEachObj(lambda x: x.set_process("WH_lep") if x.process()=='WH_hbb' else None)


rebin = ch.AutoRebin().SetBinThreshold(0.).SetBinUncertFraction(1.0).SetRebinMode(1).SetPerformRebin(True).SetVerbosity(1)

#binning=np.linspace(0.2,1.0,num=13)
#print binning


if args.auto_rebin:
  rebin.Rebin(cb, cb)

if args.zero_out_low:
  range_to_drop = {'Wen':[[1,0,0.5]],'Wmn':[[1,0,0.5]],'Znn':[[1,0,0.5]],'Zee':[[1,0,0.5],[2,0,0.5]],'Zmm':[[1,0,0.5],[2,0,0.5]]} #First number is bin_id, second number lower bound of range to drop, third number upper bound of range to drop
  for chn in chns:
    for i in range(len(range_to_drop[chn])):
      cb.cp().channel([chn]).bin_id([range_to_drop[chn][i][0]]).ZeroBins(range_to_drop[chn][i][1],range_to_drop[chn][i][2])

ch.SetStandardBinNames(cb)

writer=ch.CardWriter("output/" + args.output_folder + year + "/$TAG/$BIN"+year+".txt",
                      "output/" + args.output_folder + year +"/$TAG/vhbb_input_$BIN"+year+".root")
writer.SetWildcardMasses([])
writer.SetVerbosity(0);
                
#Combined:
writer.WriteCards("cmb",cb);
writer.WriteCards("cmb_CRonly",cb.cp().bin_id([3,4,5,6,7,8]));

#Per channel:
for chn in chns:
  writer.WriteCards(chn,cb.cp().channel([chn]))

if 'Znn' in chns:
  #writer.WriteCards("Znn",cb.cp().FilterAll(lambda x: not (x.channel()=='Znn' or ( (x.channel() in ['Wmn','Wen']) and x.bin_id() in [3,4,5,6,7,8]))))
  if not args.mjj:
      writer.WriteCards("Znn",cb.cp().channel(['Znn']))
      
      if not args.multi:
          writer.WriteCards("Znn",cb.cp().bin_id([3,4,5,6,7,8]).channel(['Wmn','Wen']))
      else:
          writer.WriteCards("Znn",cb.cp().bin_id([5]).channel(['Wmn','Wen']))
      writer.WriteCards("Znn_CRonly",cb.cp().bin_id([3,4,5,6,7,8]).channel(['Znn','Wmn','Wen']))
  else:
      writer.WriteCards("Znn",cb.cp().channel(['Znn']))
      writer.WriteCards("Znn",cb.cp().bin_id([5,6,7,8]).channel(['Wmn','Wen']))
      writer.WriteCards("Znn_CRonly",cb.cp().bin_id([3,4,5,6,7,8]).channel(['Znn']))
      writer.WriteCards("Znn_CRonly",cb.cp().bin_id([5,6,7,8]).channel(['Wmn','Wen']))

#Zll and Wln:
if 'Wen' in chns and 'Wmn' in chns:
  writer.WriteCards("Wln",cb.cp().channel(['Wen','Wmn']))
  writer.WriteCards("Wln_CRonly",cb.cp().bin_id([3,4,5,6,7,8]).channel(['Wen','Wmn']))

if 'Zee' in chns and 'Zmm' in chns:
  writer.WriteCards("Zll",cb.cp().channel(['Zee','Zmm']))
  writer.WriteCards("Zll_CRonly",cb.cp().bin_id([3,4,5,6,7,8]).channel(['Zee','Zmm']))

print("end:", chns)
