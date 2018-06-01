# VHbb instructions

This file collects instructions for producing the statistical results for the VHbb analysis. More detailed information on CombineHarvester can be found in the documentation at

http://cms-analysis.github.io/CombineHarvester/

## Setting up the area

    export SCRAM_ARCH=slc6_amd64_gcc530
    scram project CMSSW CMSSW_8_1_0
    cd CMSSW_8_1_0/src
    cmsenv
    git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
    cd HiggsAnalysis/CombinedLimit
    git checkout v7.0.8
    cd ../..
    git clone https://github.com/cms-analysis/CombineHarvester.git CombineHarvester
    cd CombineHarvester
    git checkout -b HIG16044-dev origin/HIG16044-dev
    cd ..
    scram b

## Getting the input root files

Before checking out the shape files, move to the relevant subdirectory:

`cd CombineHarvester/VH2017`

The input shape files are stored in an external repository. On a machine with a kerberos token for CERN access (e.g. lxplus) the repository can be checked out as:

`git clone https://:@gitlab.cern.ch:8443/cms-vhbb/VH2017.git shapes`

A password is not needed for this. Otherwise with normal https access (which does require a username and password) the repository can be checked out as:

`git clone https://gitlab.cern.ch/cms-vhbb/VH2017.git shapes`

Access to this repository is linked to the higgs-vlephbb e-group. 

## Setting up datacards

./scripts/VHbb2017.py [options]

This creates .txt datacards in the 'output' directory, both combined and per channel (Zee,Zmm,Wen,Wmn,Znn,Wln,Zll), all in separate subdirectories.
At the moment the options are
- `--channel`: set to 'all' by default, can specify individual channels to run here (e.g. `--channel=Zee,Zmm`)
- `--output_folder`: subdirectory of 'output' where the cards are written. Set to 'vhbb2017' by default.
- `--bbb_mode`: toggle to set the bin-by-bin inclusion options. mode 0: do not add bin-by-bins, 1 (default):use autoMCStat mode 
- `--auto_rebin`: switches on automated rebinning of the input histograms. Off by default.
- `--zero_out_low`: sets the bin contents in some of the SR bins to 0 (for the purpose of making yield tables). Off by default.
- `--year`: set to '2017' by default. This governs which filenames to read out of (with -2017 or -2016 postfix!) and appends the year label to the output folder

## Setting up workspaces
**Note: from this point on make sure to have called `ulimit -s unlimited` in your shell since logging in. Otherwise any of these manipulations might lead to a seg fault**

To create workspaces for every combination of regions the cards have been written out for in the previous step:

`combineTool.py -M T2W -o "ws.root" -i output/<output_folder>/*`

Or, for example, to just create a workspace for the Zee channel:

`combineTool.py -M T2W -o "ws.root" -i output/<output_folder>/Zee/`

**NOTE:** only use `*` for subdirectories. If you used e.g. `-i output/<output_folder>/Zee/*`, text2workspace would be called successively on every file in the Zee folder, including the
just-created workspace which leads to problems. 

## Fits
### Signal strength (without uncertainty):
Pre-fit:  
`combineTool.py -M MultiDimFit -t -1 -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0 --expectSignal X`
Here X can be 0 or 1 -> result of the fit will be 0 or 1 too.

Post-fit:  
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0`

### Signal strength (with reasonably accurate uncertainty)
Pre-fit:  
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there -t -1 --cminDefaultMinimizerStrategy 0 --algo singles`

Post-fit:  
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0 --algo singles`

### Significance:
Pre-fit expected[*]: `combineTool.py -M Significance --significance -d output/<output_folder>/cmb/ws.root --there -t -1 --expectSignal 1`\
Post-fit expected: `combineTool.py -M Significance --significance -d output/<output_folder>/cmb/ws.root --there -t -1 --expectSignal 1 --toysFrequentist`\
Observed : `combineTool.py -M Significance --significance -d output/<output_folder>/cmb/ws.root --there`\

[*] To calculate the pre-fit expected significance with the control regions unblind we have to do slightly more work.
However, this is the fairer thing to do as the CR fit can have quite a large effect on the background predictions in the SR:

First we need to create a new workspace, set up for channel masking:

`combineTool.py -M T2W -o "ws_masked.root" -i output/<output_folder>/* --channel-masks`

This adds additional parameters to the workspace which we can use to mask certain regions (=remove them from the likelihood).
We will use this to generate a toy in which the nuisance parameters are set to their best-fit values (from effectively a b-only fit to the control regions):

`combineTool.py -M GenerateOnly --setParameters mask_vhbb_Zmm_1_13TeV<year>=1,mask_vhbb_Zmm_2_13TeV<year>=1,mask_vhbb_Zee_1_13TeV<year>=1,mask_vhbb_Zee_2_13TeV<year>=1,mask_vhbb_Wen_1_13TeV<year>=1,mask_vhbb_Wmn_1_13TeV<year>=1,mask_vhbb_Znn_1_13TeV<year>=1 -t -1 --toysFrequentist  --expectSignal 1 --saveToys --there -d output/<output_folder>/cmb/ws_masked.root`

Now continue as with post-fit expected significance:
`combineTool.py -M Significance --significance -d output/<output_folder>/cmb/ws.root --there --toysFrequentist -t -1 --toysFile higgsCombine.Test.GenerateOnly.mH120.123456.root`


## Pre- and post-fit plots
### Post-fit plots
First run the maximum likelihood fit:

`combineTool.py -M FitDiagnostics -m 125 -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0`

create the post-fit shapes with uncertainties from the datacard and the MLFit:\
*Important:* before doing this, check that the covariance matrix is positive definite. If not, the plotted uncertainties will be nonsense.

`PostFitShapesFromWorkspace -d output/<output_folder>/cmb/combined.txt.cmb -w output/<output_folder>/cmb/ws.root -o shapes.root --print --postfit --sampling -f output/<output_folder>/cmb/fitDiagnostics.Test.root:fit_s`

To make pre- and post fit plots of the BDT distributions in the SR:\
`python scripts/makePostFitPlots.py`\
*Note* For now these plots are made blinded in the [0,1] BDT discr. range. This range can be controlled using the options --x_blind_min, --x_blind_max (arguments to postFitPlot.py). The plots
can be fully unblinded by removing the `--blind` option passed in scripts/makePostFitPlots.py.

To make pre- and post fit plots of the CMVA distributions in the CR:\
`python scripts/makePostFitPlotsCR.py`

### CR-only post-fit plots:
`combineTool.py -M T2W -o "ws_masked.root" -i output/<output_folder>/cmb --channel-masks`

Run maximum likelihood fit, masking the SR from the likelihood:
`combineTool.py -M FitDiagnostics -m 125 -d output/<output_folder>/cmb/ws_masked.root --there --cminDefaultMinimizerStrategy 0 --setParameters mask_vhbb_Zmm_1_13TeV<year>=1,mask_vhbb_Zmm_2_13TeV<year>=1,mask_vhbb_Zee_1_13TeV<year>=1,mask_vhbb_Zee_2_13TeV<year>=1,mask_vhbb_Wen_1_13TeV<year>=1,mask_vhbb_Wmn_1_13TeV<year>=1,mask_vhbb_Znn_1_13TeV<year>=1 -n .SRMasked `

create the post-fit shapes with uncertainties from the datacard and the MLFit:
*Important:* before doing this, check that the covariance matrix is positive definite. If not, the plotted uncertainties will be nonsense.

`PostFitShapesFromWorkspace -d output/<output_folder>/cmb/combined.txt.cmb -w output/<output_folder>/cmb/ws.root -o shapes.root --print --postfit --sampling -f output/<output_folder>/cmb/fitDiagnostics.SRMasked.root:fit_s`

To make pre- and post fit plots of the BDT distributions in the SR:
`python scripts/makePostFitPlots<year>.py`

To make pre- and post fit plots of the CMVA distributions in the CR:
`python scripts/makePostFitPlotsCR<year>.py`

Note: pre-fit in this case will be pre all fits, post-fit will be CR-only post-fit.

### Full pre-fit plots only:
`PostFitShapesFromWorkspace -d output/<output_folder>/cmb/combined.txt.cmb -w output/<output_folder>/cmb/ws.root -o shapes.root --print `

from scripts/makePostFitPlots<year>.py and scripts/makePostFitPlotsCR<year>.py remove 'postfit' from the 'MODE' line and make plots as above. 


The underlying plotting scripts is scripts/postFitPlot.py. Cosmetic changes still needed.

## Yield tables
First run the maximum likelihood fit as described above for the post-fit plots.

Set up new cards and workspace for which the contents of the bins we want to ignore are set to 0 (NOTE: this implementation in the datacard production script still to be improved)

`./scripts/VHbb2017.py [options] --zero_out_low`
`combineTool.py -M T2W -o "ws.root" -i output/<output_folder_zeroed_out>/cmb/`

Create the pre- and postfit yield tables (note: by default this is setup for 2017. We can add a 2016 version if needed, or just replace 2017 by 2016 in printYieldTables.py) :
`./scripts/printYieldTables.py --workspace output/<output_folder_zeroed_out>/cmb/ws.root --fit_file output/<output_folder>/cmb/fitDiagnostics.Test.root`

It is *very* important to use fit results for the *full* model, otherwise the uncertainties on the yields will not be correct. <output_folder_zeroed_out> and <output_folder> are therefore explicitly different, unless yield tables are made for the full model too.


## Other plots
### Channel compatibility (post fit)
Make workspace with separate r_ZH/r_WH:

`combineTool.py -M T2W -i output/<output_folder>/cmb/ -o "ws_proc.root" -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO verbose --PO 'map=.*/.*ZH_hbb:r_ZH[1,0,5]' --PO 'map=.*/WH_hbb:r_WH[1,0,5]' `

Make workspace with separate r for 0,1 and 2 lepton channels:
`combineTool.py -M T2W -i output/<output_folder>/cmb/ -o "ws_channel.root" -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO verbose --PO 'map=vhbb_Zee_.*_13TeV/.*H_hbb:r_twolep[1,0,5]' --PO 'map = vhbb_Zmm_.*_13TeV/.*H_hbb:r_twolep[1,0,5]' --PO 'map=vhbb_Znn_.*_13TeV/.*H_hbb:r_zerolep[1,-2,5]' --PO 'map=vhbb_Wen_.*_13TeV/.*H_hbb:r_onelep[1,0,5]' --PO 'map=vhbb_Wmn_.*_13TeV/.*H_hbb:r_onelep[1,0,5]' `

Now we need to run MultiDimFit to get the best-fit value and uncertainty for each separate signal strength, as well as the combined signal strength:

```
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --cminDefaultMinimizerStrategy 0 --algo singles -n .cmb

combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_proc.root --setParameters r_ZH=1,r_WH=1 --redefineSignalPOIs r_ZH -n .ZH --algo singles --cminDefaultMinimizerStrategy 0
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_proc.root --setParameters r_ZH=1,r_WH=1 --redefineSignalPOIs r_WH -n .WH --algo singles --cminDefaultMinimizerStrategy 0

combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_channel.root --setParameters r_zerolep=1,r_onelep=1,r_twolep=1 --redefineSignalPOIs r_zerolep -n .zerolep --algo singles --cminDefaultMinimizerStrategy 0
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_channel.root --setParameters r_zerolep=1,r_onelep=1,r_twolep=1 --redefineSignalPOIs r_onelep -n .onelep --algo singles --cminDefaultMinimizerStrategy 0
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_channel.root --setParameters r_zerolep=1,r_onelep=1,r_twolep=1 --redefineSignalPOIs r_twolep -n .twolep --algo singles --cminDefaultMinimizerStrategy 0
```

Next we want to collect all of the fit results in a single json file:

```
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r -i higgsCombine.cmb.MultiDimFit.mH120.root --algo singles

combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_ZH -i higgsCombine.ZH.MultiDimFit.mH120.root --algo singles
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_WH -i higgsCombine.WH.MultiDimFit.mH120.root --algo singles

combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_zerolep -i higgsCombine.zerolep.MultiDimFit.mH120.root --algo singles
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_onelep -i higgsCombine.onelep.MultiDimFit.mH120.root --algo singles
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_twolep -i higgsCombine.twolep.MultiDimFit.mH120.root --algo singles
```

Now make the plot:

`./scripts/plotCCC.py -i MultiDimFit_cc.json -o cccPlot`

### Channel compatibility (pre fit)
Make workspace with separate r_ZH/r_WH:

`combineTool.py -M T2W -i output/<output_folder>/cmb/ -o "ws_proc.root" -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO verbose --PO 'map=.*/.*ZH_hbb:r_ZH[1,0,5]' --PO 'map=.*/WH_hbb:r_WH[1,0,5]' `

Make workspace with separate r for 0,1 and 2 lepton channels:
`combineTool.py -M T2W -i output/<output_folder>/cmb/ -o "ws_channel.root" -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO verbose --PO 'map=vhbb_Zee_.*_13TeV/.*H_hbb:r_twolep[1,0,5]' --PO 'map = vhbb_Zmm_.*_13TeV/.*H_hbb:r_twolep[1,0,5]' --PO 'map=vhbb_Znn_.*_13TeV/.*H_hbb:r_zerolep[1,-2,5]' --PO 'map=vhbb_Wen_.*_13TeV/.*H_hbb:r_onelep[1,0,5]' --PO 'map=vhbb_Wmn_.*_13TeV/.*H_hbb:r_onelep[1,0,5]' `

Now we need to run MultiDimFit to get the best-fit value and uncertainty for each separate signal strength, as well as the combined signal strength:

```
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --cminDefaultMinimizerStrategy 0 --algo singles -n .cmb --expectSignal 1 -t -1
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_proc.root --setParameters r_ZH=1,r_WH=1 --redefineSignalPOIs r_ZH -n .ZH --algo singles --cminDefaultMinimizerStrategy 0 --expectSignal 1 -t -1
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_proc.root --setParameters r_ZH=1,r_WH=1 --redefineSignalPOIs r_WH -n .WH --algo singles --cminDefaultMinimizerStrategy 0 --expectSignal -t -1

combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_channel.root --setParameters r_zerolep=1,r_onelep=1,r_twolep=1 --redefineSignalPOIs r_zerolep -n .zerolep --algo singles --cminDefaultMinimizerStrategy 0 --expectSignal -t -1
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_channel.root --setParameters r_zerolep=1,r_onelep=1,r_twolep=1 --redefineSignalPOIs r_onelep -n .onelep --algo singles --cminDefaultMinimizerStrategy 0 --expectSignal -t -1
combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws_channel.root --setParameters r_zerolep=1,r_onelep=1,r_twolep=1 --redefineSignalPOIs r_twolep -n .twolep --algo singles --cminDefaultMinimizerStrategy 0 --expectSignal -t -1
```

Next we want to collect all of the fit results in a single json file:

```
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r -i higgsCombine.cmb.MultiDimFit.mH120.root --algo singles

combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_ZH -i higgsCombine.ZH.MultiDimFit.mH120.root --algo singles
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_WH -i higgsCombine.WH.MultiDimFit.mH120.root --algo singles

combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_zerolep -i higgsCombine.zerolep.MultiDimFit.mH120.root --algo singles
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_onelep -i higgsCombine.onelep.MultiDimFit.mH120.root --algo singles
combineTool.py -M PrintFit --json MultiDimFit_ccc.json -P r_twolep -i higgsCombine.twolep.MultiDimFit.mH120.root --algo singles
```

Now make the plot:

`./scripts/plotCCC.py -i MultiDimFit_cc.json -o cccPlot`


### S-over-B ordered plot
**Note: this is currently set up to replicate the HIG-16-044 plot. These instructions may be subject to change.**
**Note: at the moment this is set up for 2017 only. Can adapt as needed**

As inputs we will need the orignal combined datacard, the original combined workspace and the RooFit result obtained when running FitDiagnostics.  
First we need to set up some datacards with the bins re-ordered according to (pre-fit S)/(post-fit B) 

`./scripts/prepareSoverBordered.py -w output/<original_output_folder>/cmb/ws.root -f output/<original_output_folder>/cmb/fitDiagnostics.Test.root -d output/<original_output_folder>/cmb/combined.txt.cmb`

This writes out S/B ordered datacards for the SR categories only to output/vhbb_sbordered/vhbb_2017.txt

Make the workspace for these cards:
`combineTool.py -M T2W -o "ws.root" -i output/vhbb_sbordered/ `

Now we need to run PostFitShapesFromWorkspace on the new S/B ordered workspace we have just made, using the RooFit result we have been using all along:

`PostFitShapesFromWorkspace -d output/vhbb_sbordered/vhbb_2017.txt -w output/vhbb_sbordered/ws.root -o shapes.root --postfit --sampling -f output/<original_output_folder>/cmb/fitDiagnostics.Test.root:fit_s --total-shapes`

To make the plot:
`./scripts/plotSoverBordered.py -f shapes.root --log_y --custom_y_range --ratio`

### S/(S+B) weighted plot
a-la-HIG-16-044 we would need multiple steps. First we have to extract S/(S+B) weights from the existing model:

`./scripts/extractSoverSplusBweights.py -w output/<original_output_folder>/cmb/ws.root -f output/<original_output_folder>/cmb/fitDiagnostics.Test.root -d output/<original_output_folder>/cmb/combined.txt.cmb`

This writes a file store_ssplusbweights.root which contains histograms with the same BDT binning as used in the analysis, containing the relevant weight for each BDT bin that can then be applied by the analysts. In HIG-16-044 style the analysts then provide m_jj shape inputs with the weights applied, which we will use to make the plot. First set up the datacards for the mjj shapes up as before (currently would need to hack the input root file names into VHbb2017.py but we should add an option to do this instead).

Then make the workspace for these cards:  
`combineTool.py -M T2W -o "ws.root" -i output/mjj_cards/cmb/`  

And as before run PostFitShapesFromWorkspace on this new workspace with the fit result we have been using all along as input:

`PostFitShapesFromWorkspace -d output/mjj_cards/cmb/combined.txt.cmb -w output/mjj_cards/cmb/ws.root -o shapes_mjj.root --postfit --sampling -f output/<original_output_folder>/cmb/fitDiagnostics.Test.root:fit_s --total-shapes`  

Plotting script very similar to ./scripts/plotSoverBordered.py still needed.

## Impacts (post-fit)
First set up the datacards as above and create the workspace.

Run the initial fit:
```
combineTool.py -M Impacts -d output/<output_folder>/cmb/ws.root -m 125 --doInitialFit --robustFit 1 --setParameterRanges r=0,3
```

Then run fits for all nuisance parameters:
```
combineTool.py -M Impacts -d output/<output_folder>/cmb/ws.root -m 125 --doFits --robustFit 1 --setParameterRanges r=0,3 --allPars
```

We can submit these fits to a batch system too, by adding:  
(lxbatch): `--job-mode lxbatch --sub-opts '-q <queuename>' --merge 10`  
(condor):  `--job-mode condor --sub-opts --sub-opts='+JobFlavour = "workday"'  
`--merge N` runs N of the fits in the same job, these fits can take a long time so --merge 5 is probably reasonable. 

Collecting the results in a json file: 
`combineTool.py -M Impacts -d output/<output_folder>/cmb/ws.root -m 125 --allPars -o impacts.json`

Plotting:  
`plotImpacts.py -i impacts.json -o impacts_out --transparent`

## Impacts (pre-fit)
First set up the datacards as above and create the workspace.

Run the initial fit:
```
combineTool.py -M Impacts -d output/<output_folder>/cmb/ws.root -m 125 --doInitialFit --robustFit 1 --setParameterRanges r=0,3 -t -1 --expectSignal 1
```

Then run fits for all nuisance parameters:
```
combineTool.py -M Impacts -d output/<output_folder>/cmb/ws.root -m 125 --doFits --robustFit 1 --setParameterRanges r=0,3 --allPars -t -1 --expectSignal 1
```

## Goodness-of-Fit
**NOTE: There is no such thing as a blind goodness-of-fit test, so only run once it is ok to unblind**  
Several GoF tests  are implemented in combine: the saturated model, Kolmogorov-Smirnov and Anderson-Darling tests. More info [here](https://cms-hcomb.gitbooks.io/combine/content/part3/commonstatsmethods.html#goodness-of-fit-tests).\n
Both KS and AD rely on the full model, but compute a GoF measure in each category/region. The saturated model test is defined for individiual categories/regions as well as combinations thereof.\n
Because our background predictions rely heavily on the fitted control regions we need to use post-fit toys to build our test-statistic distribution. The KS and AD tests are then slightly fairer since at least the post-fit toys will be fully post-fit, not just in the category/region we are testing. However, there is nothing technically to stop us from running the saturated model.

### AD/KS
$ALGO = AD,KS:  
```
combineTool.py -M GoodnessOfFit --algorithm $ALGO -m 125 --there -d output/<output_folder>/cmb/ws.root -n ".$ALGO.toys" --fixedSignalStrength=1 -t 500 --toysFrequentist  
combineTool.py -M GoodnessOfFit --algorithm $ALGO -m 125 --there -d output/<output_folder>/cmb/ws.root -n ".$ALGO" --fixedSignalStrength=1
```

these jobs can be submitted to a batch system/condor as specified above. In that case we probably want to split the N toys into fewer toys per job, for example for 5 toys/job we could replace `-t 500` by `-t 5 -s 0:99:1` (which sets the seed of each job to 0,1...99).
When the jobs finish we collect the output:

`combineTool.py -M CollectGoodnessOfFit --input output/<output_folder>/cmb/higgsCombine.$ALGO.GoodnessOfFit.mH125.root output/<output_folder>/cmb/higgsCombine.$ALGO.toys.GoodnessOfFit.mH125.*.root -o cmb_$ALGO.json`

And to make plots for all regions:

`python ../CombineTools/scripts/plotGof.py --statistic $ALGO --mass 125.0 cmb_$ALGO.json --title-right="35.9 fb^{-1} (13 TeV)" --output='-$ALGO'`

### Saturated model
**Note: we do not currently write datacards for individual regions into separate folders. Workspaces for individual regions can be created like as, e.g. for 1-electron channel SR:  
`text2workspace.py -o output/<output_folder>/Wen/ws_wen1.root output/<output_folder>/Wen/vhbb_Wen_1_13TeV.txt`**

Now run everything separately for each region/combination of regions you want to look at:
```
combineTool.py -M GoodnessOfFit --algorithm saturated -m 125 --there -d output/<output_folder>/Zee/ws.root -n ".saturated.toys" --fixedSignalStrength=1 -t 500 --toysFrequentist  
combineTool.py -M GoodnessOfFit --algorithm saturated -m 125 --there -d output/<output_folder>/Zee/ws.root -n ".saturated" --fixedSignalStrength=1

combineTool.py -M CollectGoodnessOfFit --input output/<output_folder>/Zee/higgsCombine.saturated.GoodnessOfFit.mH125.root output/<output_folder>/Zee/higgsCombine.saturated.toys.GoodnessOfFit.mH125.*.root -o Zee_saturated.json

python ../CombineTools/scripts/plotGof.py --statistic saturated --mass 125.0 -o Zee_saturated Zee_saturated.json  --title-right="35.9 fb^{-1} (13 TeV)" --title-left="2-electron (SRs+CRs)"

```

## Freezing groups of nuisances
To determine the effect of addition or removal of a group of nuisances on the signal strength. The nuisance groups are defined in VH2017.py, search for `SetGroup`. Note that a group for the bin-by-bin parameters has to be created during the text2workspace step and cannot be defined at the datacard making stage. You will need to merge this PR: https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit/pull/478 to be able to do this. The group is called autoMCStats.
Given the groups defined in VHbb2017.py at the moment of writing these instructions: allparams, signal_xs, bkg_xs, sim_modelling, jes, jer, b_eff, b_Fake, lumi, rateparams

Removal of group rateparams
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0 --algo singles --freezeNuisanceGroups rateparams `

The result of this needs to be compared with a fit with all nuisances:
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0 --algo singles `

Addition of group rateparams:
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0 --algo singles --freezeNuisanceGroups signal_xs,bkg_xs,sim_modelling,jes,jer,b_eff,b_Fake,lumi,autoMCStats `

Which should be compared with:
`combineTool.py -M MultiDimFit -d output/<output_folder>/cmb/ws.root --there --cminDefaultMinimizerStrategy 0 --algo singles --freezeNuisances all `


## Diagnostic tools
### Printing/visualising correlations:
We can use the FitDiagnostics output to print/plot the correlations (from the fit covariance matrix).\
To print the top N correlations:\
`./scripts/printAllCorrelations -i output/<output_folder>/cmb/fitDiagnostics.Test.root:fit_s -m N`\
To print the N largest correlations of other parameters with a given parameter:\
`./scripts/printCorrelations -i output/<output_folder>/cmb/fitDiagnostics.Test.root:fit_s -p PARAMETER_NAME -m N`\
To save and draw the correlation matrix for a given set of parameters:\
`./scripts/plotCorrelations -i output/<output_folder>/cmb/fitDiagnostics.Test.root:fit_s -p PARAM_NAME_1,PARAM_NAME_2,...,PARAM_NAME_3 -o <output_name_string>`\
This plots the correlation matrix as <output_name_string>.pdf/png and saves the TH2 in <output_name_string>.root 

### FastScan 
FastScan can be used to get an idea of what the likelihood looks like as a function of the parameters. This assumes you have a FitDiagnostics result with an inaccurate convariance matrix that you want to inspect. Assume the file is called fitDiagnostics.root
If we want to run this on an asimov dataset, we need to generate a toy first. Assuming we want to generate an asimov dataset with the CRs unblind:
`combineTool.py -M GenerateOnly --setParameters mask_vhbb_Zmm_1_13TeV<year>=1,mask_vhbb_Zmm_2_13TeV<year>=1,mask_vhbb_Zee_1_13TeV<year>=1,mask_vhbb_Zee_2_13TeV<year>=1,mask_vhbb_Wen_1_13TeV<year>=1,mask_vhbb_Wmn_1_13TeV<year>=1,mask_vhbb_Znn_1_13TeV<year>=1 -t -1 --toysFrequentist  --expectSignal 1 --saveToys --there -d output/<output_folder>/cmb/ws_masked.root`

then:
`combineTool.py -M FastScan -w ws_masked.root:w -d higgsCombineTest.GenerateOnly.mH120.123456.root:toys/toy_asimov -f fitDiagnostics.root:fit_b` (or fit_s, depending on which of the two is giving problems)

The output of this is is a plot of the NLL as a function of each parameter, in addition to the first and second derivative of the NLL as a function of each parameter. Kinks in the likelihood will show up as discontinuities in the derivatives of the NLL. If such a feature is present near the minimum of a particular parameter, that indicates this parameter could be causing the problems in the fit.

## General troubleshooting
### Covariance matrix not accurate
After running FitDiagnostics in the steps to make post-fit plots you should always check that the covariance matrix is accurate, as described above. 
If the quality is `covariance matrix quality: Full matrix, but forced positive-definite` or `covariance matrix quality: Not calculated at all` you should not use this fit result to make post-fit plots because the uncertainties will not make sense. 
Things to try to solve this include:
- playing around with the minimizerTolerance (--cminDefaultMinimizerTolerance) and minimizerStrategy (--cminDefaultMinimizerStrategy). The strategy is set to 0 in the instructions at the moment, which is the least likely to give these problems. The minimizerTolerance is 0.1 by default.
- Checking if any parameters are strongly anti-correlated. 
- Are any parameters close to their boundaries?
- Are there discontinuities in the NLL? Try running FastScan to determine this. If this is the case, try freezing the suspicious parameter and see if this solves the problem. Of course one should then check if there are any problems with the input shapes for that parameter for example and try to fix any possible problems.

###To be updated
To be updated