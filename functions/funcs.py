"""Functions file"""

# import python modules
import os
import pickle
import itertools
import numpy as np
import scipy.special as sp
from scipy.optimize import curve_fit
import scipy.interpolate as scp_interpolate
import matplotlib.pyplot as plt

# Definition
#--auxilliary data
def mrs_aux(band):
    allbands = ['1A','1B','1C','2A','2B','2C','3A','3B','3C','4A','4B','4C']
    allchannels = ['1','2','3','4']
    allsubchannels = ['A','B','C']

    MRS_bands = {'1A':[4.83,5.82],
        '1B':[5.62,6.73],
        '1C':[6.46,7.76],
        '2A':[7.44,8.90],
        '2B':[8.61,10.28],
        '2C':[9.94,11.87],
        '3A':[11.47,13.67],
        '3B':[13.25,15.80],
        '3C':[15.30,18.24],
        '4A':[17.54,21.10],
        '4B':[20.44,24.72],
        '4C':[23.84,28.82]} # microns

    MRS_R = {'1A':[3320.,3710.],
        '1B':[3190.,3750.],
        '1C':[3100.,3610.],
        '2A':[2990.,3110.],
        '2B':[2750.,3170.],
        '2C':[2860.,3300.],
        '3A':[2530.,2880.],
        '3B':[1790.,2640.],
        '3C':[1980.,2790.],
        '4A':[1460.,1930.],
        '4B':[1680.,1770.],
        '4C':[1630.,1330.]} # R = lambda / delta_lambda

    MRS_nslices = {'1':21,'2':17,'3':16,'4':12} # number of slices

    MRS_alphapix = {'1':0.196,'2':0.196,'3':0.245,'4':0.273} # arcseconds

    MRS_slice = {'1':0.176,'2':0.277,'3':0.387,'4':0.645} # arcseconds

    MRS_FOV = {'1':[3.70,3.70],'2':[4.51,4.71],'3':[6.13,6.19],
               '4':[7.74,7.74]} # arcseconds along and across slices

    MRS_FWHM = {'1':2.16*MRS_alphapix['1'],'2':3.30*MRS_alphapix['2'],
                '3':4.04*MRS_alphapix['3'],'4':5.56*MRS_alphapix['4']} # MRS PSF
    return allbands,allchannels,allsubchannels,MRS_bands[band],MRS_R[band],MRS_alphapix[band[0]],MRS_slice[band[0]],MRS_FOV[band[0]],MRS_FWHM[band[0]]

#--import cdps
def get_cdps(band,cdpDir,output='img'):
    """Returns fringe, photom, psf, and resolution CDP fits files """
    subchan_names = {'A':'SHORT','B':'MEDIUM','C':'LONG'}
    if int(band[0]) < 3: detnick = 'MIRIFUSHORT'
    else: detnick = 'MIRIFULONG'


    # fringe flat cdp, compiled by Fred Lahuis
    if int(band[0]) < 3: fringe_subchan_name = '12'
    else: fringe_subchan_name = '34'
    fringe_subchan_name += subchan_names[band[1]]
    fringe_file = os.path.join(cdpDir,\
      'MIRI_FM_%s_%s_FRINGE_06.02.00.fits' % (detnick,fringe_subchan_name))

    # photom cdp, compiled by Bart Vandenbussche
    photom_file = os.path.join(cdpDir,\
      'MIRI_FM_%s_%s_PHOTOM_06.03.02.fits' % (detnick,subchan_names[band[1]]))

    # psf cdp, compiled by Adrian Glauser
    psf_subchan_name = band[0]+subchan_names[band[1]]
    psf_file = os.path.join(cdpDir,\
      'MIRI_FM_%s_%s_PSF_7B.02.00.fits' % (detnick,psf_subchan_name))

    # spatial and spectral resolution cdp, compiled by Alvaro Labiano
    if int(band[0]) < 3: resol_subchan_name = '12'
    else: resol_subchan_name = '34'
    resol_file = os.path.join(cdpDir,\
      'MIRI_FM_%s_%s_RESOL_7B.00.00.fits' % (detnick,resol_subchan_name))

    # photon-conversion efficiency (PCE)
    pce_subchan_name = band[0]+subchan_names[band[1]]
    pce_file = os.path.join(cdpDir,\
      'MIRI_FM_%s_%s_PCE_06.00.00.fits' % (detnick,pce_subchan_name))

    if output == 'filepath':
        return fringe_file,photom_file,psf_file,resol_file,pce_file
    elif output == 'img':
        from astropy.io import fits
        fringe_img     = fits.open(fringe_file)[1].data        # [unitless]
        photom_img     = fits.open(photom_file)[1].data        # [DN/s * pixel/mJy]
        pixsiz_img     = fits.open(photom_file)[5].data        # [arcsec^2/pix]
        psffits        = fits.open(psf_file)                   # [unitless]
        specres_table  = fits.open(resol_file)[1].data         # [unitless]
        pce_table      = fits.open(pce_file)[1].data
        return fringe_img,photom_img,pixsiz_img,psffits,specres_table,pce_table
    elif output == 'img_error':
        from astropy.io import fits
        fringe_img_error = fits.open(fringe_file)[2].data        # [unitless]
        photom_img_error = fits.open(photom_file)[2].data        # [DN/s * pixel/mJy]
        return fringe_img_error,photom_img_error

#--import MIRIM PSFs
def mirimpsfs(workDir=None):
    import glob
    # CV2 PSF measurements
    dataDir = workDir+'CV2_data/LVL2/'

    files = [os.path.basename(i) for i in glob.glob(dataDir+'*')]
    subchannels = ['SHORT','MED','LONG']
    pointings = ['P'+str(i) for i in range(17)]

    MIRIMPSF_dictionary = {}
    for pointing in pointings:
        mylist = []
        for subchannel in subchannels:
            sub = 'MIRM0363-{}-{}'.format(pointing,subchannel)
            mylist.extend([s for s in files if sub in s])
        MIRIMPSF_dictionary['CV2_'+pointing] = list(mylist)

    # CV3 PSF measurements
    dataDir = workDir+'CV3_data/LVL2/'

    files = [os.path.basename(i) for i in glob.glob(dataDir+'*')]

    pointings = ['Q'+str(i) for i in range(17)]
    for pointing in pointings:
        sub = 'MIRM103-{}-SHORT'.format(pointing)
        MIRIMPSF_dictionary['CV3_'+pointing] = [s for s in files if sub in s]

    # Dictionary keys are equivalent to PSF measurements in CV2 and CV3 tests (with different pointings).
    # Dictionary indeces within keys, for CV2 obs. are equivalent to:
    # [0,1,2,3] : SHORT_494,SHORT_495,SHORTB_494,SHORTB_495
    # [4,5,6,7] : MED_494,MED_495,MEDB_494,MEDB_495
    # [8,9,10,11] : LONG_494,LONG_495,LONGB_494,LONGB_495

    # Dictionary indeces within keys, for CV3 obs. are equivalent to:
    # [0,1,2,3] : SHORT_494,SHORT_495,SHORTB_494,SHORTB_495
    # There are only SHORT CV3 PSF measurements

    return MIRIMPSF_dictionary

#--corrections
def OddEvenRowSignalCorrection(sci_img,nRows=1024):
    copy_img = sci_img.copy()
    for nRow in range(nRows-2):
        copy_img[nRow+1,:] = (((sci_img[nRow,:]+sci_img[nRow+2,:])/2.)+sci_img[nRow+1,:])/2.
    return copy_img

# straylight correction
def Shepard2DKernel(R, k):
    """
    Calculates the kernel matrix of Shepard's modified algorithm
    R : Radius of influence
    k : exponent
    """
    xk, yk = np.meshgrid(np.arange(-R/2, R/2+1),np.arange(-R/2, R/2+1))
    d = np.sqrt(xk**2+yk**2)
    w = (np.maximum(0,R-d)/(R*d))**k
    w[d==0]=0
    return w

def straylightCorrection(sci_img,sliceMap,R=50, k=1, output='source'):
    from astropy.convolution import convolve, Box2DKernel
    """
    Applies a modified version of the Shepard algorithm to remove straylight from the MIRI MRS detector
    img: Input image
    R: Radius of influence
    k: exponent of Shepard kernel
    sliceMap: Matrix indicating slice (band*100+slice_nr) and gap (0) pixels
    """
    w = Shepard2DKernel(R,k) # calculate kernel
    #mask where gap pixels are 1 and slice pixels are 0
    mask = np.zeros_like(sliceMap)
    mask[sliceMap == 0] = 1
    #apply mask to science img
    img_gap = sci_img*mask

    # img_gap[img_gap>0.02*np.max(sci_img[sliceMap>0])] = 0 # avoid cosmic rays contaminating result
    img_gap[img_gap<0] = 0 # set pixels less than zero to 0
    img_gap = convolve(img_gap, Box2DKernel(3)) # smooth gap pixels with Boxkernel
    img_gap*=mask # reset sci pixels to 0
    # convolve gap pixel img with weight kernel
    astropy_conv = convolve(img_gap, w)
    # normalize straylight flux by sum of weights
    norm_conv = convolve(mask, w)
    astropy_conv /= norm_conv
    # reinstate gap pixels to previous values
    #astropy_conv[sliceMap==0] = img_gap[sliceMap==0]
    if output=='source':
        return sci_img-astropy_conv
    elif output=='straylight':
        return astropy_conv

def straylightManga(band,sci_img,err_img,sliceMap,det_dims=(1024,1032)):
    from scipy.interpolate import splrep,BSpline
    nx = det_dims[1]
    ny = det_dims[0]

    # Get rid of any nans
    sci_img[np.isnan(sci_img)] = 0
    # Get rid of any negative values
    sci_img[sci_img<0] = 0

    # Make a simple mask from the slice map for illustrative purposes
    simplemask = np.full(det_dims,0)
    simplemask[np.nonzero(sliceMap)] = 1.

    # Define the ids of the individual slices
    sliceid1=[111,121,110,120,109,119,108,118,107,117,106,116,105,115,104,114,103,113,102,112,101]
    sliceid2=[201,210,202,211,203,212,204,213,205,214,206,215,207,216,217,209] # 208,
    sliceid3=[316,308,315,307,314,306,313,305,312,304,311,303,310,302,309,301]
    sliceid4=[412,406,411,405,410,404,409,403,408,402,407,401]

    if band[0] in ['1','2']:
        sliceid1,sliceid2 = sliceid1,sliceid2
    elif band[0] in ['3','4']:
        sliceid1,sliceid2 = sliceid4,sliceid3
    nslice1,nslice2 = len(sliceid1),len(sliceid2)

    # Make our mask for straylight purposes dynamically
    mask = np.zeros(det_dims)

    # At the edges and middle of the detector we'll select pixels at least 5 pixels away from the nearest slice to use in creating our model
    optspace=5

    # In each gap between slices we'll select the pixel with the lowest flux
    # Loop up rows
    for i in range(ny):
        # Define temporary vector of slicenum along this row
        temp = sliceMap[i,:]
        # Left edge of detector
        indxr = np.where(temp == sliceid1[0])[0]
        mask[i,:indxr[0]-optspace] = 1
        # Left-half slices
        for j in range(nslice1-1):
            indxl = np.where(temp == sliceid1[j])[0]
            indxr = np.where(temp == sliceid1[j+1])[0]
            flux  = sci_img[i,indxl[-1]+1:indxr[0]-1] # signal in pixels between two stripes/slices on the detector
            indx  = np.where(flux == min(flux))[0]
            mask[i,indx[0]+(indxl[-1]+1)] = 1
        # Mid-detector pixels
        indxl = np.where(temp == sliceid1[-1])[0]
        indxr = np.where(temp == sliceid2[0])[0]
        mask[i,indxl[-1]+optspace:indxr[0]-optspace] = 1
        # Right-half slices
        for j in range(nslice2-1):
            indxl = np.where(temp == sliceid2[j])[0]
            indxr = np.where(temp == sliceid2[j+1])[0]
            flux  = sci_img[i,indxl[-1]+1:indxr[0]-1] # signal in pixels between two stripes/slices on the detector
            indx  = np.where(flux == min(flux))[0]
            mask[i,indx[0]+(indxl[-1]+1)] = 1
        # Right edge of detector
        indxl = np.where(temp == sliceid2[-1])[0]
        mask[i,indxl[-1]+optspace:] = 1

    # Mask the data
    masked_data = sci_img*mask

    # Create the scattered light array
    scatmodel_pass1 = np.zeros(det_dims)
    scatmodel_pass2 = np.zeros(det_dims)
    # Define pixel vectors
    xvec = np.arange(nx)
    yvec = np.arange(ny)

    # Bspline the unmasked pixels looping along each row
    for i in range(ny):
        indx  = np.where(mask[i,:] == 1)[0] # select only unmasked pixels
        thisx = xvec[indx]
        thisf = sci_img[i,indx]
        var = (err_img[i,indx]**2)[~np.isnan(err_img[i,indx])].sum()
    #     var = np.var(thisf[~np.isnan(thisf)])
        w = np.full(len(thisx),1.0/var)

        everyn = 5
        len_thisx = len(thisx)
        nbkpts = (len_thisx / everyn)
        xspot = np.arange(nbkpts)*(len_thisx / (nbkpts-1))
        bkpt = thisx[xspot]
        bkpt = bkpt.astype(float)
        fullbkpt = bkpt.copy()

        t, c, k = splrep(thisx, thisf, w=w, task=-1, t=fullbkpt[1:-1])
        spline = BSpline(t, c, k, extrapolate=False)
        scatmodel_pass1[i,:] = spline(xvec) # expand spline to the full range of x values

    # Get rid of nans:
    scatmodel_pass1[np.isnan(scatmodel_pass1)] = 0

    # Get rid of negative spline values
    scatmodel_pass1[scatmodel_pass1<0] = 0

    # Bspline again in the Y direction
    for i in range(nx):
        thisy = yvec[~np.isnan(scatmodel_pass1[:,i])]
        thisf = scatmodel_pass1[:,i][~np.isnan(scatmodel_pass1[:,i])]
    #     var = (err_img[:,i]**2)[~np.isnan(err_img[:,i])].sum()
        var = np.var(thisf[~np.isnan(thisf)])
        w = np.full(len(thisy),1./var)

        everyn = 30
        len_thisy = len(thisy)
        nbkpts = (len_thisy / everyn)
        yspot = np.arange(nbkpts)*(len_thisy / (nbkpts-1))
        bkpt = thisy[yspot]
        bkpt = bkpt.astype(float)
        fullbkpt = bkpt.copy()

        t, c, k = splrep(thisy, thisf, w=w,task=-1, t=fullbkpt[1:-1]) # spline breakpoint every 30 values
        spline = BSpline(t, c, k, extrapolate=False)
        scatmodel_pass2[:,i] = spline(yvec)

    return sci_img - scatmodel_pass2

#--compute
def getSpecR(lamb0=None,band=None,specres_table=None):
    """Return spectral resolution (a.k.a. resolving power)"""
    res_select = 'res_avg'
    resDic = {'res_low':[2,3,4],'res_high':[5,6,7],'res_avg':[8,9,10]}
    subchan_names = {'A':'SHORT','B':'MEDIUM','C':'LONG'}
    resol_subchan_name = band[0]+subchan_names[band[1]]
    band_list = {'1SHORT':0,'1MEDIUM':1,'1LONG':2,\
                 '2SHORT':3,'2MEDIUM':4,'2LONG':5,\
                 '3SHORT':6,'3MEDIUM':7,'3LONG':8,\
                 '4SHORT':9,'4MEDIUM':10,'4LONG':11}

    specR = specres_table[band_list[resol_subchan_name]][resDic[res_select][0]] + \
            specres_table[band_list[resol_subchan_name]][resDic[res_select][1]]*(lamb0-specres_table[band_list[resol_subchan_name]][1]) + \
            specres_table[band_list[resol_subchan_name]][resDic[res_select][2]]*(lamb0-specres_table[band_list[resol_subchan_name]][1])**2

    return specR

def getSpecR_linearR(lamb0=None,band=None):
    """Return spectral resolution (a.k.a. resolving power) assuming a linear relation to wavelength"""
    MRS_bands = {'1A':[4.83,5.82],
        '1B':[5.62,6.73],
        '1C':[6.46,7.76],
        '2A':[7.44,8.90],
        '2B':[8.61,10.28],
        '2C':[9.94,11.87],
        '3A':[11.47,13.67],
        '3B':[13.25,15.80],
        '3C':[15.30,18.24],
        '4A':[17.54,21.10],
        '4B':[20.44,24.72],
        '4C':[23.84,28.82]} # microns
    MRS_R = {'1A':[3320.,3710.],
        '1B':[3190.,3750.],
        '1C':[3100.,3610.],
        '2A':[2990.,3110.],
        '2B':[2750.,3170.],
        '2C':[2860.,3300.],
        '3A':[2530.,2880.],
        '3B':[1790.,2640.],
        '3C':[1980.,2790.],
        '4A':[1460.,1930.],
        '4B':[1680.,1770.],
        '4C':[1630.,1330.]} # R = lambda / delta_lambda
    bandlims = MRS_bands[band]
    Rlims = MRS_R[band]
    specR = (Rlims[1]-Rlims[0])/(bandlims[1]-bandlims[0]) * (lamb0-bandlims[0]) + Rlims[0]
    return specR

def spectral_gridding(band,d2cMaps,specres_table=None,oversampling = 1.):
    # Construct spectral (wavelength) grid
    lambdaMap = d2cMaps['lambdaMap']
    bandlims  = [lambdaMap[np.nonzero(lambdaMap)].min(),lambdaMap[np.nonzero(lambdaMap)].max()]
    #> initialize variables
    lambcens = []
    lambfwhms = []

    #> loop over wavelength bins (bin width defined based on MRS spectral resolution)
    lamb0   = bandlims[0]
    maxlamb = bandlims[1]

    # first iteration
    R       = getSpecR(lamb0=lamb0,band=band,specres_table=specres_table)
    fwhm    = lamb0 / R
    lambcen = lamb0 + (fwhm/2.)/oversampling

    lambcens.append(lambcen)
    lambfwhms.append(fwhm)

    # iterate over spectral range
    done = False
    while not done:
        R = getSpecR(lamb0=lamb0,band=band,specres_table=specres_table)
        fwhm = lamb0 / R
        lambcen = lamb0 + (fwhm/2.)/oversampling
        if (lambcen > maxlamb-(fwhm/2.)/oversampling):
            done = True
        else:
            lamb0 = lambcen + (fwhm/2.)/oversampling

        lambcens.append(lambcen)
        lambfwhms.append(fwhm)

    return np.array(lambcens),np.array(lambfwhms)

def spectral_gridding_linearR(band=None,d2cMaps=None,oversampling = 1.):
    # Construct spectral (wavelength) grid
    lambdaMap = d2cMaps['lambdaMap']
    bandlims  = [lambdaMap[np.nonzero(lambdaMap)].min(),lambdaMap[np.nonzero(lambdaMap)].max()]
    #> initialize variables
    lambcens = []
    lambfwhms = []

    #> loop over wavelength bins (bin width defined based on MRS spectral resolution)
    lamb0   = bandlims[0]
    maxlamb = bandlims[1]

    # first iteration
    R       = getSpecR_linearR(lamb0=lamb0,band=band)
    fwhm    = lamb0 / R
    lambcen = lamb0 + (fwhm/2.)/oversampling

    lambcens.append(lambcen)
    lambfwhms.append(fwhm)

    # iterate over spectral range
    done = False
    while not done:
        R = getSpecR_linearR(lamb0=lamb0,band=band)
        fwhm = lamb0 / R
        lambcen = lamb0 + (fwhm/2.)/oversampling
        if (lambcen > maxlamb-(fwhm/2.)/oversampling):
            done = True
        else:
            lamb0 = lambcen + (fwhm/2.)/oversampling

        lambcens.append(lambcen)
        lambfwhms.append(fwhm)

    return np.array(lambcens),np.array(lambfwhms)

def point_source_centroiding(band,sci_img,d2cMaps,spec_grid=None,fit='2D',center=None):
    # distortion maps
    sliceMap  = d2cMaps['sliceMap']
    lambdaMap = d2cMaps['lambdaMap']
    alphaMap  = d2cMaps['alphaMap']
    betaMap   = d2cMaps['betaMap']
    nslices   = d2cMaps['nslices']
    MRS_alphapix = {'1':0.196,'2':0.196,'3':0.245,'4':0.273} # arcseconds
    MRS_FWHM = {'1':2.16*MRS_alphapix['1'],'2':3.30*MRS_alphapix['2'],
                '3':4.04*MRS_alphapix['3'],'4':5.56*MRS_alphapix['4']} # MRS PSF
    mrs_fwhm  = MRS_FWHM[band[0]]
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]
    unique_betas = np.sort(np.unique(betaMap[(sliceMap>100*int(band[0])) & (sliceMap<100*(int(band[0])+1))]))
    fov_lims  = [alphaMap[np.nonzero(lambdaMap)].min(),alphaMap[np.nonzero(lambdaMap)].max()]

    print 'STEP 1: Rough centroiding'
    if center is None:
        # premise> center of point source is located in slice with largest signal
        # across-slice center:
        sum_signals = np.zeros(nslices)
        for islice in xrange(1+nslices):
            sum_signals[islice-1] = sci_img[(sliceMap == 100*int(band[0])+islice) & (~np.isnan(sci_img))].sum()
        source_center_slice = np.argmax(sum_signals)+1

        # along-slice center:
        det_dims = (1024,1032)
        img = np.full(det_dims,0.)
        sel = (sliceMap == 100*int(band[0])+source_center_slice)
        img[sel]  = sci_img[sel]

        source_center_alphas = []
        for row in range(det_dims[0]):
            source_center_alphas.append(alphaMap[row,img[row,:].argmax()])
        source_center_alphas = np.array(source_center_alphas)
        source_center_alpha  = np.average(source_center_alphas[~np.isnan(source_center_alphas)])
    else:
        source_center_slice,source_center_alpha = center[0],center[1]
    # summary:
    print 'Slice {} has the largest summed flux'.format(source_center_slice)
    print 'Source position: beta = {}arcsec, alpha = {}arcsec \n'.format(round(unique_betas[source_center_slice-1],2),round(source_center_alpha,2))

    print 'STEP 2: 1D Gaussian fit'

    # Fit Gaussian distribution to along-slice signal profile
    sign_amp,alpha_centers,alpha_fwhms,bkg_signal = [np.full((len(lambcens)),np.nan) for j in range(4)]
    failed_fits = []
    for ibin in xrange(len(lambcens)):
        coords = np.where((sliceMap == 100*int(band[0])+source_center_slice) & (np.abs(lambdaMap-lambcens[ibin])<=lambfwhms[ibin]/2.) & (~np.isnan(sci_img)))
        if len(coords[0]) == 0: failed_fits.append(ibin); continue
        try:popt,pcov = curve_fit(gauss1d_wBaseline, alphaMap[coords], sci_img[coords], p0=[sci_img[coords].max(),source_center_alpha,mrs_fwhm/2.355,0],method='lm')
        except: failed_fits.append(ibin); continue
        sign_amp[ibin]      = popt[0]+popt[3]
        alpha_centers[ibin] = popt[1]
        alpha_fwhms[ibin]   = 2.355*np.abs(popt[2])
        bkg_signal[ibin]    = popt[3]

    # omit outliers
    for i in xrange(len(np.diff(sign_amp))):
        if np.abs(np.diff(alpha_centers)[i]) > 0.05:
            sign_amp[i],sign_amp[i+1],alpha_centers[i],alpha_centers[i+1],alpha_fwhms[i],alpha_fwhms[i+1] = [np.nan for j in range(6)]

    print '[Along-slice fit] The following bins failed to converge:'
    print failed_fits

    # Fit Gaussian distribution to across-slice signal profile (signal brute-summed in each slice)
    summed_signal,beta_centers,beta_fwhms = [np.full((len(lambcens)),np.nan) for j in range(3)]
    failed_fits = []
    for ibin in range(len(lambcens)):
        if np.isnan(alpha_centers[ibin]): failed_fits.append(ibin);continue
        sel = (np.abs(lambdaMap-lambcens[ibin])<=lambfwhms[ibin]/2.) & (~np.isnan(sci_img))
        try:signals = np.array([sci_img[(sliceMap == 100*int(band[0])+islice) & sel][np.abs(alphaMap[(sliceMap == 100*int(band[0])+islice) & sel]-alpha_centers[ibin]).argmin()] for islice in range(1,1+nslices)])
        except ValueError: failed_fits.append(ibin); continue
        try:popt,pcov = curve_fit(gauss1d_wBaseline, unique_betas, signals, p0=[signals.max(),unique_betas[source_center_slice-1],mrs_fwhm/2.355,0],method='lm')
        except: failed_fits.append(ibin); continue
        summed_signal[ibin] = popt[0]+popt[3]
        beta_centers[ibin]  = popt[1]
        beta_fwhms[ibin]    = 2.355*np.abs(popt[2])

    # # omit outliers
    # for i in range(len(np.diff(summed_signal))):
    #     if np.abs(np.diff(beta_centers)[i]) > 0.05:
    #         summed_signal[i],summed_signal[i+1],beta_centers[i],beta_centers[i+1],beta_fwhms[i],beta_fwhms[i+1] = [np.nan for j in range(6)]

    print '[Across-slice fit] The following bins failed to converge:'
    print failed_fits
    print ''

    if fit == '1D':
        sigma_alpha, sigma_beta = alpha_fwhms/2.355, beta_fwhms/2.355
        return sign_amp,alpha_centers,beta_centers,sigma_alpha,sigma_beta,bkg_signal

    elif fit == '2D':
        print 'STEP 3: 2D Gaussian fit'
        sign_amp2D,alpha_centers2D,beta_centers2D,sigma_alpha2D,sigma_beta2D,bkg_amp2D = [np.full((len(lambcens)),np.nan) for j in range(6)]
        failed_fits = []

        for ibin in range(len(lambcens)):
            # initial guess for fitting, informed by previous centroiding steps
            amp,alpha0,beta0  = sign_amp[ibin],alpha_centers[ibin],beta_centers[ibin]
            sigma_alpha, sigma_beta = alpha_fwhms[ibin]/2.355, beta_fwhms[ibin]/2.355
            base = 0
            guess = [amp, alpha0, beta0, sigma_alpha, sigma_beta, base]
            bounds = ([0,-np.inf,-np.inf,0,0,-np.inf],[np.inf,np.inf,np.inf,np.inf,np.inf,np.inf])

            # data to fit
            coords = (np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.)
            alphas, betas, zobs   = alphaMap[coords],betaMap[coords],sci_img[coords]
            alphabetas = np.array([alphas,betas])

            # perform fitting
            try:popt,pcov = curve_fit(gauss2d, alphabetas, zobs, p0=guess,bounds=bounds)
            except: failed_fits.append(ibin); continue

            sign_amp2D[ibin]      = popt[0]
            alpha_centers2D[ibin] = popt[1]
            beta_centers2D[ibin]  = popt[2]
            sigma_alpha2D[ibin]   = popt[3]
            sigma_beta2D[ibin]    = popt[4]
            bkg_amp2D[ibin]       = popt[5]

        print 'The following bins failed to converge:'
        print failed_fits

        return sign_amp2D,alpha_centers2D,beta_centers2D,sigma_alpha2D,sigma_beta2D,bkg_amp2D

def point_source_along_slice_centroiding(band,sci_img,d2cMaps,spec_grid=None,offset_slice=0,campaign=None):
    # same as "point_source_centroiding" function, however only performs 1D Gaussian fitting, in along-slice (alpha) direction
    # param. "offset slice" allows to perform the centroiding analysis in a neighboring slice
    # distortion maps
    sliceMap  = d2cMaps['sliceMap']
    lambdaMap = d2cMaps['lambdaMap']
    alphaMap  = d2cMaps['alphaMap']
    betaMap   = d2cMaps['betaMap']
    nslices   = d2cMaps['nslices']

    mrs_fwhm  = mrs_aux(band)[8]
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]
    unique_betas = np.sort(np.unique(betaMap[(sliceMap>100*int(band[0])) & (sliceMap<100*(int(band[0])+1))]))
    fov_lims  = [alphaMap[np.nonzero(lambdaMap)].min(),alphaMap[np.nonzero(lambdaMap)].max()]

    # premise> center of point source is located in slice with largest signal
    # across-slice center:
    sum_signals = np.zeros(nslices)
    for islice in xrange(1+nslices):
        sum_signals[islice-1] = sci_img[(sliceMap == 100*int(band[0])+islice) & (~np.isnan(sci_img))].sum()
    source_center_slice = np.argmax(sum_signals)+1
    source_center_slice+=offset_slice

    print 'Slice {} has the largest summed flux'.format(source_center_slice)

    # along-slice center:
    det_dims = (1024,1032)
    img = np.full(det_dims,0.)
    sel = (sliceMap == 100*int(band[0])+source_center_slice)
    img[sel]  = sci_img[sel]

    first_nonzero_row = 0
    while all(img[first_nonzero_row,:][~np.isnan(img[first_nonzero_row,:])] == 0.): first_nonzero_row+=1
    source_center_alpha = alphaMap[first_nonzero_row,img[first_nonzero_row,:].argmax()]
    if campaign=='CV1RR':
        source_center_alpha = alphaMap[np.where(img[~np.isnan(img)].max() == img)]

    # Fit Gaussian distribution to along-slice signal profile
    sign_amps,alpha_centers,alpha_sigmas,bkg_amps = [np.full((len(lambcens)),np.nan) for j in range(4)]
    failed_fits = []
    for ibin in xrange(len(lambcens)):
        coords = np.where((sliceMap == 100*int(band[0])+source_center_slice) & (np.abs(lambdaMap-lambcens[ibin])<=lambfwhms[ibin]/2.) & (~np.isnan(sci_img)))
        if len(coords[0]) == 0: failed_fits.append(ibin); continue
        try:popt,pcov = curve_fit(gauss1d_wBaseline, alphaMap[coords], sci_img[coords], p0=[sci_img[coords].max(),source_center_alpha,mrs_fwhm/2.355,0],method='lm')
        except: failed_fits.append(ibin); continue
        sign_amps[ibin]     = popt[0]
        alpha_centers[ibin] = popt[1]
        alpha_sigmas[ibin]  = np.abs(popt[2])
        bkg_amps[ibin]      = popt[3]

    print 'The following bins failed to converge:'
    print failed_fits

    # omit outliers
    for i in xrange(len(np.diff(sign_amps))):
        if np.abs(np.diff(alpha_centers)[i]) > 0.05:
            sign_amps[i],sign_amps[i+1],alpha_centers[i],alpha_centers[i+1],alpha_sigmas[i],alpha_sigmas[i+1],bkg_amps[i],bkg_amps[i+1] = [np.nan for j in range(8)]
    if campaign == 'CV1RR':
        for i in xrange(len(np.diff(sign_amps))):
            if np.abs(np.diff(sign_amps)[i]) > 10.:
                sign_amps[i],sign_amps[i+1],alpha_centers[i],alpha_centers[i+1],alpha_sigmas[i],alpha_sigmas[i+1],bkg_amps[i],bkg_amps[i+1] = [np.nan for j in range(8)]

    return sign_amps,alpha_centers,source_center_slice,alpha_sigmas,bkg_amps

def get_pixel_spatial_area(band=None,d2cMaps=None):
    # Calculate size map
    # The spatial area of a pixel (assumed quadrilateral) is calculated as the sum of two triangles
    # The two trangles have side lengths A,B,C, and side C is shared (i.e. equal in both triangles)

    #get dimensions
    alphaULMap = d2cMaps['alphaULMap']
    alphaLLMap = d2cMaps['alphaLLMap']
    alphaURMap = d2cMaps['alphaURMap']
    alphaLRMap = d2cMaps['alphaULMap']

    betaULMap = d2cMaps['betaULMap']
    betaLLMap = d2cMaps['betaLLMap']
    betaURMap = d2cMaps['betaURMap']
    betaLRMap = d2cMaps['betaULMap']

    A1 = np.sqrt( (alphaULMap-alphaLLMap)**2 + (betaULMap-betaLLMap)**2 )
    B1 = np.sqrt( (alphaURMap-alphaULMap)**2 + (betaURMap-betaULMap)**2 )
    C1 = np.sqrt( (alphaURMap-alphaLLMap)**2 + (betaURMap-betaLLMap)**2 )
    A2 = np.sqrt( (alphaURMap-alphaLRMap)**2 + (betaURMap-betaLRMap)**2 )
    B2 = np.sqrt( (alphaLRMap-alphaLLMap)**2 + (betaLRMap-betaLLMap)**2 )
    C2 = C1.copy()

    # The area of a triangle can be calculated from the length of its sides using Heron's formula
    s1 = (A1+B1+C1)/2. # half of triangle's perimeter
    s2 = (A2+B2+C2)/2. # " " "

    Area1 = np.sqrt(s1*(s1-A1)*(s1-B1)*(s1-C1))
    Area2 = np.sqrt(s2*(s2-A2)*(s2-B2)*(s2-C2))

    spaxelsizeMap = Area1 + Area2

    return spaxelsizeMap

def get_pixel_area_in_alphalambda(band=None,d2cMaps=None):
    # Calculate size map
    # The spatial area of a pixel (assumed quadrilateral) is calculated as the sum of two triangles
    # The two trangles have side lengths A,B,C, and side C is shared (i.e. equal in both triangles)

    #get dimensions
    alphaULMap = d2cMaps['alphaULMap']
    alphaLLMap = d2cMaps['alphaLLMap']
    alphaURMap = d2cMaps['alphaURMap']
    alphaLRMap = d2cMaps['alphaULMap']

    lambdaULMap = d2cMaps['lambdaULMap']
    lambdaLLMap = d2cMaps['lambdaLLMap']
    lambdaURMap = d2cMaps['lambdaURMap']
    lambdaLRMap = d2cMaps['lambdaULMap']

    A1 = np.sqrt( (alphaULMap-alphaLLMap)**2 + (lambdaULMap-lambdaLLMap)**2 )
    B1 = np.sqrt( (alphaURMap-alphaULMap)**2 + (lambdaURMap-lambdaULMap)**2 )
    C1 = np.sqrt( (alphaURMap-alphaLLMap)**2 + (lambdaURMap-lambdaLLMap)**2 )
    A2 = np.sqrt( (alphaURMap-alphaLRMap)**2 + (lambdaURMap-lambdaLRMap)**2 )
    B2 = np.sqrt( (alphaLRMap-alphaLLMap)**2 + (lambdaLRMap-lambdaLLMap)**2 )
    C2 = C1.copy()

    # The area of a triangle can be calculated from the length of its sides using Heron's formula
    s1 = (A1+B1+C1)/2. # half of triangle's perimeter
    s2 = (A2+B2+C2)/2. # " " "

    Area1 = np.sqrt(s1*(s1-A1)*(s1-B1)*(s1-C1))
    Area2 = np.sqrt(s2*(s2-A2)*(s2-B2)*(s2-C2))

    pixsiz_alphalambda = Area1 + Area2

    return pixsiz_alphalambda

def standard_photometry_point_source(sci_img,d2cMaps,spec_grid=None):
    lambdaMap = d2cMaps['lambdaMap']
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]

    signals_standard = np.zeros(len(lambcens))
    for ibin in range(len(lambcens)):
        # map containing only pixels within one spectral bin, omitting NaNs
        pixelsInBinNoNaN = np.where((np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.) & (np.isnan(sci_img)==False) )
        # number of pixels in spectral bin and in aperture
        nPixels = len(pixelsInBinNoNaN[0])
        # map containing only pixels within one spectral bin
        sci_img_masked = sci_img[pixelsInBinNoNaN]
        # perform aperture photometry
        signals_standard[ibin] = sci_img_masked.sum()/nPixels
    return signals_standard

def aperture_photometry_point_source(band,sci_img,apertureMask,aperture_area,d2cMaps,spec_grid=None,img_type='sci'):
    lambdaMap = d2cMaps['lambdaMap']
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]

    pixsiz_img = get_pixel_spatial_area(band,d2cMaps) # [arcsec*arcsec]
    pixelsiz_alphalambdaMap = get_pixel_area_in_alphalambda(band,d2cMaps) # [arcsec*micron]
    pixvol_img = pixelsiz_alphalambdaMap*d2cMaps['bdel']

    signals_aper = np.zeros(len(lambcens))
    for ibin in range(len(lambcens)):
        # map containing only pixels within one spectral bin, within the defined aperture, omitting NaNs
        pixelsInBinInApertureNoNaN = np.where((np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.) & (apertureMask!=0.) & (np.isnan(sci_img)==False) )
        nPixels = len(pixelsInBinInApertureNoNaN[0])

        # map containing only pixels within one spectral bin, within the defined aperture
        sci_img_masked    = sci_img[pixelsInBinInApertureNoNaN]
        pixsiz_img_masked = pixsiz_img[pixelsInBinInApertureNoNaN]
        pixvol_img_masked = pixvol_img[pixelsInBinInApertureNoNaN]

        # perform aperture photometry
        if img_type=='sci':
            signals_aper[ibin] = sci_img_masked.sum() #/nPixels
            # signals_aper[ibin] = ((sci_img_masked.sum()/pixvol_img_masked.sum()) * aperture_area * lambfwhms[ibin])/nPixels
            # print pixvol_img_masked.sum(), aperture_area * lambfwhms[ibin]
        elif img_type=='err':
            var_img = (sci_img_masked*pixsiz_img_masked)**2.
            signals_aper[ibin] = var_img.sum()/nPixels
            # signals_aper[ibin] = (var_img.sum()/pixvol_img_masked.sum()) * aperture_area * lambfwhms[ibin]
        elif img_type=='psf':
            psf = sci_img

            # enforce normalization of psf in every wavelength bin
            psf[np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.] = psf[np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.]/psf[np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.].sum()

            psf_masked = psf[pixelsInBinInApertureNoNaN]
            signals_aper[ibin] = (psf_masked.sum()/pixvol_img_masked.sum()) * aperture_area * lambfwhms[ibin]

    return signals_aper

def aperture_weighted_photometry_point_source(sci_img,weight_map,d2cMaps,spec_grid=None):
    lambdaMap = d2cMaps['lambdaMap']
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]

    copy_sci_img = sci_img.copy()
    copy_sci_img[np.isnan(copy_sci_img)] = 0

    signals_aper = np.zeros(len(lambcens))
    for ibin in range(len(lambcens)):
        # map containing only pixels within one spectral bin, within the defined aperture, omitting NaNs
        pixelsInBin = np.where(np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.)

        # map containing only pixels within one spectral bin, within the defined aperture
        sci_img_masked    = copy_sci_img[pixelsInBin]*weight_map[pixelsInBin]

        # perform aperture photometry
        signals_aper[ibin] = sci_img_masked.sum()
    return signals_aper

def aperture_photometry_extended_source(sci_img,apertureMask,aperture_area,d2cMaps=None,spec_grid=None):
    lambdaMap = d2cMaps['lambdaMap']
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]

    signals_aper = np.zeros(len(lambcens))
    for ibin in range(len(lambcens)):
        # map containing only pixels within one spectral bin, within the defined aperture, omitting NaNs
        pixelsInBinInApertureNoNaN = np.where((np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.) & (apertureMask!=0.) & (np.isnan(sci_img)==False) )
        # number of pixels in spectral bin and in aperture
        nPixels = len(pixelsInBinInApertureNoNaN[0])

        # map containing only pixels within one spectral bin, within the defined aperture
        sci_img_masked    = sci_img[pixelsInBinInApertureNoNaN]

        # perform aperture photometry
        signals_aper[ibin] = (sci_img_masked.sum()/nPixels) * aperture_area
    return signals_aper

def pixel_signal_contribution(d2cMaps,aperture,spec_grid=None):
    from shapely.geometry import Polygon
    print 'Pixel weight mapping'
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]
    weight_map = np.zeros((1024,1032))
    for ibin in range(len(lambcens)):
        if ibin%100 == 0: print '{}/{} bins processed'.format(ibin,len(lambcens))
        i,j = np.where(np.abs(d2cMaps['lambdaMap']-lambcens[ibin])<lambfwhms[ibin]/2.)
        for pix in range(len(i)):
            alphaUR = d2cMaps['alphaURMap'][i[pix],j[pix]]
            alphaUL = d2cMaps['alphaULMap'][i[pix],j[pix]]
            alphaLL = d2cMaps['alphaLLMap'][i[pix],j[pix]]
            alphaLR = d2cMaps['alphaLRMap'][i[pix],j[pix]]

            betaUR = d2cMaps['betaURMap'][i[pix],j[pix]]
            betaUL = d2cMaps['betaULMap'][i[pix],j[pix]]
            betaLL = d2cMaps['betaLLMap'][i[pix],j[pix]]
            betaLR = d2cMaps['betaLRMap'][i[pix],j[pix]]

            alphabetaUR = [alphaUR,betaUR]
            alphabetaUL = [alphaUL,betaUL]
            alphabetaLL = [alphaLL,betaLL]
            alphabetaLR = [alphaLR,betaLR]

            xy = [alphabetaUR, alphabetaUL, alphabetaLL, alphabetaLR]
            polygon_shape = Polygon(xy)

            weight_map[i[pix],j[pix]] = polygon_shape.intersection(aperture).area/polygon_shape.area
    print '{}/{} bins processed'.format(len(lambcens),len(lambcens))
    return weight_map

def aperture_weighted_photometry_extended_source(sci_img,weight_map,aperture_area,d2cMaps=None,spec_grid=None):
    lambdaMap = d2cMaps['lambdaMap']
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]

    copy_sci_img = sci_img.copy()
    copy_sci_img[np.isnan(copy_sci_img)] = 0

    signals_aper = np.zeros(len(lambcens))
    for ibin in range(len(lambcens)):
        # map containing only pixels within one spectral bin, within the defined aperture, omitting NaNs
        pixelsInBin = np.where((np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.) )

        # map containing only pixels within one spectral bin, within the defined aperture
        sci_img_masked    = sci_img[pixelsInBin]*weight_map[pixelsInBin]

        # perform aperture photometry
        signals_aper[ibin] = (sci_img_masked.sum()/weight_map[pixelsInBin].sum()) * aperture_area
    return signals_aper

def optimal_extraction(band,sci_img,err_img,psf,d2cMaps,spec_grid=None):
    lambdaMap = d2cMaps['lambdaMap']
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]
    var_img    = err_img**2.
    psf_copy   = psf.copy()

    signals_opex,signals_error_opex = np.zeros(len(lambcens)),np.zeros(len(lambcens))
    for ibin in range(len(lambcens)):
        # map containing only pixels within one spectral bin
        pixelsInBinNoNaN = np.where((np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.) & (np.isnan(sci_img)==False) & (np.isnan(var_img)==False) )
        # number of pixels in spectral bin and in aperture
        nPixels = len(pixelsInBinNoNaN[0])

        # enforce normalization of psf in every wavelength bin
        psf_copy[pixelsInBinNoNaN] = psf_copy[pixelsInBinNoNaN]/psf_copy[pixelsInBinNoNaN].sum()

        # compute weights
        weights = psf_copy[pixelsInBinNoNaN]**2./var_img[pixelsInBinNoNaN]

        signals_opex[ibin] = ( ( weights*sci_img[pixelsInBinNoNaN]/psf_copy[pixelsInBinNoNaN] ).sum()/weights.sum() )
        signals_error_opex[ibin] = np.sqrt( 1/weights.sum() )

    return signals_opex,signals_error_opex

#--degrade
def convolvegauss(wavelength,flux,FWHM = None, mode = 'same'):
    """
    returns degraded flux plofile in accordance with the
    input resolution defined through {FWHM} which is equal to
    the mean wavelength of the wavelength range considered
    divided by the resolution of the instrument

    @ wavelength: numpy 1D array
    @ flux: numpy 1D array
    @ FWHM: numpy float
    """

    # make Gaussian kernel
    width = FWHM/(2.0*np.sqrt(2.0*np.log(2.0))) # convert from FWHM to sigma

    width_pix = width/(wavelength[1]-wavelength[0])

    nker = 20*width_pix # the number of portions (20) making up the kernel is arbitrary...
    # ..it just defines how far the wings of the kernel reach (since the value of the kernel
    # there is expected to be small / close to zero, the kernel is limited to (20) pixel
    # to the left and (20) pixels to the right from the defined center)
    z = (np.arange(nker)- nker/2.)/width_pix
    kernel = np.exp(-z**2/2.)

    # for flux conservation
    scale_factor = kernel.sum()

    # convolve flux array with gaussian
    result = 1./scale_factor * np.convolve(flux, kernel, mode = mode)

    return result

def convolvegauss_windt(x,y,sig):
    """
    NAME:
          convolvegauss_windt
    PURPOSE:
        Convolve a function with a gaussian.
    CALLING SEQUENCE:
        Result=convolvegauss_windt(X,Y,SIG)
    INPUTS:
        X - vector of independent variables.
        Y - vector of dependent variables.
        SIG - width of gaussian, in same units as X.
    KEYWORDS:
          NSIGMA - A factor that determines how many points to use for
                   the gaussian kernel. The exact number of points used
                   depends on the value of SIG and the range of X values
                   as well, but it will be roughly equal to 2*NSIGMA*SIG.
                   Default=2.5.
    PROCEDURE:
          CONVOL is used to convolve y with a gaussian whose width is
          sig, in x axis units.  The gaussian is defined as Gaussian =
          1./sqrt(2.*pi*sigma)*exp(-0.5*(x/sigma)^2)
    """
    nsigma  = 2.5 # approximate width in units of sigma
    nsigma2 = nsigma*2
    n       = len(x)
    conv    = (max(x)-min(x))/(n-1)    # conversion, units/point
    n_pts  = np.ceil(nsigma2*sig/conv) # number of points
    if (n_pts%2) == 0: n_pts += 1      # make odd number of points
    xvar = (np.arange(n_pts)/(n_pts-1)-0.5)*n_pts # approx. - NSIGMA < x < +NSIGMA
    gauss = np.exp(-.5*(xvar/(sig/conv))**2)         # gaussian of width sig.
    scale_factor = gauss.sum() # impose flux conservation

    # convolve y with gaussian kernel
    result = 1./scale_factor * np.convolve(y, gauss, mode = 'same')

    return result

def degradefunc(wvl_range,wvl_arr,flux_arr,resolution):
    flux_arrcopy = np.copy(flux_arr)

    ind_wavlMin = find_nearest(wvl_arr,wvl_range[0])
    ind_wavlMax = find_nearest(wvl_arr,wvl_range[1])
    passband_centralWvl = (wvl_range[0]+wvl_range[1])/2.
    if ind_wavlMin <= 3:
        ind_wavlMin = 3
    boundary_edge = 3 # add elements to convolution in order to get rid of boundary edge effects for mode 'same'

    flux_arrcopy[ind_wavlMin-boundary_edge:ind_wavlMax+boundary_edge] = convolvegauss(wvl_arr[ind_wavlMin-boundary_edge:ind_wavlMax+boundary_edge],flux_arrcopy[ind_wavlMin-boundary_edge:ind_wavlMax+boundary_edge], FWHM = (passband_centralWvl/resolution))
    flux_arr[ind_wavlMin:ind_wavlMax] = flux_arrcopy[ind_wavlMin:ind_wavlMax]

    return flux_arr

#--model
def elliptical_aperture(center=[0,0],r=1.,q=1.,pa=0,d2cMaps=None):
    """
    Elliptical aperture, written by Ruyman Azzollini (DIAS, ruyman.azzollini@gmail.com), edited by Ioannis Argyriou (KUL, ioannis.argyriou@kuleuven.be)

    centre: (alpha,beta)
    r : semi-major axis
    q : axis ratio. q=1 for circular apertures.
    pa : position angle, counter-clockwise from 'y' axis.

    """
    assert q <= 1.

    if q==1:
        spatial_extent = (d2cMaps['alphaMap']-center[0])**2. + (d2cMaps['betaMap']-center[1])**2.
    else:
        radeg = 180. / np.pi
        ang = pa / radeg

        cosang = np.cos(ang)
        sinang = np.sin(ang)

        xtemp = (d2cMaps['alphaMap']-centre[0]) * cosang + (d2cMaps['betaMap']-centre[1]) * sinang
        ytemp = -(d2cMaps['alphaMap']-centre[0]) * sinang + (d2cMaps['betaMap']-centre[1]) * cosang

        spatial_extent = (xtemp/q)**2. + ytemp**2.

    elliptical_aperture_area = np.pi * r**2. * q

    return spatial_extent <= r**2.,elliptical_aperture_area

def rectangular_aperture(center=[0,0],width=1.,height=1.,d2cMaps=None):
    """
    Rectangular aperture, written by Ruyman Azzollini (DIAS, ruyman.azzollini@gmail.com), edited by Ioannis Argyriou (KUL, ioannis.argyriou@kuleuven.be)

    centre: (alpha,beta)
    width : width (alpha dimension)
    height : height (beta dimension)
    """

    pixels_inside_rectangle = (np.abs(d2cMaps['alphaMap']-center[0])<=(width/2.) ) & (np.abs(d2cMaps['betaMap']-center[1])<=(height/2.) )

    rectangular_aperture_area = width * height

    return pixels_inside_rectangle,rectangular_aperture_area

def evaluate_psf_cdp(psffits,d2cMaps,source_center=[0,0]):
    # PSF CDP is provided as a spectral cube
    #>get values
    psf_values = psffits[1].data.transpose(2,1,0) # flip data from Z,Y,X to X,Y,Z

    # #>normalize values
    # for layer in range(psf_values.shape[2]):
    #     psf_values[:,:,layer] /= psf_values[:,:,layer].sum()

    #>get grid
    NAXIS1,NAXIS2,NAXIS3 = psf_values.shape

    alphastpix = psffits[1].header['CRPIX1'] # pixel nr
    alpha_step = psffits[1].header['CDELT1'] # arcsec/pix
    stalpha    = psffits[1].header['CRVAL1']-(alphastpix-1)*alpha_step # arcsec

    betastpix = psffits[1].header['CRPIX2'] # pixel nr
    beta_step = psffits[1].header['CDELT2'] # arcsec/pix
    stbeta    = psffits[1].header['CRVAL2']-(betastpix-1)*beta_step # arcsec

    stwavl = psffits[1].header['CRVAL3'] # microns
    wavl_step   = psffits[1].header['CDELT3'] # microns/pix

    alpha_slices = np.linspace(stalpha,stalpha+ (NAXIS1-1.5)*alpha_step,NAXIS1)
    beta_slices  = np.linspace(stbeta,stbeta+ (NAXIS2-1.5)*beta_step,NAXIS2)
    wvl_slices   = np.linspace(stwavl ,stwavl+NAXIS3*wavl_step,NAXIS3)

    #> center psf to source
    alpha_slices += source_center[0]
    beta_slices  += source_center[1]

    #> create interpolant based on regular grid
    interpolpsf = scp_interpolate.RegularGridInterpolator((alpha_slices,beta_slices,wvl_slices),psf_values)
    interpolpsf.fill_value=0.
    interpolpsf.bounds_error=False

    # evaluate psf at each pixel center and pixel corner
    alphaULMap = d2cMaps['alphaULMap']
    alphaURMap = d2cMaps['alphaURMap']
    alphaLLMap = d2cMaps['alphaLLMap']
    alphaLRMap = d2cMaps['alphaLRMap']
    alphaMap   = d2cMaps['alphaMap']

    betaULMap = d2cMaps['betaULMap']
    betaURMap = d2cMaps['betaURMap']
    betaLLMap = d2cMaps['betaLLMap']
    betaLRMap = d2cMaps['betaLRMap']
    betaMap   = d2cMaps['betaMap']

    lambdaULMap = d2cMaps['lambdaULMap']
    lambdaURMap = d2cMaps['lambdaURMap']
    lambdaLLMap = d2cMaps['lambdaLLMap']
    lambdaLRMap = d2cMaps['lambdaLRMap']
    lambdaMap = d2cMaps['lambdaMap']

    #> interpolate psf to science image pixel centers and corners
    #-- assume no significant change in wavelength over one pixel size
    psfUL  = interpolpsf((alphaULMap,betaULMap,lambdaULMap))
    psfUR  = interpolpsf((alphaURMap,betaURMap,lambdaURMap))
    psfLL  = interpolpsf((alphaLLMap,betaLLMap,lambdaLLMap))
    psfLR  = interpolpsf((alphaLRMap,betaLRMap,lambdaLRMap))
    psfCEN = interpolpsf((alphaMap,betaMap,lambdaMap))

    #> evaluate psf as a weighted average
    w = np.array([0.125,0.125,0.125,0.125,0.5]) # WARNING: ARBITRARY!
    sumweights = w.sum()

    psf = (w[0]*psfUL+w[1]*psfUR+w[2]*psfLL+w[3]*psfLR+w[4]*psfCEN)/sumweights

    return psf

#--fit
# 1d
def straight_line(x,a,b):
    return a*x+b

def order2polyfit(x,a,b,c):
    return a*x**2 + b*x +c

def order3polyfit(x,a,b,c,d):
    return a*x**3 + b*x**2 + c*x +d

def order4polyfit(x,a,b,c,d,e):
    return a*x**4 + b*x**3 + c*x**2 + d*x + e

def gauss1d_wBaseline(x, A, mu, sigma, baseline):
    """1D Gaussian distribution function"""
    return A*np.exp(-(x-mu)**2/(2.*sigma**2))+baseline

def gauss1d_woBaseline(x, A, mu, sigma):
    """1D Gaussian distribution function"""
    return A*np.exp(-(x-mu)**2/(2.*sigma**2))

def skewnorm_func(x, A, mu, sigmag, alpha):
    #normal distribution
    normpdf = (1/(sigmag*np.sqrt(2*np.pi)))*np.exp(-(np.power((x-mu),2)/(2*np.power(sigmag,2))))
    normcdf = (0.5*(1+sp.erf((alpha*((x-mu)/sigmag))/(np.sqrt(2)))))
    return 2*A*normpdf*normcdf

def lorentzian_profile(x,A,mu,sigma):
    # Wrong amplitude?
    L_nu = (2*A/(np.pi*sigma))/(1+4*((x-mu)/sigma)**2)
    return L_nu

def voight_profile(x,A,mu,sigma,f):
    G_nu = (A/sigma) * np.sqrt(4*np.log(2)/np.pi) * np.exp(-4*np.log(2)*((x-mu)/sigma)**2)
    L_nu = (2*A/(np.pi*sigma))/(1+4*((x-mu)/sigma)**2)
    return f*L_nu + (1-f)*G_nu

def skewed_voight(x,A,mu,sigma0,f,a):
    """ According to Stancik and Brauns (2008)"""
    A /= ( ((1-f)/sigma0) * np.sqrt(4*np.log(2)/np.pi) + f*(2./(np.pi*sigma0)))
    sigma = 2*sigma0 / (1+np.exp(a*(x-mu)))
    G_nu = (A/sigma) * np.sqrt(4*np.log(2)/np.pi) * np.exp(-4*np.log(2)*((x-mu)/sigma)**2)
    L_nu = (2*A/(np.pi*sigma))/(1+4*((x-mu)/sigma)**2)
    return f*L_nu + (1-f)*G_nu

def FPfunc(wavenumber,R,D,phi,theta=0):
    # T = 1-R-A
    return (1 + (4*R/(1-R)**2) * np.sin(2*np.pi*D*wavenumber*np.cos(theta) - (phi-np.pi))**2 )**-1

def FPfunc_noPhaseShift(wavenumber,R,D,theta=0):
    # T = 1-R-A
    return (1 + (4*R/(1-R)**2) * np.sin(2*np.pi*D*wavenumber*np.cos(theta))**2 )**-1

def reflectivity_from_continuum(y):
    """
    Spectral continuum where: sin(delta/2) = 0 ==> 1 / (1 + F) = y
    ==> (1 + F) = 1/y ==> F = 1/y -1

    F = 4*R/(1-R)**2 ==> F * (1 -2*R + R**2) - 4*R = 0
    ==> F -2*F*R + F*R**2  - 4*R = 0 ==> R**2 -(2 + 4/F)*R + 1 = 0 (second order equation)

    a = 1; b = -(2 + 4/F) ; c = 1
    Discr = b**2 - 4*a*c = (2 + 4/F)**2 - 4 = 4 + 16/F + 16/F**2 - 4 = 16/F + 16/F**2
    R1 = -b +sqrt(Discr) / 2*a = ((2 + 4/F) + sqrt(16/F + 16/F**2)) / 2
    R2 = -b -sqrt(Discr) / 2*a = ((2 + 4/F) - sqrt(16/F + 16/F**2)) / 2
    """
    F = 1/y -1
    R1 = ((2. + 4./F) + np.sqrt(16./F + 16./F**2)) / 2.
    R2 = ((2. + 4./F) - np.sqrt(16./F + 16./F**2)) / 2.
    return F,R1,R2

# 2d
def gauss2d(xy, amp, x0, y0, sigma_x, sigma_y, base):
    amp, x0, y0, sigma_x, sigma_y, base = float(amp),float(x0),float(y0),float(sigma_x),float(sigma_y),float(base)
    x, y = xy
    a = 1/(2*sigma_x**2)
    b = 1/(2*sigma_y**2)
    inner = a * (x - x0)**2
    inner += b * (y - y0)**2
    return amp * np.exp(-inner) + base

def voight_profile2d(xy,amp,x0,y0,sigma_x,sigma_y,f):
    x, y = xy
    a = 1/(2*sigma_x**2)
    b = 1/(2*sigma_y**2)
    inner = a * (x - x0)**2
    inner += b * (y - y0)**2
    G_nu = amp * np.exp(-inner)
    L_nu = (2*amp/(np.pi*(sigma_x+sigma_y)))/(1+4*inner)
    return f*L_nu + (1-f)*G_nu

def polyfit2d(x_s, x, y, z, order=3):
    ncols = (order + 1)**2
    G = np.zeros((x.size, ncols))
    ij = itertools.product(range(order+1), range(order+1))
    for k, (i,j) in enumerate(ij):
        G[:,k] = (x-x_s)**j * y**i
    m, _, _, _ = np.linalg.lstsq(G, z)
    return m

def convert_m_order2_to_order4(m):
    m_new = np.array(list(m[:3])+[0,0]+list(m[3:6])+[0,0]+list(m[6:])+[0,0,0,0,0,0,0,0,0,0,0,0])
    return m_new

def polyval2d(x_s, x, y, m):
    order = int(np.sqrt(len(m))) - 1
    ij = itertools.product(range(order+1), range(order+1))
    z = np.zeros_like(x)
    for a, (i,j) in zip(m, ij):
        z = z + a * (x-x_s)**j * y**i
    return z


# etalon lines
def etalon_line_params(band):
    if band == "1B":
        alpha_high = 1.4
        alpha_low = -1.5
        thres_e1a=0.3
        min_dist_e1a=5
        sigma0_e1a = 1.5
        thres_e1b=0.2
        min_dist_e1b=6
        sigma0_e1b = 10.
    elif band == '1C':
        alpha_high = 1.45
        alpha_low = -1.5
        thres_e1a=0.1
        min_dist_e1a=9
        sigma0_e1a=1.5
        thres_e1b=0.2
        min_dist_e1b=5
        sigma0_e1b=1.7
    elif band == '2A':
        alpha_high = 2.2
        alpha_low = -1.5
        thres_e1a=0.3
        min_dist_e1a=9
        sigma0_e1a=1.8
        thres_e1b=0.3
        min_dist_e1b=9
        sigma0_e1b=1.8
    elif band == '2B':
        alpha_high = 2.2
        alpha_low = -1.5
        thres_e1a=0.3
        min_dist_e1a=9
        sigma0_e1a=4.
        thres_e1b=0.3
        min_dist_e1b=9
        sigma0_e1b=1.9
    elif band == "2C":
        alpha_high = 2.2
        alpha_low = -1.5
        thres_e1a=0.2
        min_dist_e1a=12
        sigma0_e1a=15.
        thres_e1b=0.2
        min_dist_e1b=9
        sigma0_e1b=1.9

    elif band == "4A":
        alpha_high = 3.8
        alpha_low = -2.8
        thres_e2b=0.2
        min_dist_e2b=18
        sigma0_e2b=3.5

    elif band == "4B":
        alpha_high = 3.8
        alpha_low = -2.8
        thres_e2b=0.3
        min_dist_e2b=25
        sigma0_e2b=3.5

    elif band == "4C":
        alpha_high = 3.8
        alpha_low = -2.8
        thres_e2b=0.2
        min_dist_e2b=32
        sigma0_e2b=3.5

    if band[0] in ['1','2']:
        return alpha_high,alpha_low,thres_e1a,min_dist_e1a,sigma0_e1a,thres_e1b,min_dist_e1b,sigma0_e1b
    elif band[0] in ['4']:
        return alpha_high,alpha_low,thres_e2b,min_dist_e2b,sigma0_e2b

def fit_etalon_lines(x,y,peaks,fit_func='skewed_voight',sigma0=3.5,f0=0.5,a0=0.1):
    # Available fitting functions: 'gauss1d','skewnorm_func','voight_profile','skewed_voight'
    xdata = x.copy()
    xdata[np.isnan(xdata)] = 0.
    # xdata[np.isinf(xdata)] = 0.
    ydata = y.copy()
    ydata[np.isnan(ydata)] = 0.
    # ydata[np.isinf(ydata)] = 0.

    bounds_gauss = ([0,0,0],[np.inf,np.inf,np.inf])
    bounds_skewnorm = ([0,0,0,-np.inf],[np.inf,np.inf,np.inf,np.inf])
    bounds_lorentzian = ([0,0,0],[np.inf,np.inf,np.inf])
    bounds_voight = ([0,0,0,0],[np.inf,np.inf,np.inf,1])
    bounds_skewvoight = ([0,0,0,0,-np.inf],[np.inf,np.inf,np.inf,1,np.inf])

    fitparams = []
    fiterrors = []
    fitting_flag = []
    range_ini = np.full(len(peaks),np.nan) # fit range first position
    range_fin = np.full(len(peaks),np.nan) # fit range last position
    for i in range(len(peaks)):
        if i == len(peaks)-1: N = np.diff(peaks)[i-1]/2 - 1
        else: N = np.diff(peaks)[i]/2

        peak_idx = peaks[i]

        guess_gauss = [ydata[peak_idx],xdata[peak_idx],sigma0]
        guess_skewnorm = guess_gauss+[a0]
        guess_lorentzian = [ydata[peak_idx],xdata[peak_idx],sigma0]
        guess_voight = guess_gauss+[f0]
        guess_skewvoight = guess_gauss+[f0,a0]

        if peak_idx<N:
            range_ini[i] = xdata[0]
            range_fin[i] = xdata[peak_idx+N]
            if fit_func == 'gauss1d':
                popt,pcov = curve_fit(gauss1d_woBaseline,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                fitting_flag.append('gauss1d')
            elif fit_func == 'skewnorm_func':
                try:
                    popt,pcov = curve_fit(skewnorm_func,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_skewnorm,absolute_sigma=True,bounds=bounds_skewnorm)
                    fitting_flag.append('skewnorm_func')
                except RuntimeError:
                    popt,pcov = curve_fit(gauss1d_woBaseline,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                    fitting_flags.append('gauss1d')
            elif fit_func == 'lorentzian_profile':
                popt,pcov = curve_fit(lorentzian_profile,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_lorentzian,absolute_sigma=True,bounds=bounds_lorentzian)
                fitting_flag.append('lorentzian_profile')
            elif fit_func == 'voight_profile':
                popt,pcov = curve_fit(voight_profile,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_voight,absolute_sigma=True,bounds=bounds_voight)
                fitting_flag.append('voight_profile')
            elif fit_func == 'skewed_voight':
                try:
                    popt,pcov = curve_fit(skewed_voight,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_skewvoight,absolute_sigma=True,bounds=bounds_skewvoight)
                    fitting_flag.append('skewed_voight')
                except RuntimeError:
                    try:
                        popt,pcov = curve_fit(voight_profile,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_voight,absolute_sigma=True,bounds=bounds_voight)
                        fitting_flag.append('voight_profile')
                    except RuntimeError:
                        popt,pcov = curve_fit(gauss1d_woBaseline,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                        fitting_flag.append('gauss1d')
        elif peak_idx+N >= len(ydata):
            range_ini[i] = xdata[peak_idx-N]
            range_fin[i] = xdata[-1]
            if fit_func == 'gauss1d':
                popt,pcov = curve_fit(gauss1d_woBaseline,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                fitting_flag.append('gauss1d')
            elif fit_func == 'skewnorm_func':
                try:
                    popt,pcov = curve_fit(skewnorm_func,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_skewnorm,absolute_sigma=True,bounds=bounds_skewnorm)
                    fitting_flag.append('skewnorm_func')
                except RuntimeError:
                    popt,pcov = curve_fit(gauss1d_woBaseline,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                    fitting_flag.append('gauss1d')
            elif fit_func == 'lorentzian_profile':
                popt,pcov = curve_fit(lorentzian_profile,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_lorentzian,absolute_sigma=True,bounds=bounds_lorentzian)
                fitting_flag.append('lorentzian_profile')
            elif fit_func == 'voight_profile':
                popt,pcov = curve_fit(voight_profile,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_voight,absolute_sigma=True,bounds=bounds_voight)
                fitting_flag.append('voight_profile')
            elif fit_func == 'skewed_voight':
                try:
                    popt,pcov = curve_fit(skewed_voight,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_skewvoight,absolute_sigma=True,bounds=bounds_skewvoight)
                    fitting_flag.append('skewed_voight')
                except RuntimeError:
                    try:
                        popt,pcov = curve_fit(voight_profile,xdata[peak_idx-N:],ydata[peak_idx-N:],p0=guess_voight,absolute_sigma=True,bounds=bounds_voight)
                        fitting_flag.append('voight_profile')
                    except RuntimeError:
                        popt,pcov = curve_fit(gauss1d_woBaseline,xdata[0:peak_idx+N],ydata[0:peak_idx+N],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                        fitting_flag.append('gauss1d')
        else:
            range_ini[i] = xdata[peak_idx-N]
            range_fin[i] = xdata[peak_idx+N]
            if fit_func == 'gauss1d':
                popt,pcov = curve_fit(gauss1d_woBaseline,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                fitting_flag.append('gauss1d')
            elif fit_func == 'skewnorm_func':
                try:
                    popt,pcov = curve_fit(skewnorm_func,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_skewnorm,absolute_sigma=True,bounds=bounds_skewnorm)
                    fitting_flag.append('skewnorm_func')
                except RuntimeError:
                    popt,pcov = curve_fit(gauss1d_woBaseline,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_gauss,absolute_sigma=True,bounds=bounds_gauss)
                    fitting_flag.append('gauss1d')
            elif fit_func == 'lorentzian_profile':
                popt,pcov = curve_fit(lorentzian_profile,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_lorentzian,absolute_sigma=True,bounds=bounds_lorentzian)
                fitting_flag.append('gauss1d')
            elif fit_func == 'voight_profile':
                    popt,pcov = curve_fit(voight_profile,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_voight,absolute_sigma=True,bounds=bounds_voight)
                    fitting_flag.append('voight_profile')
            elif fit_func == 'skewed_voight':
                try:
                    popt,pcov = curve_fit(skewed_voight,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_skewvoight,absolute_sigma=True,bounds=bounds_skewvoight)
                    fitting_flag.append('skewed_voight')
                except RuntimeError:
                    try:
                        popt,pcov = curve_fit(voight_profile,xdata[peak_idx-N:peak_idx+N],ydata[peak_idx-N:peak_idx+N],p0=guess_voight,absolute_sigma=True,bounds=bounds_voight)
                        fitting_flag.append('voight_profile')
                    except RuntimeError:
                        popt = guess_gauss
                        pcov = pcov
                        fitting_flag.append('gauss1d')
                except ValueError:
                    try:
                        sel = np.nonzero(ydata[peak_idx-N:peak_idx+N])
                        popt,pcov = curve_fit(skewed_voight,xdata[peak_idx-N:peak_idx+N][sel],ydata[peak_idx-N:peak_idx+N][sel],p0=guess_skewvoight,absolute_sigma=True,bounds=bounds_skewvoight)
                        fitting_flag.append('skewed_voight')
                    except RuntimeError:
                        popt = guess_gauss
                        pcov = pcov
                        fitting_flag.append('gauss1d')
        fitparams.append(popt)
        fiterrors.append(pcov)

    return fitparams,fiterrors,fitting_flag,range_ini,range_fin

def get_amplitude(fitparams,fitting_flag):
    amplitude = np.full(len(fitparams),np.nan)
    for i in range(len(fitparams)):
        if fitting_flag[i] == 'gauss1d':
            amplitude[i] = fitparams[i][0]
        elif fitting_flag[i] == 'skewnorm_func':
            plotx = np.linspace(fitparams[i][1]-1*fitparams[i][2],fitparams[i][1]+1*fitparams[i][2],500)
            ploty = skewnorm_func(plotx,*fitparams[i])
            amplitude[i] = np.max(ploty)
        elif fitting_flag[i] == 'lorentzian_profile':
            amplitude[i] = fitparams[i][0]
        elif fitting_flag[i] == 'voight_profile':
            amplitude[i] = fitparams[i][0]
        elif fitting_flag[i] == 'skewed_voight':
            plotx = np.linspace(fitparams[i][1]-1*fitparams[i][2],fitparams[i][1]+1*fitparams[i][2],500)
            ploty = skewed_voight(plotx,*fitparams[i])
            amplitude[i] = np.max(ploty)
    return amplitude

def get_linecenter(fitparams,fitting_flag):
    linecenter = np.full(len(fitparams),np.nan)
    for i in range(len(fitparams)):
        if fitting_flag[i] == 'gauss1d':
            linecenter[i] = fitparams[i][1]
        elif fitting_flag[i] == 'skewnorm_func':
            plotx = np.linspace(fitparams[i][1]-1*fitparams[i][2],fitparams[i][1]+1*fitparams[i][2],500)
            ploty = skewnorm_func(plotx,*fitparams[i])
            linecenter[i] = plotx[np.argmax(ploty)]
        elif fitting_flag[i] == 'lorentzian_profile':
            linecenter[i] = fitparams[i][1]
        elif fitting_flag[i] == 'voight_profile':
            linecenter[i] = fitparams[i][1]
        elif fitting_flag[i] == 'skewed_voight':
            plotx = np.linspace(fitparams[i][1]-1*fitparams[i][2],fitparams[i][1]+1*fitparams[i][2],500)
            ploty = skewed_voight(plotx,*fitparams[i])
            linecenter[i] = plotx[np.argmax(ploty)]
    return linecenter

def get_FWHM(fitparams,fitting_flag):
    fwhm = np.full(len(fitparams),np.nan)
    for i in range(len(fitparams)):
        if fitting_flag[i] == 'gauss1d':
            fwhm[i] = 2.355*fitparams[i][2]
        elif fitting_flag[i] == 'skewnorm_func':
            plotx = np.linspace(fitparams[i][1]-3*fitparams[i][2],fitparams[i][1]+3*fitparams[i][2],500)
            ploty = skewnorm_func(plotx,*fitparams[i])
            fwhm_idxs = np.abs(ploty-ploty.max()/2.).argsort()[:2]
            fwhm[i] = np.abs(plotx[fwhm_idxs[1]]-plotx[fwhm_idxs[0]])
        elif fitting_flag[i] == 'lorentzian_profile':
            plotx = np.linspace(fitparams[i][1]-3*fitparams[i][2],fitparams[i][1]+3*fitparams[i][2],500)
            ploty = lorentzian_profile(plotx,*fitparams[i])
            fwhm_idxs = np.abs(ploty-ploty.max()/2.).argsort()[:2]
            fwhm[i] = np.abs(plotx[fwhm_idxs[1]]-plotx[fwhm_idxs[0]])
        elif fitting_flag[i] == 'voight_profile':
            plotx = np.linspace(fitparams[i][1]-3*fitparams[i][2],fitparams[i][1]+3*fitparams[i][2],500)
            ploty = voight_profile(plotx,*fitparams[i])
            fwhm_idxs = np.abs(ploty-ploty.max()/2.).argsort()[:2]
            fwhm[i] = np.abs(plotx[fwhm_idxs[1]]-plotx[fwhm_idxs[0]])
        elif fitting_flag[i] == 'skewed_voight':
            plotx = np.linspace(fitparams[i][1]-3*fitparams[i][2],fitparams[i][1]+3*fitparams[i][2],500)
            ploty = skewed_voight(plotx,*fitparams[i])
            fwhm_idxs = np.abs(ploty-ploty.max()/2.).argsort()[:2]
            fwhm[i] = np.abs(plotx[fwhm_idxs[1]]-plotx[fwhm_idxs[0]])
    return fwhm

def get_skewness(fitparams,fitting_flag):
    skewparam = np.full(len(fitparams),np.nan)
    for i in range(len(fitparams)):
        if fitting_flag[i] == 'gauss1d':
            skewparam[i] = 0.
        elif fitting_flag[i] == 'skewnorm_func':
            skewparam[i] = fitparams[i][3]
        elif fitting_flag[i] == 'lorentzian_profile':
            skewparam[i] = 0.
        elif fitting_flag[i] == 'voight_profile':
            skewparam[i] = 0.
        elif fitting_flag[i] == 'skewed_voight':
            skewparam[i] = fitparams[i][4]
    return skewparam

def sum_etalon_lines(xdata,fitparams,fitting_flag):
    summed_signal = np.zeros(len(xdata))
    for i in range(len(fitparams)):
        if fitting_flag[i] == 'gauss1d':
            signal = gauss1d_woBaseline(xdata,*fitparams[i])
        elif fitting_flag[i] == 'skewnorm_func':
            signal = skewnorm_func(xdata,*fitparams[i])
        elif fitting_flag[i] == 'lorentzian_profile':
            signal = lorentzian_profile(xdata,*fitparams[i])
        elif fitting_flag[i] == 'voight_profile':
            signal = voight_profile(xdata,*fitparams[i])
        elif fitting_flag[i] == 'skewed_voight':
            signal = skewed_voight(xdata,*fitparams[i])
        summed_signal+= signal
    return summed_signal


def plot_etalon_fit(fitparams,fitting_flag):
    for i in range(len(fitparams)):
        if fitting_flag[i] == 'gauss1d':
            plotx = np.linspace(fitparams[i][1]-10*fitparams[i][2],fitparams[i][1]+10*fitparams[i][2],100)
            ploty = gauss1d_woBaseline(plotx,*fitparams[i])
        elif fitting_flag[i] == 'skewnorm_func':
            plotx = np.linspace(fitparams[i][1]-10*fitparams[i][2],fitparams[i][1]+10*fitparams[i][2],100)
            ploty = skewnorm_func(plotx,*fitparams[i])
        elif fitting_flag[i] == 'lorentzian_profile':
            plotx = np.linspace(fitparams[i][1]-10*fitparams[i][2],fitparams[i][1]+10*fitparams[i][2],500)
            ploty = lorentzian_profile(plotx,*fitparams[i])
        elif fitting_flag[i] == 'voight_profile':
            plotx = np.linspace(fitparams[i][1]-10*fitparams[i][2],fitparams[i][1]+10*fitparams[i][2],500)
            ploty = voight_profile(plotx,*fitparams[i])
        elif fitting_flag[i] == 'skewed_voight':
            plotx = np.linspace(fitparams[i][1]-10*fitparams[i][2],fitparams[i][1]+10*fitparams[i][2],500)
            ploty = skewed_voight(plotx,*fitparams[i])
        plt.plot(plotx,ploty,'r')
    plt.plot(plotx,ploty,'r',label='fitted lines')

#--normalize fringes
def norm_fringe(sci_data,thres=0,min_dist=2,k=3,ext=3):
    # determine peaks
    sci_data_noNaN = sci_data.copy()
    sci_data_noNaN[np.isnan(sci_data_noNaN)] = 0.
    peaks = find_peaks(sci_data_noNaN,thres=thres,min_dist=min_dist)
    # determine fringe continuum
    if len(peaks)!=0:
        # omit peak at boundary of array (false positive)
        if peaks[0] == np.nonzero(sci_data_noNaN)[0][0]:
            peaks = np.delete(peaks,0)

        if len(peaks)>1:
            arr_interpolator = scp_interpolate.InterpolatedUnivariateSpline(peaks,sci_data_noNaN[peaks],k=k,ext=ext)
            sci_data_profile = arr_interpolator(range(len(sci_data_noNaN)))
        elif len(peaks)==1:
            sci_data_profile = sci_data_noNaN[peaks]*np.ones(len(sci_data_noNaN))
        elif len(peaks)==0:
            sci_data_profile = np.zeros(len(sci_data))

        return sci_data_noNaN,peaks,sci_data_profile

    else:
        return sci_data_noNaN,peaks,np.zeros(len(sci_data))

def cleanRD(R,D):
    # take care of numerical instabilities
    cleanR = R.copy()
    cleanD = D.copy()
    numerics = [] # list of indexes were "cleaning" required

    # reflectivity
    #--have not found exceptions yet

    # optical thickness
    diffD = np.diff(cleanD)
    offset = np.mean(np.abs(diffD)[np.where(np.abs(diffD)*10000.>1)[0]])
    while len(np.where(np.abs(diffD)*10000.>1)[0] != 0):
        clean_idx_pos = np.where(diffD*10000.>1)[0]
        numerics.extend(clean_idx_pos+1)
        cleanD[clean_idx_pos+1] -= offset
        diffD = np.diff(cleanD)

    numerics = np.sort(np.unique(np.array(numerics)))
    return cleanR,cleanD,numerics

#--find
def find_nearest(array,value):
    return np.abs(array-value).argmin()

def find_peaks(ydata, thres=0.3, min_dist=1):
    """Peak detection routine.

    Finds the numeric index of the peaks in *y* by taking its first order difference. By using
    *thres* and *min_dist* parameters, it is possible to reduce the number of
    detected peaks. *y* must be signed.

    Parameters
    ----------
    y : ndarray (signed)
        1D amplitude ydata to search for peaks.
    thres : float between [0., 1.]
        Normalized threshold. Only the peaks with amplitude higher than the
        threshold will be detected.
    min_dist : int
        Minimum distance between each detected peak. The peak with the highest
        amplitude is preferred to satisfy this constraint.

    Returns
    -------
    ndarray
        Array containing the numeric indexes of the peaks that were detected
    """
    if isinstance(ydata, np.ndarray) and np.issubdtype(ydata.dtype, np.unsignedinteger):
        raise ValueError("ydata must be signed")

    y = ydata.copy()
    y[np.isnan(y)] = 0

    thres = thres * (np.max(y) - np.min(y)) + np.min(y)
    min_dist = int(min_dist)

    # compute first order difference
    dy = np.diff(y)

    # propagate left and right values successively to fill all plateau pixels (0-value)
    zeros,=np.where(dy == 0)

    while len(zeros):
        # add pixels 2 by 2 to propagate left and right value onto the zero-value pixel
        zerosr = np.hstack([dy[1:], 0.])
        zerosl = np.hstack([0., dy[:-1]])

        # replace 0 with right value if non zero
        dy[zeros]=zerosr[zeros]
        zeros,=np.where(dy == 0)

        # replace 0 with left value if non zero
        dy[zeros]=zerosl[zeros]
        zeros,=np.where(dy == 0)

    # find the peaks by using the first order difference
    peaks = np.where((np.hstack([dy, 0.]) < 0.)
                     & (np.hstack([0., dy]) > 0.)
                     & (y > thres))[0]

    if peaks.size > 1 and min_dist > 1:
        highest = peaks[np.argsort(y[peaks])][::-1]
        rem = np.ones(y.size, dtype=bool)
        rem[peaks] = False

        for peak in highest:
            if not rem[peak]:
                sl = slice(max(0, peak - min_dist), peak + min_dist + 1)
                rem[sl] = True
                rem[peak] = False

        peaks = np.arange(y.size)[~rem]

    return peaks

def detpixel_trace(band,d2cMaps,sliceID=None,alpha_pos=None):
    # detector dimensions
    det_dims=(1024,1032)
    # initialize placeholders
    ypos,xpos = np.arange(det_dims[0]),np.zeros(det_dims[0])
    slice_img,alpha_img = [np.full(det_dims,0.) for j in range(2)]
    # create pixel masks
    sel_pix = (d2cMaps['sliceMap'] == 100*int(band[0])+sliceID) # select pixels with correct slice number
    slice_img[sel_pix] = d2cMaps['sliceMap'][sel_pix]           # image containing single slice
    alpha_img[sel_pix] = d2cMaps['alphaMap'][sel_pix]           # image containing alpha positions in single slice

    # find pixel trace
    for row in ypos:
        if band[0] in ['1','4']:
            try:xpos[row] = np.argmin(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_pos)
            except ValueError:
                """Band 1C has missing pixel values (zeros instead of valid values)"""
                continue
        elif band[0] in ['2','3']:
            xpos[row] = np.argmax(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_pos)
    xpos = xpos.astype(int)

    return ypos,xpos

def detpixel_trace_compactsource(sci_img,band,d2cMaps,offset_slice=0,verbose=False):
    # detector dimensions
    det_dims  = (1024,1032)
    nslices   = d2cMaps['nslices']
    sliceMap  = d2cMaps['sliceMap']
    ypos,xpos = np.arange(det_dims[0]),np.zeros(det_dims[0])

    sum_signals = np.zeros(nslices)
    for islice in xrange(1+nslices):
        sum_signals[islice-1] = sci_img[(sliceMap == 100*int(band[0])+islice) & (~np.isnan(sci_img))].sum()
    source_center_slice = np.argmax(sum_signals)+1
    if verbose==True:
        print 'Source center slice ID: {}'.format(source_center_slice)

    signal_img = np.full(det_dims,0.)
    sel_pix = (sliceMap == 100*int(band[0])+source_center_slice+offset_slice)
    signal_img[sel_pix] = sci_img[sel_pix]
    for row in ypos:
        xpos[row] = np.argmax(signal_img[row,:])
    xpos = xpos.astype(int)
    return ypos,xpos

def slice_alphapositions(band,d2cMaps,sliceID=None):
    # find how many alpha positions fill an entire slice
    det_dims = (1024,1032)
    MRS_alphapix = {'1':0.196,'2':0.196,'3':0.245,'4':0.273} # arcseconds
    MRS_FWHM = {'1':2.16*MRS_alphapix['1'],'2':3.30*MRS_alphapix['2'],
                '3':4.04*MRS_alphapix['3'],'4':5.56*MRS_alphapix['4']} # MRS PSF
    mrs_fwhm  = MRS_FWHM[band[0]]

    ypos = np.arange(det_dims[0])
    slice_img,alpha_img,alpha_img2 = np.full(det_dims,0.),np.full(det_dims,0.),np.full(det_dims,0.)
    sel_pix = (d2cMaps['sliceMap'] == 100*int(band[0])+sliceID) # select pixels with correct slice number
    slice_img[sel_pix] = d2cMaps['sliceMap'][sel_pix]           # image containing single slice
    alpha_img[sel_pix] = d2cMaps['alphaMap'][sel_pix]           # image containing alpha positions in single slice

    alpha_pos = alpha_img[(alpha_img!=0)].min() # arcsec
    step = mrs_fwhm/2.
    increment = mrs_fwhm/40.
    while (alpha_img2-alpha_img).any() != 0:
        xpos = np.zeros(len(ypos))
        for row in ypos:
            if band[0] in ['1','4']:
                xpos[row] = np.argmin(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_pos)
            elif band[0] in ['2','3']:
                xpos[row] = np.argmax(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_pos)
        xpos = xpos.astype(int)

        # Spectrum origination on detector
        alpha_img2[ypos,xpos] = d2cMaps['alphaMap'][ypos,xpos]
        alpha_pos += step

        if (alpha_pos > alpha_img[(alpha_img!=0)].max() + 2*mrs_fwhm):
            alpha_img2 = np.full(det_dims,0.)
            alpha_pos = alpha_img[(alpha_img!=0)].min()
            step -= increment

        if step <= 0:
            alpha_img2 = np.full(det_dims,0.)
            alpha_pos = alpha_img[(alpha_img!=0)].min()
            step = 0.2
            increment /= 2.

    alpha_positions = np.arange(alpha_img[(alpha_img!=0)].min(),alpha_pos,step)

    rmv_positions = []
    for j in range(len(alpha_positions)-1):
        xpos1 = np.zeros(len(ypos))
        for row in ypos:
            if band[0] in ['1','3']:
                xpos1[row] = np.argmin(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_positions[j])
            elif band[0] in ['2','4']:
                xpos1[row] = np.argmax(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_positions[j])

        xpos2 = np.zeros(len(ypos))
        for row in ypos:
            if band[0] in ['1','3']:
                xpos2[row] = np.argmin(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_positions[j+1])
            elif band[0] in ['2','4']:
                xpos2[row] = np.argmax(alpha_img[row,:])+find_nearest(alpha_img[row,:][(slice_img[row,:]!=0)],alpha_positions[j+1])

        if np.array_equal(xpos1, xpos2):
            # print j
            rmv_positions.append(j+1)
    new_alpha_positions = np.delete(alpha_positions,rmv_positions)

    return new_alpha_positions

#--slice mapping
def slice_mapping(band,signal,signal_error,sliceMap_0percent,margin=5,stop_criterion = 5.,transm_criterion=0.9,verbose=False):
    import pandas as pd
    # Recommended margin value for channel 1 and 2 is 5 pixels.
    # Recommended margin value for channel 3 and 4 is 7 pixels.

    # ids of the individual slices
    sliceid1=[111,121,110,120,109,119,108,118,107,117,106,116,105,115,104,114,103,113,102,112,101]
    sliceid2=[201,210,202,211,203,212,204,213,205,214,206,215,207,216,208,217,209]
    sliceid3=[316,308,315,307,314,306,313,305,312,304,311,303,310,302,309,301]
    sliceid4=[412,406,411,405,410,404,409,403,408,402,407,401]

    if band[0]   == '1': sliceid = sliceid1
    elif band[0] == '2': sliceid = sliceid2
    elif band[0] == '3': sliceid = sliceid3
    elif band[0] == '4': sliceid = sliceid4

    # initialize placeholders
    transm_img        = np.zeros((1024,1032))
    new_sliceMap      = np.zeros((1024,1032))
    new_sliceMap_poly = np.zeros((1024,1032))

    # interpolate NaN values
    # take care of any remaining NaN values present in the signal of channel 4
    if band[0] =='4':axis = 1
    else: axis = 0

    signal = pd.DataFrame(signal)
    interp_signal = signal.interpolate(method='nearest',axis=axis).as_matrix()

    signal_error = pd.DataFrame(signal_error)
    interp_signal_error = signal_error.interpolate(method='nearest',axis=axis).as_matrix()

    # compute new slice map
    for islice in sliceid:
        if verbose is True:
            print 'Slice {}'.format(islice)
        for row in range(1,1023):
            lower = np.where(sliceMap_0percent[row,:] == islice)[0][0]
            upper = np.where(sliceMap_0percent[row,:] == islice)[0][-1]+2

            xdata = np.arange(1032)[lower+margin:upper-margin]
            ydata = interp_signal[row,lower+margin:upper-margin]
            sigma = interp_signal_error[row,lower+margin:upper-margin]

            n_poly   = 1
            residual_change = 100.
            residual_changes = [residual_change]
            counter = 0
            flag    = 0
            while residual_change > stop_criterion:
                counter += 1
                popt_1     = np.polyfit(xdata,ydata,n_poly,w=1/sigma)
                poly_1     = np.poly1d(popt_1)
                residual_1 = (ydata-poly_1(xdata))**2

                popt_2     = np.polyfit(xdata,ydata,n_poly+1,w=1/sigma)
                poly_2     = np.poly1d(popt_2)
                residual_2 = (ydata-poly_2(xdata))**2

                residual_change = np.abs((residual_2.sum()-residual_1.sum())/residual_1.sum())*100.
                residual_changes.append(residual_change)

                n_poly+= 1

                if residual_changes[counter]>residual_changes[counter-1]:
                    flag = 1
                    break

                if n_poly == 5:
                    break

            if n_poly == 2:
                # first iteration gives good enough fit
                n_polynomial   = 1
                popt     = popt_1
                poly     = poly_1
                residual = residual_1
            else:
                # n+1 iteration gives best fit
                n_polynomial   = n_poly-1
                popt     = popt_2
                poly     = poly_2
                residual = residual_2
            if flag == 1:
                n_polynomial   = n_poly-1
                popt     = popt_1
                poly     = poly_1
                residual = residual_1

            transmission = interp_signal[row,lower:upper]/poly(np.arange(1032)[lower:upper] )
            transm_img[row,lower:upper] = transmission

            min_idx = np.where(transmission>transm_criterion)[0][0]
            max_idx = np.where(transmission>transm_criterion)[0][-1]

            new_sliceMap[row,lower+min_idx+1:lower+max_idx] = islice
    new_sliceMap[0,:] = new_sliceMap[1,:]
    new_sliceMap[1023,:] = new_sliceMap[1022,:]

    # fit polynomial solution to slice edges
    edge_pixels_left,edge_pixels_right = {},{}
    for islice in sliceid:
        edge_pixels_left[str(islice)],edge_pixels_right[str(islice)] = np.zeros(1024),np.zeros(1024)
        for row in range(1024):
            edge_pixels_left[str(islice)][row]  = np.where(new_sliceMap[row,:] == islice)[0][0]
            edge_pixels_right[str(islice)][row] = np.where(new_sliceMap[row,:] == islice)[0][-1]

        # shifts of more than two pixels are rejected
        for row in range(1,1024):
            if (np.abs(edge_pixels_left[str(islice)][row]-edge_pixels_left[str(islice)][row-1]) ==2):
                edge_pixels_left[str(islice)][row-1] = np.nan

            if (np.abs(edge_pixels_right[str(islice)][row]-edge_pixels_right[str(islice)][row-1]) ==2):
                edge_pixels_right[str(islice)][row-1] = np.nan

        sel_left  = ~np.isnan(edge_pixels_left[str(islice)])
        popt_left = np.polyfit(np.arange(1024)[sel_left],edge_pixels_left[str(islice)][sel_left],4)
        poly_left = np.poly1d(popt_left)

        sel_right  = ~np.isnan(edge_pixels_right[str(islice)])
        popt_right = np.polyfit(np.arange(1024)[sel_right],edge_pixels_right[str(islice)][sel_right],4)
        poly_right = np.poly1d(popt_right)

        for row in range(1024):
            assert np.around(poly_left(np.arange(1024))[row])<=np.around(poly_right(np.arange(1024))[row])+2, 'Something went wrong in the polynomial fitting'
            new_sliceMap_poly[row,np.around(poly_left(np.arange(1024))[row]):np.around(poly_right(np.arange(1024))[row])+2] = islice

    return transm_img,new_sliceMap,new_sliceMap_poly

#--plot
def plot_point_source_centroiding(band,sci_img,d2cMaps,spec_grid=None,centroid=None,ibin=None,data=None):
    # distortion maps
    sliceMap  = d2cMaps['sliceMap']
    lambdaMap = d2cMaps['lambdaMap']
    alphaMap  = d2cMaps['alphaMap']
    betaMap   = d2cMaps['betaMap']
    nslices   = d2cMaps['nslices']
    MRS_alphapix = {'1':0.196,'2':0.196,'3':0.245,'4':0.273} # arcseconds
    MRS_FWHM = {'1':2.16*MRS_alphapix['1'],'2':3.30*MRS_alphapix['2'],
                '3':4.04*MRS_alphapix['3'],'4':5.56*MRS_alphapix['4']} # MRS PSF
    mrs_fwhm  = MRS_FWHM[band[0]]
    unique_betas = np.sort(np.unique(betaMap[(sliceMap>100*int(band[0])) & (sliceMap<100*(int(band[0])+1))]))
    fov_lims  = [alphaMap[np.nonzero(lambdaMap)].min(),alphaMap[np.nonzero(lambdaMap)].max()]
    lambcens,lambfwhms = spec_grid[0],spec_grid[1]
    sign_amp,alpha_centers,beta_centers,sigma_alpha,sigma_beta,sign_bkg = centroid

    # across-slice center:
    sum_signals = np.zeros(nslices)
    for islice in xrange(1+nslices):
        sum_signals[islice-1] = sci_img[(sliceMap == 100*int(band[0])+islice) & (~np.isnan(sci_img))].sum()
    source_center_slice = np.argmax(sum_signals)+1

    # along-slice center:
    det_dims = (1024,1032)
    img = np.full(det_dims,0.)
    sel = (sliceMap == 100*int(band[0])+source_center_slice)
    img[sel]  = sci_img[sel]

    first_nonzero_row = 0
    while all(img[first_nonzero_row,:][~np.isnan(img[first_nonzero_row,:])] == 0.): first_nonzero_row+=1
    source_center_alpha = alphaMap[first_nonzero_row,img[first_nonzero_row,:].argmax()]

    # plot centroiding process in a single bin
    fig,axs = plt.subplots(2,1,figsize=(12,10))
    coords = np.where((sliceMap == 100*int(band[0])+source_center_slice) & (np.abs(lambdaMap-lambcens[ibin])<=lambfwhms[ibin]/2.) & (~np.isnan(sci_img)))
    popt,pcov = curve_fit(gauss1d_wBaseline, alphaMap[coords], sci_img[coords], p0=[sci_img[coords].max(),alpha_centers[ibin],mrs_fwhm/2.355,0.],method='lm')
    testx = np.linspace(alphaMap[coords].min(),alphaMap[coords].max(),1000)
    testy = gauss1d_wBaseline(testx,*popt)

    axs[0].plot(alphaMap[coords], sci_img[coords],'bo',label='along-slice data')
    axs[0].plot(testx, testy,'r',label='1D Gauss fit')
    axs[0].plot(testx,gauss1d_wBaseline(testx,popt[0],popt[1],0.31*(lambcens[ibin]/8.)/2.355,popt[3]),alpha=0.4,label='diffraction-limited PSF')
    axs[0].vlines([alpha_centers[ibin]-3*sigma_alpha[ibin].max(),alpha_centers[ibin]+3*sigma_alpha[ibin].max()],testy.min(),testy.max(),label=r'3$\sigma$ lines')
    axs[0].set_xlim(fov_lims[0],fov_lims[1])
    axs[0].tick_params(axis='both',labelsize=20)
    axs[0].set_xlabel(r'Along-slice direction $\alpha$ [arcsec]',fontsize=20)
    if data == 'slope': axs[0].set_ylabel('Signal [DN/sec]',fontsize=20)
    elif data == 'divphotom': axs[0].set_ylabel('Signal [mJy/pix]',fontsize=20)
    elif data == 'surfbright': axs[0].set_ylabel(r'Signal [mJy/arcsec$^2$]',fontsize=20)
    axs[0].legend(loc='best',fontsize=14)

    # across-slice source centroiding
    sel = (np.abs(lambdaMap-lambcens[ibin])<=lambfwhms[ibin]/2.) & (~np.isnan(sci_img))
    signals = np.zeros(nslices)
    for islice in range(1,1+nslices):
        signals[islice-1] = sci_img[(sliceMap == 100*int(band[0])+islice) & sel][np.abs(alphaMap[(sliceMap == 100*int(band[0])+islice) & sel]-popt[1]).argmin()]
    popt,pcov = curve_fit(gauss1d_wBaseline, unique_betas, signals, p0=[signals.max(),beta_centers[ibin],mrs_fwhm/2.355,0],method='lm')
    testx = np.linspace(unique_betas.min(),unique_betas.max(),1000)
    testy = gauss1d_wBaseline(testx,*popt)

    axs[1].plot(unique_betas, signals,'bo',label='across-slice data')
    axs[1].plot(testx, testy,'r',label='1D Gauss fit')
    axs[1].plot(testx,gauss1d_wBaseline(testx,popt[0],popt[1],0.31*(lambcens[ibin]/8.)/2.355,popt[3]),alpha=0.4,label='diffraction-limited PSF')
    axs[1].vlines([beta_centers[ibin]-3*sigma_beta[ibin].max(),beta_centers[ibin]+3*sigma_beta[ibin].max()],testy.min(),testy.max(),label=r'3$\sigma$ lines')
    axs[1].tick_params(axis='both',labelsize=20)
    axs[1].set_xlabel(r'Across-slice direction $\beta$ [arcsec]',fontsize=20)
    if data == 'slope': axs[1].set_ylabel('Signal [DN/sec]',fontsize=20)
    elif data == 'divphotom': axs[1].set_ylabel('Signal [mJy/pix]',fontsize=20)
    elif data == 'surfbright': axs[1].set_ylabel(r'Signal [mJy/arcsec$^2$]',fontsize=20)
    axs[1].legend(loc='best',fontsize=14)
    plt.suptitle('1D Gaussian Fitting',fontsize=20)
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    # initial guess for fitting, informed by previous centroiding steps
    amp,alpha0,beta0  = sign_amp[ibin],alpha_centers[ibin],beta_centers[ibin]
    sigma_alpha0, sigma_beta0 = sigma_alpha[ibin], sigma_beta[ibin]
    base = 0.
    guess = [amp, alpha0, beta0, sigma_alpha0, sigma_beta0, base]
    bounds = ([0,-np.inf,-np.inf,0,0,-np.inf],[np.inf,np.inf,np.inf,np.inf,np.inf,np.inf])

    # data to fit
    coords = (np.abs(lambdaMap-lambcens[ibin])<lambfwhms[ibin]/2.)
    alphas, betas, zobs   = alphaMap[coords],betaMap[coords],sci_img[coords]
    alphabetas = np.array([alphas,betas])

    # projected grid
    betai, alphai = np.mgrid[unique_betas.min():unique_betas.max():300j, fov_lims[0]:fov_lims[1]:300j]
    alphabetai = np.vstack([alphai.ravel(), betai.ravel()])

    zpred = gauss2d(alphabetai, *guess)
    zpred.shape = alphai.shape

    # plot result
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(alphas, betas, c=zobs, s=50)
    im = ax.imshow(zpred, extent=[alphai.min(), alphai.max(), betai.max(), betai.min()],
                   aspect='auto')
    cbar = fig.colorbar(im)
    cbar.ax.tick_params(labelsize=14)
    if data == 'slope': cbar.set_label(r'Signal [DN/sec]', labelpad=30,rotation=270,fontsize=16)
    elif data == 'divphotom': cbar.set_label(r'Signal [mJy/pix]', labelpad=30,rotation=270,fontsize=16)
    elif data == 'surfbright': cbar.set_label(r'Signal [mJy/arcsec$^2$]', labelpad=30,rotation=270,fontsize=16)
    plt.xlabel(r'Along-slice direction $\alpha$ [arcsec]',fontsize=16)
    plt.ylabel(r'Across-slice direction $\beta$ [arcsec]',fontsize=16)
    plt.tick_params(axis='both',labelsize=20)
    ax.invert_yaxis()
    plt.suptitle('2D Gaussian Fitting',fontsize=20)
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    # make wireframe plot
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure(figsize=(10,7))
    ax = fig.gca(projection='3d')
    ax.scatter(alphas, betas, zobs)
    ax.plot_wireframe(alphai,betai, zpred,color='r',alpha=0.15)
    ax.set_xlim(fov_lims[0],fov_lims[1])
    ax.set_ylim(unique_betas.min(),unique_betas.max())
    ax.set_zlim(0)
    ax.set_xlabel(r'Along-slice direction $\alpha$ [arcsec]',fontsize=16)
    ax.set_ylabel(r'Across-slice direction $\beta$ [arcsec]',fontsize=16)
    if data == 'slope': ax.set_zlabel('Signal [DN/sec]',fontsize=16)
    elif data == 'divphotom': ax.set_zlabel(r'Signal [mJy/pix]',fontsize=16)
    if data == 'surfbright': ax.set_zlabel(r'Signal [mJy/arcsec$^2$]',fontsize=16)
    ax.text2D(0.14, 0.85, r'$\lambda =$'+str(round(lambcens[ibin],2))+'um', transform=ax.transAxes,fontsize=20)
    ax.tick_params(axis='both',labelsize=10)
    plt.suptitle('Wireframe plot',fontsize=20)
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    plt.show()

def tick_function(X):
    # for plotting wavelengths and wavenumbers on the same plot (two x-axes)
    V = 10000./X
    return ["%.2f" % z for z in V]

#--optical coefficients
def indexOfRefractionZnS(wav):
    """ Index of refraction of Zinc Sulfide (AR coatings) according to M. R. Querry. "Optical constants of minerals and other materials from the millimeter to the ultraviolet"
    Data source: https://refractiveindex.info """
    wav_data,n_data,k_data = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/refractive_index_ZnS.txt',usecols=(0,1,2),delimiter=',',unpack=True)

    interp_n  = scp_interpolate.interp1d(wav_data,n_data)
    interp_k  = scp_interpolate.interp1d(wav_data,k_data)

    try:
        n,k = [],[]
        for wvl in wav:
            n.append(interp_n(wvl))
            k.append(interp_k(wvl))
        n,k = np.array(n),np.array(k)
    except TypeError:
        n,k = interp_n(wav),interp_k(wav)

    return n+k*1j

def indexOfRefractionSi(wav):
    # Salzberg and Villa 1957: n 1.36-11 microns
    wav2= wav**2
    C1 = 10.6684293
    C2 = (0.301516485)**2
    C3 = 0.003043475
    C4 = (1.13475115)**2
    C5 = 1.54133408
    C6 = (1104.0)**2
    n = np.sqrt( 1 + C1*wav2/(wav2-C2) + C3*wav2/(wav2-C4) + C5*wav2/(wav2-C6) )
    wav0 = (10.6)**2
    n_10 = np.sqrt( 1 + C1*wav0/(wav0-C2) + C3*wav0/(wav0-C4) + C5*wav0/(wav0-C6) )
    n = n * 3.38966 / n_10

    # Chandler-Horowitz and Amirtharaj 2005
    n = np.sqrt(11.67316 + (1/wav**2) + (0.004482633/(wav**2 - 1.108205**2)) )

    wav_data,k_data = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/extinction_coeff_silicon.txt',usecols=(0,1),delimiter=',',unpack=True)
    interp_k  = scp_interpolate.interp1d(wav_data,k_data)

    try:
        k = []
        for wvl in wav:
            if (wvl <wav_data[0]) or (wvl >wav_data[-1]):
                k.append(0)
            else:
                k.append(interp_k(wvl))
        k = np.array(k)
    except TypeError:
        if (wav <wav_data[0]) or (wav >wav_data[-1]):
            k = 0
        else:
            k = interp_k(wav)

    return n+k*1j

def indexOfRefractionSiAs(wav):
    # real component of index of refraction (assume refractive index of pure Silicon, due to lack of data)
    n = indexOfRefractionSi(wav)
    # imaginary component of index of refraction (data from "qe_report_new_rev.pdf", sent to me by George Rieke)
    absorption_coeff = 102.*(wav/7.)**2 # [cm-1]
    k = absorption_coeff*wav*1e-4/(4*np.pi)
    # or directly
    k = 5.69*10**-3 * (wav/7.)**3
    return n+k*1j

def indexOfRefractionAl(wav):
    wav_data,n_data,k_data = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/extinction_coeff_aluminium.txt',usecols=(0,1,2),delimiter=',',unpack=True)
    interp_n  = scp_interpolate.interp1d(wav_data,n_data)
    interp_k  = scp_interpolate.interp1d(wav_data,k_data)
    try:
        n,k = [],[]
        for wvl in wav:
            n.append(interp_n(wvl))
            k.append(interp_k(wvl))
        n,k = np.array(n),np.array(k)
    except TypeError:
        n,k = interp_n(wav),interp_k(wav)

    return n +k*1j

def indexOfRefractionTransCont(wav):
    # Index of refraction of transparent contact
    n = indexOfRefractionSi(wav)-0.1
    k = 0.
    return n+k*1j

def indexOfRefractionCdTe(wav):
    """ Index of refraction of Cadmium Telluride (dichroic)
    Data source: refractiveindex.info"""
    # wav is wavelength in microns
    return np.sqrt(1 + (6.0599879*wav**2)/(wav**2 - 0.1004272) + (3.7564378*wav**2)/(wav**2 - 6138.789))

def indexOfRefractionAl2O3(wav):
    """ Index of refraction of Aluminium Oxide (front surface of BiB detector (after buried layer and front contact, as seen in Woods et al. 2011))
    Data source: https://refractiveindex.info """
    wav_data,n_data,k_data = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/opticalconstants_Al2O3.txt',usecols=(0,1,2),delimiter=',',unpack=True)

    interp_n  = scp_interpolate.interp1d(wav_data,n_data)
    interp_k  = scp_interpolate.interp1d(wav_data,k_data)

    try:
        n,k = [],[]
        for wvl in wav:
            n.append(interp_n(wvl))
            k.append(interp_k(wvl))
        n,k = np.array(n),np.array(k)
    except TypeError:
        n,k = interp_n(wav),interp_k(wav)

#     if k<0:
#         k=np.abs(k)
    return n+k*1j

def indexOfRefractionZnSe(wav):
    """ Index of refraction of Zinc Selenide (etalons used by INTA to produce FTS measurements)
    Data source: https://refractiveindex.info """
    wav_data,n_data,k_data = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/opticalconstants_ZnSe.txt',usecols=(0,1,2),delimiter=',',unpack=True)

    interp_n  = scp_interpolate.interp1d(wav_data,n_data)
    interp_k  = scp_interpolate.interp1d(wav_data,k_data)

    try:
        n,k = [],[]
        for wvl in wav:
            n.append(interp_n(wvl))
            k.append(interp_k(wvl))
        n,k = np.array(n),np.array(k)
    except TypeError:
        n,k = interp_n(wav),interp_k(wav)

    return n+k*1j

def indexOfRefractionSiO2(wav):
    """ Index of refraction of Silicon Oxide
    Data source: https://refractiveindex.info """
    wav_data,n_data,k_data = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/refractive_index_SiO2.txt',usecols=(0,1,2),delimiter=',',unpack=True)

    interp_n  = scp_interpolate.interp1d(wav_data,n_data)
    interp_k  = scp_interpolate.interp1d(wav_data,k_data)

    try:
        n,k = [],[]
        for wvl in wav:
            if (wvl <wav_data[0]):
                n.append(np.sqrt( 1 + (0.6961663*wvl**2 / (wvl**2 - 0.0684043**2)) + (0.4079426*wvl**2 / (wvl**2 - 0.1162414**2)) + (0.8974794*wvl**2 / (wvl**2 - 9.896161**2))) )
                k.append(0)
            else:
                n.append(interp_n(wvl))
                k.append(interp_k(wvl))
        n,k = np.array(n),np.array(k)
    except TypeError:
        if (wav <wav_data[0]):
            n = np.sqrt( 1 + (0.6961663*wav**2 / (wav**2 - 0.0684043**2)) + (0.4079426*wav**2 / (wav**2 - 0.1162414**2)) + (0.8974794*wav**2 / (wav**2 - 9.896161**2)))
            k = 0
        else:
            n,k = interp_n(wav),interp_k(wav)

    return n+k*1j

def ALrefract_index(dosage):
    # Data from "Refractive index and extinction coefficient of doped polycrystalline silicon films in infrared spectrum"
    # Note that phosphorus is used as the doping element (i.e. not Arsenic as in MIRI's detectors)
    Implanted_dosage = np.array([1.,6.,16.,51.])*10**14
    ALrefract_index = np.array([3.3,3.27,3.14,2.67])
    ALextinct_coeff = np.array([3.48e-3,1.09e-2,2.23e-2,2.04e-1])
    ALrefract_index_interpolator = scp_interpolate.InterpolatedUnivariateSpline(Implanted_dosage,ALrefract_index,k=2,ext=0)
    ALextinct_coeff_interpolator = scp_interpolate.InterpolatedUnivariateSpline(Implanted_dosage,ALextinct_coeff,k=2,ext=0)
    return ALrefract_index_interpolator(dosage) + ALextinct_coeff_interpolator(dosage)*1j

def buriedelectrode_transmission(workDir=None):
    wav_data,transmission = np.genfromtxt(workDir+'transp_contact_transm_5e14implant_poly.txt',skip_header=3,usecols=(0,1),delimiter='',unpack=True)
    transmission /= 100.
    # wav_data in micron
    # transmission normalized to 1
    return wav_data,transmission

def indexOfRefractionBE(wav):
    # buried electrode
    wav_data,transmission = np.genfromtxt('/Users/ioannisa/Desktop/python/miri_devel/transp_contact_transm_5e14implant_poly.txt',skip_header=3,usecols=(0,1),delimiter='',unpack=True)
    transmission /= 100.
    reflection = 1-transmission
    # wav_data in micron
    # transmission normalized to 1

    # Assuming:
    # n1 = 1
    # incidence_angle = 0 deg
    # absorption = 0
    n2 = (1.-reflection)/(reflection+1.)
    interp_n  = scp_interpolate.interp1d(wav_data,n2)

    n,k = [],[]
    for wvl in wav:
        n.append(interp_n(wvl))
        k.append(0)
    n,k = np.array(n),np.array(k)
    return n+k*1j

def SW_ARcoat_reflectance(workDir=None):
    # The SW AR coating is made out of Zinc Sulphide (ZnS)
    wav_data,reflectance = np.genfromtxt(workDir+'SW_ARcoat_reflectance.txt',skip_header=4,usecols=(0,1),delimiter=',',unpack=True)
    # wav_data in micron
    # reflectance normalized to 1
    return wav_data,reflectance

def snells_law(n_list,th_0):
    from scipy import arcsin
    n_list = np.array(n_list)
    #------------------
    # th_list is a list with, for each layer, the angle that the light travels
    # through the layer. Computed with Snell's law. Note that the "angles" may be
    # complex!
    th_list = arcsin(n_list[0]*np.sin(th_0) / n_list)
    return th_list

#--transfer matrix method
def simple_tmm(n_list,d_list,th_0,lambda_vacuum):
    from scipy import arcsin
    n_list,d_list = np.array(n_list),np.array(d_list)
    #------------------
    num_layers = n_list.size
    # th_list is a list with, for each layer, the angle that the light travels
    # through the layer. Computed with Snell's law. Note that the "angles" may be
    # complex!
    th_list = arcsin(n_list[0]*np.sin(th_0) / n_list)
    # kz is the z-component of (complex) angular wavevector for forward-moving
    # wave. Positive imaginary part means decaying.
    kz_list = 2 * np.pi * n_list * np.cos(th_list) / lambda_vacuum
    # delta is the total phase accrued by traveling through a given layer.
    # Ignore warning about inf multiplication
    delta = kz_list * d_list
    #------------------
    # t_list[i,j] and r_list[i,j] are transmission and reflection amplitudes,
    # respectively, coming from i, going to j. Only need to calculate this when
    # j=i+1. (2D array is overkill but helps avoid confusion.)

    # s-polarization
    t_list_spol = np.zeros((num_layers, num_layers), dtype=complex)
    r_list_spol = np.zeros((num_layers, num_layers), dtype=complex)
    for i in range(num_layers-1):
        t_list_spol[i,i+1] = 2 * n_list[i] * np.cos(th_list[i]) / (n_list[i] * np.cos(th_list[i]) + n_list[i+1] * np.cos(th_list[i+1]))
        r_list_spol[i,i+1] = ((n_list[i] * np.cos(th_list[i]) - n_list[i+1] * np.cos(th_list[i+1])) / (n_list[i] * np.cos(th_list[i]) + n_list[i+1] * np.cos(th_list[i+1])))

    # p-polarization
    t_list_ppol = np.zeros((num_layers, num_layers), dtype=complex)
    r_list_ppol = np.zeros((num_layers, num_layers), dtype=complex)
    for i in range(num_layers-1):
        t_list_ppol[i,i+1] = 2 * n_list[i] * np.cos(th_list[i]) / (n_list[i+1] * np.cos(th_list[i]) + n_list[i] * np.cos(th_list[i+1]))
        r_list_ppol[i,i+1] = ((n_list[i+1] * np.cos(th_list[i]) - n_list[i] * np.cos(th_list[i+1])) / (n_list[i+1] * np.cos(th_list[i]) + n_list[i] * np.cos(th_list[i+1])))
    #------------------
    def make_2x2_array(a, b, c, d, dtype=float):
        my_array = np.empty((2,2), dtype=dtype)
        my_array[0,0] = a
        my_array[0,1] = b
        my_array[1,0] = c
        my_array[1,1] = d
        return my_array

    # At the interface between the (n-1)st and nth material, let v_n be the
    # amplitude of the wave on the nth side heading forwards (away from the
    # boundary), and let w_n be the amplitude on the nth side heading backwards
    # (towards the boundary). Then (v_n,w_n) = M_n (v_{n+1},w_{n+1}). M_n is
    # M_list[n]. M_0 and M_{num_layers-1} are not defined.
    # My M is a bit different than Sernelius's, but Mtilde is the same.
    M_list_spol = np.zeros((num_layers, 2, 2), dtype=complex)
    for i in range(1, num_layers-1):
        M_list_spol[i] = (1/t_list_spol[i,i+1]) * np.dot(
            make_2x2_array(np.exp(-1j*delta[i]), 0, 0, np.exp(1j*delta[i]),
                           dtype=complex),
            make_2x2_array(1, r_list_spol[i,i+1], r_list_spol[i,i+1], 1, dtype=complex))
    Mtilde_spol = make_2x2_array(1, 0, 0, 1, dtype=complex)
    for i in range(1, num_layers-1):
        Mtilde_spol = np.dot(Mtilde_spol, M_list_spol[i])
    Mtilde_spol = np.dot(make_2x2_array(1, r_list_spol[0,1], r_list_spol[0,1], 1,
                                   dtype=complex)/t_list_spol[0,1], Mtilde_spol)

    M_list_ppol = np.zeros((num_layers, 2, 2), dtype=complex)
    for i in range(1, num_layers-1):
        M_list_ppol[i] = (1/t_list_ppol[i,i+1]) * np.dot(
            make_2x2_array(np.exp(-1j*delta[i]), 0, 0, np.exp(1j*delta[i]),
                           dtype=complex),
            make_2x2_array(1, r_list_ppol[i,i+1], r_list_ppol[i,i+1], 1, dtype=complex))
    Mtilde_ppol = make_2x2_array(1, 0, 0, 1, dtype=complex)
    for i in range(1, num_layers-1):
        Mtilde_ppol = np.dot(Mtilde_ppol, M_list_ppol[i])
    Mtilde_ppol = np.dot(make_2x2_array(1, r_list_ppol[0,1], r_list_ppol[0,1], 1,
                                   dtype=complex)/t_list_ppol[0,1], Mtilde_ppol)
    #------------------
    # Net complex transmission and reflection amplitudes
    r_spol = Mtilde_spol[1,0]/Mtilde_spol[0,0]
    t_spol = 1/Mtilde_spol[0,0]

    r_ppol = Mtilde_ppol[1,0]/Mtilde_ppol[0,0]
    t_ppol = 1/Mtilde_ppol[0,0]
    #------------------
    # Net transmitted and reflected power, as a proportion of the incoming light
    # power.
    R_spol = abs(r_spol)**2
    T_spol = abs(t_spol**2) * (((n_list[-1]*np.cos(th_list[-1])).real) / (n_list[0]*np.cos(th_0)).real)
    power_entering_spol = ((n_list[0]*np.cos(th_0)*(1+np.conj(r_spol))*(1-r_spol)).real
                         / (n_list[0]*np.cos(th_0)).real)

    R_ppol = abs(r_ppol)**2
    T_ppol = abs(t_ppol**2) * (((n_list[-1]*np.conj(np.cos(th_list[-1]))).real) / (n_list[0]*np.conj(np.cos(th_0))).real)
    power_entering_ppol = ((n_list[0]*np.conj(np.cos(th_0))*(1+r_ppol)*(1-np.conj(r_ppol))).real
                          / (n_list[0]*np.conj(np.cos(th_0))).real)
    #------------------
    # Calculates reflected and transmitted power for unpolarized light.
    R = (R_spol + R_ppol) / 2.
    T = (T_spol + T_ppol) / 2.
    A = 1-R-T

    return R,T,A

def not_simple_tmm(n_list,d_list,sig_list,th_0,lambda_vacuum):
    from scipy import arcsin
    n_list,d_list,sig_list = np.array(n_list),np.array(d_list),np.array(sig_list)
    #------------------
    num_layers = n_list.size
    # th_list is a list with, for each layer, the angle that the light travels
    # through the layer. Computed with Snell's law. Note that the "angles" may be
    # complex!
    th_list = arcsin(n_list[0]*np.sin(th_0) / n_list)
    # kz is the z-component of (complex) angular wavevector for forward-moving
    # wave. Positive imaginary part means decaying.
    kz_list = 2 * np.pi * n_list * np.cos(th_list) / lambda_vacuum
    # delta is the total phase accrued by traveling through a given layer.
    # Ignore warning about inf multiplication
    delta = kz_list * d_list
    w_tilde = np.exp(- (sig_list**2. / 2.) * (4.*np.pi/lambda_vacuum)**2 )
    #------------------
    # t_list[i,j] and r_list[i,j] are transmission and reflection amplitudes,
    # respectively, coming from i, going to j. Only need to calculate this when
    # j=i+1. (2D array is overkill but helps avoid confusion.)

    # s-polarization
    t_list_spol = np.zeros((num_layers, num_layers), dtype=complex)
    r_list_spol = np.zeros((num_layers, num_layers), dtype=complex)
    for i in range(num_layers-1):
        t_list_spol[i,i+1] = 2 * n_list[i] * np.cos(th_list[i]) / (n_list[i] * np.cos(th_list[i]) + n_list[i+1] * np.cos(th_list[i+1]))
        r_list_spol[i,i+1] = w_tilde[i] * ((n_list[i] * np.cos(th_list[i]) - n_list[i+1] * np.cos(th_list[i+1])) / (n_list[i] * np.cos(th_list[i]) + n_list[i+1] * np.cos(th_list[i+1])))

    # p-polarization
    t_list_ppol = np.zeros((num_layers, num_layers), dtype=complex)
    r_list_ppol = np.zeros((num_layers, num_layers), dtype=complex)
    for i in range(num_layers-1):
        t_list_ppol[i,i+1] = 2 * n_list[i] * np.cos(th_list[i]) / (n_list[i+1] * np.cos(th_list[i]) + n_list[i] * np.cos(th_list[i+1]))
        r_list_ppol[i,i+1] = w_tilde[i] * ((n_list[i+1] * np.cos(th_list[i]) - n_list[i] * np.cos(th_list[i+1])) / (n_list[i+1] * np.cos(th_list[i]) + n_list[i] * np.cos(th_list[i+1])))
    #------------------
    def make_2x2_array(a, b, c, d, dtype=float):
        my_array = np.empty((2,2), dtype=dtype)
        my_array[0,0] = a
        my_array[0,1] = b
        my_array[1,0] = c
        my_array[1,1] = d
        return my_array

    # At the interface between the (n-1)st and nth material, let v_n be the
    # amplitude of the wave on the nth side heading forwards (away from the
    # boundary), and let w_n be the amplitude on the nth side heading backwards
    # (towards the boundary). Then (v_n,w_n) = M_n (v_{n+1},w_{n+1}). M_n is
    # M_list[n]. M_0 and M_{num_layers-1} are not defined.
    # My M is a bit different than Sernelius's, but Mtilde is the same.
    M_list_spol = np.zeros((num_layers, 2, 2), dtype=complex)
    for i in range(1, num_layers-1):
        M_list_spol[i] = (1/t_list_spol[i,i+1]) * np.dot(
            make_2x2_array(np.exp(-1j*delta[i]), 0, 0, np.exp(1j*delta[i]),
                           dtype=complex),
            make_2x2_array(1, r_list_spol[i,i+1], r_list_spol[i,i+1], 1, dtype=complex))
    Mtilde_spol = make_2x2_array(1, 0, 0, 1, dtype=complex)
    for i in range(1, num_layers-1):
        Mtilde_spol = np.dot(Mtilde_spol, M_list_spol[i])
    Mtilde_spol = np.dot(make_2x2_array(1, r_list_spol[0,1], r_list_spol[0,1], 1,
                                   dtype=complex)/t_list_spol[0,1], Mtilde_spol)

    M_list_ppol = np.zeros((num_layers, 2, 2), dtype=complex)
    for i in range(1, num_layers-1):
        M_list_ppol[i] = (1/t_list_ppol[i,i+1]) * np.dot(
            make_2x2_array(np.exp(-1j*delta[i]), 0, 0, np.exp(1j*delta[i]),
                           dtype=complex),
            make_2x2_array(1, r_list_ppol[i,i+1], r_list_ppol[i,i+1], 1, dtype=complex))
    Mtilde_ppol = make_2x2_array(1, 0, 0, 1, dtype=complex)
    for i in range(1, num_layers-1):
        Mtilde_ppol = np.dot(Mtilde_ppol, M_list_ppol[i])
    Mtilde_ppol = np.dot(make_2x2_array(1, r_list_ppol[0,1], r_list_ppol[0,1], 1,
                                   dtype=complex)/t_list_ppol[0,1], Mtilde_ppol)
    #------------------
    # Net complex transmission and reflection amplitudes
    r_spol = Mtilde_spol[1,0]/Mtilde_spol[0,0]
    t_spol = 1/Mtilde_spol[0,0]

    r_ppol = Mtilde_ppol[1,0]/Mtilde_ppol[0,0]
    t_ppol = 1/Mtilde_ppol[0,0]
    #------------------
    # Net transmitted and reflected power, as a proportion of the incoming light
    # power.
    R_spol = abs(r_spol)**2
    T_spol = abs(t_spol**2) * (((n_list[-1]*np.cos(th_list[-1])).real) / (n_list[0]*np.cos(th_0)).real)
    power_entering_spol = ((n_list[0]*np.cos(th_0)*(1+np.conj(r_spol))*(1-r_spol)).real
                         / (n_list[0]*np.cos(th_0)).real)

    R_ppol = abs(r_ppol)**2
    T_ppol = abs(t_ppol**2) * (((n_list[-1]*np.conj(np.cos(th_list[-1]))).real) / (n_list[0]*np.conj(np.cos(th_0))).real)
    power_entering_ppol = ((n_list[0]*np.conj(np.cos(th_0))*(1+r_ppol)*(1-np.conj(r_ppol))).real
                          / (n_list[0]*np.conj(np.cos(th_0))).real)
    #------------------
    # Calculates reflected and transmitted power for unpolarized light.
    R = (R_spol + R_ppol) / 2.
    T = (T_spol + T_ppol) / 2.
    A = 1-R-T

    return R,T,A

#--save and load objects
def save_obj(obj,name,path='' ):
    with open(path+name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name,path='' ):
    with open(path+name + '.pkl', 'rb') as f:
        return pickle.load(f)

# interpolate nans in 1d array
def nan_helper(y):
    """Helper to handle indices and logical indices of NaNs.

    Input:
        - y, 1d numpy array with possible NaNs
    Output:
        - nans, logical indices of NaNs
        - index, a function, with signature indices= index(logical_indices),
          to convert logical indices of NaNs to 'equivalent' indices
    Example:
        >>> # linear interpolation of NaNs
        >>> nans, x= nan_helper(y)
        >>> y[nans]= np.interp(x(nans), x(~nans), y[~nans])
    """

    return np.isnan(y), lambda z: z.nonzero()[0]

def interp_nans(y):
    # replaces nans in 1d array by surrounding interpolated values
    nans, x = nan_helper(y)
    y[nans] = np.interp(x(nans), x(~nans), y[~nans])
    return y

# smooth out the signal
def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0))
    return (cumsum[N:] - cumsum[:-N]) / N

#--Alvaro's functions
def find_max(signal_cut,wavel_cut,maxcut,w_toler):
    #from scipy.signal import argrelmax
    #from pylab import *
    # Removes the first and last slope so they are not identified as maxima
    iii = 0
    while(signal_cut[iii] < 0) or (signal_cut[iii] > signal_cut[iii+1]) or (np.isnan(signal_cut[iii])):
        signal_cut[iii] = np.nan
        #print iii
        iii = iii+1
    jjj = -1
    while(signal_cut[jjj] < 0) or (signal_cut[jjj] > signal_cut[jjj-1]) or (np.isnan(signal_cut[jjj])):
        signal_cut[jjj] = np.nan
        #print jjj
        jjj = jjj-1

    # Assigns Nan to the Infs in the signal
    isinf = np.isinf(signal_cut)
    wcinf = where(isinf)
    for wwwinf in wcinf:
        signal_cut[wwwinf] = np.nan
    # Removes the Nan in the signal
    isnan = np.isnan(signal_cut)
    wc = where(isnan)
    for www in wc:
        signal_cut[www] = 0

    # Creates a temporary spectrum with everything below maxcut max is 0, so it only finds the line peaks (and no noise) as maxima.
    print "peak value = ", max(signal_cut)
    ws = where(signal_cut > maxcut * max(signal_cut))
    signal_temp = np.zeros(size(signal_cut))
    signal_temp[ws] = signal_cut[ws]+0

    # Searches for the maxima (i.e. the line peaks):
    inds_maxs_temp = [argrelmax(signal_temp)[0]]
    maxs_w_temp = wavel_cut[inds_maxs_temp]
    maxs_s_temp = signal_cut[inds_maxs_temp]

    # Some lines are double-peaked, so I need to remove maxima for the same line:
    for mmm in range(1,size(maxs_w_temp)):
        if abs(maxs_w_temp[mmm]-maxs_w_temp[mmm-1]) < w_toler:
            if maxs_s_temp[mmm] > maxs_s_temp[mmm-1]:
                maxs_w_temp[mmm-1] = np.nan
            else:
                maxs_w_temp[mmm] = np.nan

    # Some lines are triple-peaked, so I need to repeat the process:
    son_nan_temp2 = np.isnan(maxs_w_temp)
    inds_maxs_temp2 = where(son_nan_temp2 == False)
    maxs_s_temp2 = maxs_s_temp[inds_maxs_temp2]
    maxs_w_temp2 = maxs_w_temp[inds_maxs_temp2]

    for mmm in range(1,size(maxs_w_temp2)):
        if abs(maxs_w_temp2[mmm]-maxs_w_temp2[mmm-1]) < w_toler:
            if maxs_s_temp2[mmm] > maxs_s_temp2[mmm-1]:
                maxs_w_temp2[mmm-1] = np.nan
            else:
                maxs_w_temp2[mmm] = np.nan

    # Some lines are four-times-peaked, so I need to repeat the process:
    son_nan_temp3 = np.isnan(maxs_w_temp2)
    inds_maxs_temp3 = where(son_nan_temp3 == False)
    maxs_s_temp3 = maxs_s_temp2[inds_maxs_temp3]
    maxs_w_temp3 = maxs_w_temp2[inds_maxs_temp3]

    for mmm in range(1,size(maxs_w_temp3)):
        if abs(maxs_w_temp3[mmm]-maxs_w_temp3[mmm-1]) < w_toler:
            if maxs_s_temp3[mmm] > maxs_s_temp3[mmm-1]:
                maxs_w_temp3[mmm-1] = np.nan
            else:
                maxs_w_temp3[mmm] = np.nan

    #And again:
    son_nan_temp4 = np.isnan(maxs_w_temp3)
    inds_maxs_temp4 = where(son_nan_temp4 == False)
    maxs_s_temp4 = maxs_s_temp3[inds_maxs_temp4]
    maxs_w_temp4 = maxs_w_temp3[inds_maxs_temp4]

    for mmm in range(1,size(maxs_w_temp4)):
        if abs(maxs_w_temp4[mmm]-maxs_w_temp4[mmm-1]) < w_toler:
            if maxs_s_temp4[mmm] > maxs_s_temp4[mmm-1]:
                maxs_w_temp4[mmm-1] = np.nan
            else:
                maxs_w_temp4[mmm] = np.nan

    #One more:
    son_nan_temp5 = np.isnan(maxs_w_temp4)
    inds_maxs_temp5 = where(son_nan_temp5 == False)
    maxs_s_temp5 = maxs_s_temp4[inds_maxs_temp5]
    maxs_w_temp5 = maxs_w_temp4[inds_maxs_temp5]

    for mmm in range(1,size(maxs_w_temp5)):
        if abs(maxs_w_temp5[mmm]-maxs_w_temp5[mmm-1]) < w_toler:
            if maxs_s_temp5[mmm] > maxs_s_temp5[mmm-1]:
                maxs_w_temp5[mmm-1] = np.nan
            else:
                maxs_w_temp5[mmm] = np.nan

    # So the "cleaned" maxima are:
    son_nan = np.isnan(maxs_w_temp5)
    inds_maxs = where(son_nan == False)
    maxs_s = maxs_s_temp5[inds_maxs]
    maxs_w = maxs_w_temp5[inds_maxs]

    #One more, increasing the toler value at the middle of the spectrum:
    son_nan_temp6 = np.isnan(maxs_w_temp5)
    inds_maxs_temp6 = where(son_nan_temp6 == False)
    maxs_s_temp6 = maxs_s_temp5[inds_maxs_temp6]
    maxs_w_temp6 = maxs_w_temp5[inds_maxs_temp6]

    for mmm in range(1, size(maxs_w_temp6)-1):
        if abs(maxs_w_temp6[mmm]-maxs_w_temp6[mmm+1]) < w_toler+1 and maxs_w_temp6[mmm] > 650:
            if maxs_s_temp6[mmm] > maxs_s_temp6[mmm+1]:
                maxs_w_temp6[mmm+1] = np.nan
            else:
                maxs_w_temp6[mmm] = np.nan
        elif abs(maxs_w_temp6[mmm]-maxs_w_temp6[mmm+1]) < w_toler+4 and maxs_w_temp6[mmm] > 950:
            if maxs_s_temp6[mmm] > maxs_s_temp6[mmm+1]:
                maxs_w_temp6[mmm+1] = np.nan
            else:
                maxs_w_temp6[mmm] = np.nan

    # So the "cleaned" maxima are:
    son_nan = np.isnan(maxs_w_temp6)
    inds_maxs = where(son_nan == False)
    maxs_s = maxs_s_temp6[inds_maxs]
    maxs_w = maxs_w_temp6[inds_maxs]

    return maxs_s,maxs_w

def find_nearest_value(array,value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]

def find_peaks2(ydata, thres=0.3, min_dist=1):
    """Peak detection routine.

    Finds the numeric index of the peaks in *y* by taking its first order difference. By using
    *thres* and *min_dist* parameters, it is possible to reduce the number of
    detected peaks. *y* must be signed.

    Parameters
    ----------
    y : ndarray (signed)
        1D amplitude ydata to search for peaks.
    thres : float between [0., 1.]
        Normalized threshold. Only the peaks with amplitude higher than the
        threshold will be detected.
    min_dist : int
        Minimum distance between each detected peak. The peak with the highest
        amplitude is preferred to satisfy this constraint.

    Returns
    -------
    ndarray
        Array containing the numeric indexes of the peaks that were detected
    """
    if isinstance(ydata, np.ndarray) and np.issubdtype(ydata.dtype, np.unsignedinteger):
        raise ValueError("ydata must be signed")

    y = ydata.copy()
    y[np.isnan(y)] = 0

    thres = thres * (np.max(y) - np.min(y)) + np.min(y)
    min_dist = int(min_dist)

    # compute first order difference
    dy = np.diff(y)

    # propagate left and right values successively to fill all plateau pixels (0-value)
    zeros,=np.where(dy == 0)

    while len(zeros):
        # add pixels 2 by 2 to propagate left and right value onto the zero-value pixel
        zerosr = np.hstack([dy[1:], 0.])
        zerosl = np.hstack([0., dy[:-1]])

        # replace 0 with right value if non zero
        dy[zeros]=zerosr[zeros]
        zeros,=np.where(dy == 0)

        # replace 0 with left value if non zero
        dy[zeros]=zerosl[zeros]
        zeros,=np.where(dy == 0)

    # find the peaks by using the first order difference
    peaks = np.where((np.hstack([dy, 0.]) < 0.)
                     & (np.hstack([0., dy]) > 0.)
                     & (y > thres))[0]

    if peaks.size > 1 and min_dist > 1:
        highest = peaks[np.argsort(y[peaks])][::-1]
        rem = np.ones(y.size, dtype=bool)
        rem[peaks] = False

        for peak in highest:
            if not rem[peak]:
                sl = slice(max(0, peak - min_dist), peak + min_dist + 1)
                rem[sl] = True
                rem[peak] = False

        peaks = np.arange(y.size)[~rem]

    return peaks

#--Wavelength calibration reference point per band
def filter_transmission(band,datapath=None,verbose=False):
    # wavelength range of interest
    lamblower,lambupper = mrs_aux(band)[3]
    if band == '1B':
        usedfilter='SWP' # Short Wavepass Filter
        # Read the measured transmission curves from the dat files
        # first colum is wavelength [micrometer]
        # second and third columns are room temperature transmissions
        # fourth column is 35K transmission
        SWPwvnr,SWPtransm = np.genfromtxt(datapath + "swp_filter.txt", skip_header = 15, skip_footer=1, usecols=(0,3), delimiter = '',unpack='True')
        SWPwave = 10000./SWPwvnr
        SWPtransm = SWPtransm/100. # convert percentage to decimal
        sel = (SWPwave>=lamblower) & (SWPwave<=lambupper)

        filter_wave = SWPwave[sel]
        filter_transm = SWPtransm[sel]

    elif band == '1C':
        usedfilter='LWP' # Long Wavepass Filter
        # -->Read the measured transmission curves from the data files
        # first column is wavelength [micrometer]
        # second and third columns are room temperature transmissions
        # fourth column is 35K transmission
        LWPwvnr,LWPtransm = np.genfromtxt(datapath + "lwp_filter.txt", skip_header = 15, skip_footer=1, usecols=(0,3), delimiter = '',unpack='True')
        LWPwave = 10000./LWPwvnr
        LWPtransm = LWPtransm/100. # convert percentage to decimal
        sel = (LWPwave>=lamblower) & (LWPwave<=lambupper)

        filter_wave = LWPwave[sel]
        filter_transm = LWPtransm[sel]

    elif band == '2A':
        usedfilter='Dichroic'
        # Read the measured transmission curves from the csv files
        # first colum is wavelength [micrometer]
        # second column is room temperature transmission
        # third column is 7K transmission
        col = 2
        filterWave= np.genfromtxt(datapath + "fm_dichroics_1a.csv", delimiter=";")[:,0]
        D1A = np.genfromtxt(datapath + "fm_dichroics_1a.csv", delimiter=";")[:,col]/100.
        D1B = np.genfromtxt(datapath + "fm_dichroics_1b.csv", delimiter=";")[:,col]/100.
        sel = (filterWave>=lamblower) & (filterWave<=lambupper)

        filter_wave = filterWave[sel]
        filter_transm = (D1B/D1A)[sel]
        if verbose:
            print 'Dichroic D1B/D1A transmission ratio'

    elif band == '2B':
        usedfilter='Dichroic'
        # Read the measured transmission curves from the csv files
        # first colum is wavelength [micrometer]
        # second column is room temperature transmission
        # third column is 7K transmission
        col = 2
        filterWave= np.genfromtxt(datapath + "fm_dichroics_1a.csv", delimiter=";")[:,0]
        D1B = np.genfromtxt(datapath + "fm_dichroics_1b.csv", delimiter=";")[:,col]/100.
        D1C = np.genfromtxt(datapath + "fm_dichroics_1c.csv", delimiter=";")[:,col]/100.
        sel = (filterWave>=lamblower) & (filterWave<=lambupper)

        filter_wave = filterWave[sel]
        filter_transm = (D1C/D1B)[sel]
        if verbose:
            print 'Dichroic D1C/D1B transmission ratio'

    elif band == '2C':
        usedfilter='LWP' # Long Wavepass Filter
        # -->Read the measured transmission curves from the data files
        # first column is wavelength [micrometer]
        # second and third columns are room temperature transmissions
        # fourth column is 35K transmission
        LWPwvnr,LWPtransm = np.genfromtxt(datapath + "lwp_filter.txt", skip_header = 15, skip_footer=1, usecols=(0,3), delimiter = '',unpack='True')
        LWPwave = 10000./LWPwvnr
        LWPtransm = LWPtransm/100. # convert percentage to decimal
        sel = (LWPwave>=lamblower) & (LWPwave<=lambupper)

        filter_wave = LWPwave[sel]
        filter_transm = LWPtransm[sel]

    elif band == '4A':
        usedfilter='Dichroic'
        # Read the measured transmission curves from the csv files
        # zeroth colum is wavelength [micrometer]
        # first column is room temperature transmission
        # second column is 7K transmission
        col = 2
        filterWave= np.genfromtxt(datapath + "fm_dichroics_1a.csv", delimiter=";")[:,0]
        D2A = np.genfromtxt(datapath + "fm_dichroics_2a.csv", delimiter=";")[:,col]/100.
        D3A = np.genfromtxt(datapath + "fm_dichroics_3a.csv", delimiter=";")[:,col]/100.
        D2B = np.genfromtxt(datapath + "fm_dichroics_2b.csv", delimiter=";")[:,col]/100.
        D3B = np.genfromtxt(datapath + "fm_dichroics_3b.csv", delimiter=";")[:,col]/100.
        sel = (filterWave>=lamblower) & (filterWave<=lambupper)

        filter_wave = filterWave[sel]
        filter_transm = ((D2B*D3B)/(D2A*D3A))[sel]

        if verbose:
            print 'Dichroic (D2B*D3B)/(D2A*D3A) transmission ratio'

    elif band == '4B':
        usedfilter='SWP' # Short Wavepass Filter
        # Read the measured transmission curves from the dat files
        # first colum is wavelength [micrometer]
        # second and third columns are room temperature transmissions
        # fourth column is 35K transmission
        SWPwvnr,SWPtransm = np.genfromtxt(datapath + "swp_filter.txt", skip_header = 15, skip_footer=1, usecols=(0,3), delimiter = '',unpack='True')
        SWPwave = 10000./SWPwvnr
        SWPtransm = SWPtransm/100. # convert percentage to decimal
        sel = (SWPwave>=lamblower) & (SWPwave<=lambupper)

        filter_wave = SWPwave[sel]
        filter_transm = SWPtransm[sel]

    elif band == '4C':
        usedfilter='Dichroic'
        # Read the measured transmission curves from the csv files
        # zeroth colum is wavelength [micrometer]
        # first column is room temperature transmission
        # second column is 7K transmission
        col = 2
        filterWave= np.genfromtxt(datapath + "fm_dichroics_1a.csv", delimiter=";")[:,0]
        D2B = np.genfromtxt(datapath + "fm_dichroics_2b.csv", delimiter=";")[:,col]/100.
        D3B = np.genfromtxt(datapath + "fm_dichroics_3b.csv", delimiter=";")[:,col]/100.
        D2C = np.genfromtxt(datapath + "fm_dichroics_2c.csv", delimiter=";")[:,col]/100.
        D3C = np.genfromtxt(datapath + "fm_dichroics_3c.csv", delimiter=";")[:,col]/100.
        sel = (filterWave>=lamblower) & (filterWave<=lambupper)

        filter_wave = filterWave[sel]
        filter_transm = ((D2C*D3C)/(D2B*D3B))[sel]

    return usedfilter,filter_wave,filter_transm


def mrs_filter_transmission(band,datapath=None):
    # Import MRS observations
    import mrsobs
    if band == '1B':
        usedfilter='SWP'
        # swp_filter_img: SWP filter extended obs (SWP transm x 800K BB), ext_source_img: 800K BB extended source config

        swp_filter_img,ext_source_img,bkg_img = mrsobs.FM_MTS_800K_BB_MRS_OPT_08(datapath,band,wp_filter=usedfilter,output='img')
        swp_transmission_img = (swp_filter_img-bkg_img)/(ext_source_img-bkg_img)

        return usedfilter,swp_filter_img,ext_source_img,swp_transmission_img

    elif band == '1C':
        usedfilter='LWP'
        # lwp_filter_img: LWP filter extended obs (LWP transm x 800K BB), ext_source_img: 800K BB extended source config

        lwp_filter_img,ext_source_img,bkg_img = mrsobs.FM_MTS_800K_BB_MRS_OPT_08(datapath,band,wp_filter=usedfilter,output='img')
        lwp_transmission_img = (lwp_filter_img-bkg_img)/(ext_source_img-bkg_img)

        return usedfilter,lwp_filter_img,ext_source_img,lwp_transmission_img

    elif band == '2A':
        usedfilter='Dichroic'
        # top: xconfig 2AxB image, bottom: nominal 1A/2A detector image
        cross_config = mrsobs.MIRI_internal_calibration_source(datapath,'2AxB',campaign='FM',output='img')
        nomin_config = mrsobs.MIRI_internal_calibration_source(datapath,'2A',campaign='FM',output='img')
        mrs_transmission_img = cross_config/nomin_config

        return usedfilter,cross_config,nomin_config,mrs_transmission_img

    elif band == '2B':
        usedfilter='Dichroic'
        # top: xconfig 2BxC image, bottom: nominal 1B/2B detector image
        cross_config = mrsobs.MIRI_internal_calibration_source(datapath,'2BxC',campaign='FM',output='img')
        nomin_config = mrsobs.MIRI_internal_calibration_source(datapath,'2B',campaign='FM',output='img')
        mrs_transmission_img = cross_config/nomin_config

        return usedfilter,cross_config,nomin_config,mrs_transmission_img

    elif band == '2C':
        usedfilter='LWP'
        # lwp_filter_img: LWP filter extended obs (LWP transm x 800K BB), ext_source_img: 800K BB extended source config

        lwp_filter_img,ext_source_img,bkg_img = mrsobs.FM_MTS_800K_BB_MRS_OPT_08(datapath,band,wp_filter='LWP',output='img')
        lwp_transmission_img = (lwp_filter_img-bkg_img)/(ext_source_img-bkg_img)

        return usedfilter,lwp_filter_img,ext_source_img,lwp_transmission_img

    elif band == '4A':
        usedfilter='Dichroic'
        # top: xconfig 2BxC image, bottom: nominal 1B/2B detector image
        cross_config = mrsobs.MIRI_internal_calibration_source(datapath,'4AxB',campaign='FM',output='img')
        nomin_config = mrsobs.MIRI_internal_calibration_source(datapath,'4A',campaign='FM',output='img')
        mrs_transmission_img = cross_config/nomin_config

        return usedfilter,cross_config,nomin_config,mrs_transmission_img

    elif band == '4B':
        usedfilter='SWP'
        # swp_filter_img: SWP filter extended obs (SWP transm x 800K BB), ext_source_img: 800K BB extended source config

        swp_filter_img,ext_source_img,bkg_img = mrsobs.FM_MTS_800K_BB_MRS_OPT_08(datapath,band,wp_filter=usedfilter,output='img')
        swp_transmission_img = (swp_filter_img-bkg_img)/(ext_source_img-bkg_img)

        return usedfilter,swp_filter_img,ext_source_img,swp_transmission_img

    elif band == '4C':
        usedfilter='Dichroic'
        # top: xconfig 2BxC image, bottom: nominal 1B/2B detector image
        cross_config = mrsobs.MIRI_internal_calibration_source(datapath,'4CxB',campaign='FM',output='img')
        nomin_config = mrsobs.MIRI_internal_calibration_source(datapath,'4C',campaign='FM',output='img')

        # the division of the above two images yields a negative signal;
        # to mitigate this we offset the signal of both images by a constant value
        xcol = 82
        offset = np.abs(cross_config[:,xcol][~np.isnan(cross_config[:,xcol])].min())
        mrs_transmission_img = (nomin_config+offset)/(cross_config+offset)

        return usedfilter,cross_config,nomin_config,mrs_transmission_img

def get_reference_point(band,filter_wave,filter_transm,mrs_transmission,plot=False):
    from scipy.signal import savgol_filter
    import scipy.interpolate as scp_interpolate
    # wavelength range of interest
    lamblower,lambupper = mrs_aux(band)[3]
    if band == '1B': usedfilter = 'SWP'
    elif band == '1C': usedfilter = 'LWP'
    elif band in ['2A','2B','4C']: usedfilter = 'Dichroic'

    if band in ['1B','1C','4C']:
        """
        Below we compare the lab and MRS determined filter transmissions. Since the steep gradient part of the transmission
        in the lab data shows erratic changes of slope (compared to the MRS data), rather than defining a cut-off on the steep
        gradient part of the curve, we determine the reference wavelength/pixel pair at the location where the filter transmission
        flattens out, i.e. where the gradient of the curve is zero. A spline is fitted through the MRS data to remove the small amplitude
        high-frequency noise in the data.
        """
        # load spectrum from desired location and carry-out analysis
        sci_fm_data = mrs_transmission

        # post-processing
        sci_fm_data[np.isnan(sci_fm_data)] = 0
        if band == '1C':
            # fit spline to data (smoother signal profile)
            spl = scp_interpolate.UnivariateSpline(np.arange(len(sci_fm_data[1:-1]) ),sci_fm_data[1:-1])
            spl.set_smoothing_factor(0.02)
            sci_fm_data = spl(np.arange(len(sci_fm_data)))

        # compute gradients and slopes
        filter_grad = np.gradient(filter_transm,filter_wave)
        filter_signs = np.sign(filter_grad)

        if band == '1B': sci_fm_data_grad = np.gradient(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],21,3))
        elif band == '1C': sci_fm_data_grad = np.gradient(sci_fm_data)
        elif band == '4C': sci_fm_data_grad = np.gradient(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],51,3))
        sci_fm_data_signs = np.sign(sci_fm_data_grad)

        # filter regions as necessary
        if band == '1B':
            filter_signs[:find_nearest(filter_wave,6.44)] = 0
            sci_fm_data_signs[:800] = 0
        elif band == '4C':
            sci_fm_data_signs[:400] = 0

        filter_zerocrossing = np.where(np.abs(np.diff(filter_signs)) == 2)[0]
        sci_fm_data_zerocrossing = np.where(np.abs(np.diff(sci_fm_data_signs)) == 2)[0]
        if band == '4C':
            sci_fm_data_zerocrossing = np.where(np.abs(np.diff(sci_fm_data_signs[575:600])) == 2)[0]
            sci_fm_data_zerocrossing += 575

        x0 = filter_wave[filter_zerocrossing[0]]
        x1 = filter_wave[filter_zerocrossing[0]+1]
        y0 = filter_grad[filter_zerocrossing[0]]
        y1 = filter_grad[filter_zerocrossing[0]+1]
        a = (y1-y0)/(x1-x0)
        cutofflamb = (-y0/a) + x0

        x0 = sci_fm_data_zerocrossing[0]
        x1 = np.arange(len(sci_fm_data))[sci_fm_data_zerocrossing[0]+1]
        y0 = sci_fm_data_grad[sci_fm_data_zerocrossing[0]]
        y1 = sci_fm_data_grad[sci_fm_data_zerocrossing[0]+1]
        a = (y1-y0)/(x1-x0)
        cutoffpix = (-y0/a) + x0

        if plot:
            fig,axs = plt.subplots(1,2,figsize=(12,4))
            axs[0].plot(filter_wave,filter_transm)
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('Transmission',fontsize=12)
            axs[0].set_title('{} filter transmission (lab data)'.format(usedfilter),fontsize=12)
            axs[1].plot(sci_fm_data[np.nonzero(sci_fm_data)],label='original data')
            if band == '1B':
                axs[1].plot(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],21,3),'r',label='smoothed data')
                axs[1].legend(loc='lower left',fontsize=12)
            axs[1].set_xlim(-40,1064)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_title('{} filter transmission (MRS data)'.format(usedfilter),fontsize=12)
            for plot in range(2): axs[plot].tick_params(axis='both',labelsize=12)
            plt.tight_layout()

            fig,axs = plt.subplots(2,1,figsize=(12,8))
            plt.suptitle('Cut-off wavelength {}micron located at pixel {}'.format(round(cutofflamb,2),round(cutoffpix,2) ),fontsize=12)
            if band == '1B': lower0,upper0 = -0.001,0.0022; lower1,upper1 = -0.004,0.008;
            elif band == '1C': lower0,upper0 =  -0.001,0.004; lower1,upper1 = -0.004,0.008
            axs[0].plot(filter_wave,np.gradient(filter_transm,filter_wave),'b')
            axs[0].hlines(0,lamblower,lambupper)
            axs[0].vlines(cutofflamb,lower0,upper0,linestyle='dashed',label='reference point')
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_ylim(lower0,upper0)
            if band == '1B':
                axs[1].plot(np.gradient(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],21,3)),'r')
            elif band == '4C':
                axs[1].plot(np.gradient(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],51,3)),'r')
            else:
                axs[1].plot(np.gradient(sci_fm_data[np.nonzero(sci_fm_data)]),'r')
            axs[1].hlines(0,0,1024)
            axs[1].vlines(cutoffpix,lower1,upper1,linestyle='dashed',label='reference point')
            axs[1].set_xlim(0,1023)
            axs[1].set_ylim(lower1,upper1)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('INTA {} transm gradient'.format(usedfilter),fontsize=12)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_ylabel('RAL {} transm gradient'.format(usedfilter),fontsize=12)
            for plot in range(2):
                axs[plot].tick_params(axis='both',labelsize=12)
                axs[plot].legend(loc='upper right',fontsize=12)
            plt.tight_layout(rect=[0, 0.03, 1, 0.98])

        if band == '1C':
            print 'The result is senstive to spl.set_smoothing_factor'

    elif band == '2A':
        # define cut-off wavelength
        cutofflamb = 8.17
        # load spectrum from desired location and carry-out analysis
        sci_fm_data = mrs_transmission
        # Relate transmission values in wavelength space and in pixel space
        matched_wavls = np.full(len(sci_fm_data),np.nan)
        sel = (filter_wave>7.4) & (filter_wave<8.4) # Take range around cut-off (== 8.17 microns)

        for i in range(len(sci_fm_data)):
            matched_wavls[i] = filter_wave[sel][np.abs(filter_transm[sel]-sci_fm_data[i]).argmin()]

        popt = np.polyfit(np.arange(len(sci_fm_data))[400:600],matched_wavls[400:600],1)
        cutoffpix = (cutofflamb-popt[1])/popt[0]

        if plot:
            fig,axs = plt.subplots(1,2,figsize=(12,4))
            axs[0].plot(filter_wave,filter_transm)
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('Transmission',fontsize=12)
            axs[0].set_title('{} filter transmission (lab data)'.format(usedfilter),fontsize=12)
            axs[1].plot(sci_fm_data[np.nonzero(sci_fm_data)],label='original data')
            axs[1].set_xlim(-40,1064)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_title('{} filter transmission (MRS data)'.format(usedfilter),fontsize=12)
            for plot in range(2): axs[plot].tick_params(axis='both',labelsize=12)
            plt.tight_layout()

            plt.figure(figsize=(8,6))
            plt.plot(np.arange(1024),matched_wavls,label='wavelength-pixel transmission relation')
            plt.plot(straight_line(np.arange(1024),*popt),label='fit')
            plt.plot(cutoffpix,cutofflamb,'ro',label='reference wavelength-pixel pair')
            plt.vlines(cutoffpix,7.4,8.4)
            plt.hlines(cutofflamb,-40,600)
            plt.xlim(-40,600)
            plt.ylim(7.4,8.4)
            plt.xlabel('Y coordinate [pix]',fontsize=12)
            plt.ylabel('Wavelength [micron]',fontsize=12)
            plt.suptitle('Cut-off wavelength {}micron located at pixel {}'.format(cutofflamb,round(cutoffpix,2) ),fontsize=12)
            plt.legend(loc='lower right')
            plt.tick_params(axis='both',labelsize=12)
            plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    elif band == '2B':
        # # define cut-off wavelength
        # cutofflamb = 8.74
        # # load spectrum from desired location and carry-out analysis
        # sci_fm_data = mrs_transmission
        # # Relate transmission values in wavelength space and in pixel space
        # matched_wavls = np.full(len(sci_fm_data),np.nan)
        #
        # for i in range(len(sci_fm_data)):
        #     matched_wavls[i] = filter_wave[np.abs(filter_transm-sci_fm_data[i]).argmin()]
        #
        # popt = np.polyfit(np.arange(len(sci_fm_data))[:80],matched_wavls[:80],1)
        # fit = np.poly1d(popt)
        # cutoffpix = (cutofflamb-popt[1])/popt[0]
        # if plot:
        #     fig,axs = plt.subplots(1,2,figsize=(12,4))
        #     axs[0].plot(filter_wave,filter_transm)
        #     axs[0].set_xlim(lamblower,lambupper)
        #     axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
        #     axs[0].set_ylabel('Transmission',fontsize=12)
        #     axs[0].set_title('{} filter transmission (lab data)'.format(usedfilter),fontsize=12)
        #     axs[1].plot(sci_fm_data[np.nonzero(sci_fm_data)],label='original data')
        #     axs[1].set_xlim(-40,1064)
        #     axs[1].set_xlabel('Y-pixel',fontsize=12)
        #     axs[1].set_title('{} filter transmission (MRS data)'.format(usedfilter),fontsize=12)
        #     for plot in range(2): axs[plot].tick_params(axis='both',labelsize=12)
        #     plt.tight_layout()
        #
        #     plt.figure(figsize=(8,6))
        #     plt.plot(np.arange(1024),matched_wavls,label='wavelength-pixel transmission relation')
        #     plt.plot(fit(np.arange(1024)),label='fit')
        #     plt.plot(cutoffpix,cutofflamb,'ro',label='reference wavelength-pixel pair')
        #     plt.vlines(cutoffpix,lamblower,lambupper)
        #     plt.hlines(cutofflamb,-10,90)
        #     plt.xlim(-10,90)
        #     plt.ylim(lamblower,8.81)
        #     plt.xlabel('Y-pixel',fontsize=12)
        #     plt.ylabel('Wavelength [micron]',fontsize=12)
        #     plt.suptitle('Cut-off wavelength {}micron located at pixel {}'.format(cutofflamb,round(cutoffpix,2) ),fontsize=12)
        #     plt.legend(loc='lower right')
        #     plt.tick_params(axis='both',labelsize=12)
        #     plt.tight_layout(rect=[0, 0.03, 1, 0.98])

        # load spectrum from desired location and carry-out analysis
        sci_fm_data = mrs_transmission

        # post-processing
        sci_fm_data[np.isnan(sci_fm_data)] = 0
        if band == '1C':
            # fit spline to data (smoother signal profile)
            spl = scp_interpolate.UnivariateSpline(np.arange(len(sci_fm_data[1:-1]) ),sci_fm_data[1:-1])
            spl.set_smoothing_factor(0.02)
            sci_fm_data = spl(np.arange(len(sci_fm_data)))

        # compute gradients and slopes
        filter_grad = np.gradient(filter_transm,filter_wave)
        filter_signs = np.sign(filter_grad)

        sci_fm_data_grad = np.gradient(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],51,3))
        sci_fm_data_signs = np.sign(sci_fm_data_grad)

        filter_zerocrossing = np.where(np.abs(np.diff(filter_signs)) == 2)[0]
        sci_fm_data_zerocrossing = np.where(np.abs(np.diff(sci_fm_data_signs)) == 2)[0]

        x0 = filter_wave[filter_zerocrossing[0]]
        x1 = filter_wave[filter_zerocrossing[0]+1]
        y0 = filter_grad[filter_zerocrossing[0]]
        y1 = filter_grad[filter_zerocrossing[0]+1]
        a = (y1-y0)/(x1-x0)
        cutofflamb = (-y0/a) + x0

        x0 = sci_fm_data_zerocrossing[0]
        x1 = np.arange(len(sci_fm_data))[sci_fm_data_zerocrossing[0]+1]
        y0 = sci_fm_data_grad[sci_fm_data_zerocrossing[0]]
        y1 = sci_fm_data_grad[sci_fm_data_zerocrossing[0]+1]
        a = (y1-y0)/(x1-x0)
        cutoffpix = (-y0/a) + x0

        if plot:
            fig,axs = plt.subplots(1,2,figsize=(12,4))
            axs[0].plot(filter_wave,filter_transm)
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('Transmission',fontsize=12)
            axs[0].set_title('{} filter transmission (lab data)'.format(usedfilter),fontsize=12)
            axs[1].plot(sci_fm_data[np.nonzero(sci_fm_data)],label='original data')
            axs[1].plot(savgol_filter(sci_fm_data[np.nonzero(sci_fm_data)],51,3),'r',label='smoothed data')
            axs[1].legend(loc='lower right',fontsize=12)
            axs[1].set_xlim(-40,1064)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_title('{} filter transmission (MRS data)'.format(usedfilter),fontsize=12)
            for plot in range(2): axs[plot].tick_params(axis='both',labelsize=12)
            plt.tight_layout()

            fig,axs = plt.subplots(2,1,figsize=(12,8))
            plt.suptitle('Cut-off wavelength {}micron located at pixel {}'.format(round(cutofflamb,2),round(cutoffpix,2) ),fontsize=12)
            lower0,upper0 = -0.001,0.007; lower1,upper1 = -0.004,0.013;
            axs[0].plot(filter_wave,np.gradient(filter_transm,filter_wave),'b')
            axs[0].hlines(0,lamblower,lambupper)
            axs[0].vlines(cutofflamb,lower0,upper0,linestyle='dashed',label='reference point')
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_ylim(lower0,upper0)
            axs[1].plot(sci_fm_data_grad,'r')
            axs[1].hlines(0,0,1024)
            axs[1].vlines(cutoffpix,lower1,upper1,linestyle='dashed',label='reference point')
            axs[1].set_xlim(0,1023)
            axs[1].set_ylim(lower1,upper1)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('INTA {} transm gradient'.format(usedfilter),fontsize=12)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_ylabel('FM {} transm gradient'.format(usedfilter),fontsize=12)
            for plot in range(2):
                axs[plot].tick_params(axis='both',labelsize=12)
                axs[plot].legend(loc='upper right',fontsize=12)
            plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    elif band == '2C':
        # load spectrum from desired location and carry-out analysis
        sci_fm_data = mrs_transmission
        sci_fm_data = interp_nans(sci_fm_data)

        # fit spline to data (smoother signal profile)
        spl = scp_interpolate.UnivariateSpline(np.arange(len(sci_fm_data[1:-1]) ),sci_fm_data[1:-1])
        spl.set_smoothing_factor(0.1)
        sci_fm_data = spl(np.arange(len(sci_fm_data)))

        # Reference wavelength/pixel pair defined by matching zero-crossing of gradient of INTA and FM LWP transmission
        sci_fm_data_grad = np.gradient(sci_fm_data)
        sci_fm_data_signs = np.sign(sci_fm_data_grad)

        sci_fm_data_zerocrossing = np.where(np.abs(np.diff(sci_fm_data_signs[870:920])) == 2)[0]

        cutofflamb = filter_wave[np.argmin(filter_transm)]

        x0 = 870+sci_fm_data_zerocrossing
        x1 = np.arange(len(sci_fm_data))[870+sci_fm_data_zerocrossing[0]+1]
        y0 = sci_fm_data_grad[sci_fm_data_zerocrossing[0]]
        y1 = sci_fm_data_grad[sci_fm_data_zerocrossing[0]+1]
        a = (y1-y0)/(x1-x0)
        cutoffpix = (-y0/a) + x0

        if plot:
            fig,axs = plt.subplots(1,2,figsize=(12,5))
            axs[0].plot(filter_wave,filter_transm)
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('Transmission',fontsize=12)
            axs[0].set_title('LWP filter transmission (lab data)',fontsize=12)
            axs[1].plot(mrs_transmission,label='original data')
            axs[1].plot(spl(np.arange(len(sci_fm_data))),'r',label='smoothed data')
            axs[1].legend(loc='lower right',fontsize=12)
            axs[1].set_xlim(-40,1064)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_title('LWP filter transmission (MRS data)',fontsize=12)
            for plot in range(2): axs[plot].tick_params(axis='both',labelsize=12)
            plt.tight_layout()

            fig,axs = plt.subplots(2,1,figsize=(12,8))
            plt.suptitle('Cut-off wavelength {}micron located at pixel {}'.format(round(cutofflamb,2),round(cutoffpix,2) ),fontsize=12)
            axs[0].plot(filter_wave,np.gradient(filter_transm,filter_wave),'b')
            axs[0].hlines(0,lamblower,lambupper)
            axs[0].vlines(cutofflamb,-0.0002,0.0002,linestyle='dashed',label='reference point')
            axs[0].set_xlim(lamblower,lambupper)
            axs[1].plot(np.gradient(spl(np.arange(1024))),'r')
            axs[1].hlines(0,633,1024)
            axs[1].vlines(cutoffpix,-0.001,0.001,linestyle='dashed',label='reference point')
            axs[1].set_xlim(633,1023)
            axs[1].set_ylim(-0.001,0.001)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=12)
            axs[0].set_ylabel('INTA LWP transm gradient',fontsize=12)
            axs[1].set_xlabel('Y-pixel',fontsize=12)
            axs[1].set_ylabel('FM LWP transm gradient',fontsize=12)
            for plot in range(2):
                axs[plot].tick_params(axis='both',labelsize=12)
                axs[plot].legend(loc='upper right',fontsize=12)
            plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    elif band == '4A':
        # load spectrum from desired location and carry-out analysis
        sci_fm_data = mrs_transmission
        sci_fm_data = interp_nans(sci_fm_data)

        # signal post-processing
        sci_fm_data = savgol_filter(sci_fm_data,201,2)

        # compute gradients and slopes
        filter_grad = np.gradient(filter_transm,filter_wave)

        sci_fm_data_grad = np.gradient(sci_fm_data)
        sci_fm_data_grad_filter = savgol_filter(sci_fm_data_grad,51,2)

        cutofflamb = filter_wave[np.argmax(filter_grad)]
        cutoffpix  = sci_fm_data_grad_filter.argmax() # wavelength maps of channels 3 and 4 are inverted!

        if plot:
            fig,axs = plt.subplots(1,2,figsize=(12,6))
            axs[0].plot(filter_wave,filter_transm,label='lab data transmission')
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_ylim(0,1.41)
            axs[0].tick_params(axis='both',labelsize=20)
            axs[0].legend(loc='upper right',framealpha=0.4,fontsize=14)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=20)
            axs[0].set_ylabel('Transmission',fontsize=20)
            axs[1].plot(mrs_transmission,label='FM transmission')
            axs[1].plot(sci_fm_data,label='filtered signal')
            axs[1].set_xlim(-40,1064)
            axs[1].set_ylim(0,1.41)
            axs[1].set_xlabel('Y-coordinate [pix]',fontsize=20)
            axs[1].tick_params(axis='both',labelsize=20)
            axs[1].legend(loc='upper right',framealpha=0.4,fontsize=14)
            plt.tight_layout()

            fig,axs = plt.subplots(2,1,figsize=(12,10))
            axs[0].plot(filter_wave,filter_grad)
            axs[0].hlines(0,lamblower,lambupper)
            axs[0].vlines(cutofflamb,-0.001,0.004)
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_ylim(-0.0002,0.001)
            # axs[1].plot(sci_fm_data_grad)
            axs[1].plot(sci_fm_data_grad_filter)
            axs[1].hlines(0,0,1024)
            axs[1].vlines(cutoffpix,-0.004,0.008)
            axs[1].set_xlim(0,1023)
            axs[1].set_ylim(-0.002,0.008)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=20)
            axs[0].set_ylabel('lab transm gradient',fontsize=20)
            axs[1].set_xlabel('Detector y-coord [pix]',fontsize=20)
            axs[1].set_ylabel('Transm gradient',fontsize=20)
            for plot in range(2):axs[plot].tick_params(axis='both',labelsize=20)
            plt.tight_layout()

    elif band == '4B':
        # load spectrum from desired location and carry-out analysis
        sci_fm_data = mrs_transmission
        sci_fm_data = interp_nans(sci_fm_data)

        # signal post-processing
        sci_fm_data = savgol_filter(sci_fm_data,51,2)

        # compute gradients and slopes
        filter_grad = np.gradient(filter_transm,filter_wave)

        sci_fm_data_grad = np.gradient(sci_fm_data)
        sci_fm_data_grad_filter = savgol_filter(sci_fm_data_grad,51,2)

        cutofflamb = filter_wave[np.argmin(filter_grad)]
        cutoffpix  = sci_fm_data_grad_filter.argmin() # wavelength maps of channels 3 and 4 are inverted!

        if plot:
            fig,axs = plt.subplots(1,2,figsize=(12,6))
            axs[0].plot(filter_wave,filter_transm,label='lab data transmission')
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_ylim(min(filter_transm),max(filter_transm))
            axs[0].tick_params(axis='both',labelsize=20)
            axs[0].legend(loc='upper right',framealpha=0.4,fontsize=14)
            axs[0].set_xlabel('Wavelength [micron]',fontsize=20)
            axs[0].set_ylabel('Transmission',fontsize=20)
            axs[1].plot(mrs_transmission,label='FM transmission')
            axs[1].plot(sci_fm_data,label='filtered signal')
            axs[1].set_xlim(-40,1064)
            axs[1].set_ylim(min(sci_fm_data),max(sci_fm_data))
            axs[1].set_xlabel('Y-coordinate [pix]',fontsize=20)
            axs[1].tick_params(axis='both',labelsize=20)
            axs[1].legend(loc='upper right',framealpha=0.4,fontsize=14)
            plt.tight_layout()

            fig,axs = plt.subplots(2,1,figsize=(12,10))
            axs[0].plot(filter_wave,filter_grad)
            axs[0].hlines(0,lamblower,lambupper)
            axs[0].vlines(cutofflamb,min(filter_grad),max(filter_grad))
            axs[0].set_xlim(lamblower,lambupper)
            axs[0].set_ylim(min(filter_grad),max(filter_grad))
            # axs[1].plot(sci_fm_data_grad)
            axs[1].plot(sci_fm_data_grad_filter)
            axs[1].hlines(0,0,1024)
            axs[1].vlines(cutoffpix,min(sci_fm_data_grad_filter),max(sci_fm_data_grad_filter))
            axs[1].set_xlim(0,1023)
            axs[1].set_ylim(min(sci_fm_data_grad_filter),max(sci_fm_data_grad_filter))
            axs[0].set_xlabel('Wavelength [micron]',fontsize=20)
            axs[0].set_ylabel('lab transm gradient',fontsize=20)
            axs[1].set_xlabel('Detector y-coord [pix]',fontsize=20)
            axs[1].set_ylabel('Transm gradient',fontsize=20)
            for plot in range(2):axs[plot].tick_params(axis='both',labelsize=20)
            plt.tight_layout()


    return cutofflamb,cutoffpix

#--slice offset
def slice_pix_offset(band,ref_source_img,second_source_img,pos_of_ref='right',plot=False):
    from scipy.interpolate import interp1d
    # select range of pixels
    if band[0] in ['1','4']: lower,upper = 10,502
    elif band[0] in ['2','3']: lower,upper = 522,1010

    pix_offsets = []
    rows = np.arange(50,1000,50)
    for row in np.arange(50,1000,50):
        sci_fm_data_ref = ref_source_img[row,:][lower:upper]

        # create a finer grid
        step = 0.02
        fine_grid = np.arange(lower,upper-1+step,step)
        sci_fm_data_ref_fine = interp1d(lower+np.arange(len(sci_fm_data_ref)),sci_fm_data_ref)(fine_grid)

        offsets = np.arange(1,100)
        wider_offsets = np.arange(-40,100)

        sci_fm_data = second_source_img[row,:][lower:upper]
        sci_fm_data_fine = interp1d(lower+np.arange(len(sci_fm_data)),sci_fm_data)(fine_grid)

        # polynomial fit order
        residuals = []
        for offset in offsets:
            if pos_of_ref=='right':
                residuals.append(np.sum(((sci_fm_data_ref_fine[offset:]-sci_fm_data_fine[:-offset])[~np.isnan(sci_fm_data_ref_fine[offset:]-sci_fm_data_fine[:-offset])])[:-100]**2))
            elif pos_of_ref=='left':
                residuals.append(np.sum(((sci_fm_data_fine[offset:]-sci_fm_data_ref_fine[:-offset])[~np.isnan(sci_fm_data_fine[offset:]-sci_fm_data_ref_fine[:-offset])])[:-100]**2))
        residuals = np.array(residuals)

        popt     = np.polyfit(offsets,residuals,4)
        poly     = np.poly1d(popt)

        pix_offset = wider_offsets[np.argmin(poly(wider_offsets))]*step
        pix_offsets.append(pix_offset)

        if plot:
            if row == 500.:
                plt.figure(figsize=(12,4))
                plt.title('Row {}'.format(row))
                plt.plot(sci_fm_data_ref_fine,label='FM data')
                plt.plot(sci_fm_data_fine,label='CV3 data')
                plt.legend(loc='lower right')
                plt.tight_layout()

                plt.figure(figsize=(12,4))
                plt.title('Row {}'.format(row))
                plt.plot(offsets*step,residuals,'bo')
                plt.plot(wider_offsets*step,poly(wider_offsets),'r')
                plt.xlabel('Slice pixel offset [pix]')
                plt.ylabel(r'residuals^2')
                plt.tight_layout()
    if plot:
        plt.figure(figsize=(12,4))
        plt.plot(np.arange(50,1000,50),pix_offsets,'bo')
        plt.xlabel('Detector row')
        plt.ylabel('Slice pixel offset [pix]')
        plt.tight_layout()

    pix_offsets = np.array(pix_offsets)
    return rows,pix_offsets
