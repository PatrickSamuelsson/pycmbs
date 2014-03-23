# -*- coding: utf-8 -*-
"""
This file is part of pyCMBS. (c) 2012-2014
For COPYING and LICENSE details, please refer to the file
COPYRIGHT.md
"""

import numpy as np
import os
import scipy as sci
from scipy import stats

from matplotlib import pylab as plt

from mpl_toolkits.axes_grid import make_axes_locatable
import matplotlib.axes as maxes
import matplotlib.cm as cm
import matplotlib.colors as col
import matplotlib as mpl
from pycmbs.plots import pm_bar, add_nice_legend
from pycmbs.mapping import map_plot
from pycmbs.data import Data
from scipy import linalg, dot
import matplotlib.gridspec as gridspec
from pycmbs.anova import *
from pycmbs.taylor import Taylor
### from pylab import *
import pickle


class DiagnosticMaster(object):
    """
    a master class for diganostics
    """
    def __init__(self, **kwargs):
        pass


class PatternCorrelation(DiagnosticMaster):
    """
    a class to perform pattern correlation diagnostics
    it calculates for each timestep the correlations between the spatial
    fields and allows to vizualize results in different ways
    """
    def __init__(self, x, y, ax=None, figure=None, figsize=(10, 3), **kwargs):
        """
        Parameters
        ----------
        x : Data
            first dataset
        y : Data
            second dataset
        ax : axis
            axis to plot to. If not specified, then a new  figure will
            be generated
        figsize : tuple
            figure size
        """
        super(PatternCorrelation, self).__init__(**kwargs)
        if not isinstance(x, Data):
            raise ValueError('Variable X is not a Data object')
        if not isinstance(y, Data):
            raise ValueError('Variable X is not a Data object')
        if x.shape != y.shape:
            print(x.shape)
            print(y.shape)
            raise ValueError('Invalid geometries!')

        if (ax is not None) and (figure is not None):
            raise ValueError('You can either specify the axis OR the figure, but not both!')

        if (ax is None) and (figure is None):
            f = plt.figure(figsize=figsize)
            self.ax = f.add_subplot(111)
        elif (ax is None) and (figure is not None):
            self.ax = figure.add_subplot(111)
        elif (ax is not None) and (figure is None):
            self.ax = ax
        else:
            raise ValueError('This option was not foreseen so far')

        self.figure = self.ax.figure

        self.x = x
        self.y = y
        self._calculated = False

        if self.x.ndim == 2:
            self.t = None
        elif self.x.ndim == 3:
            self.t = np.arange(self.x.nt) + 1
        else:
            raise ValueError('Invalid geometry')

    def _correlate(self):
        """
        perform correlation analysis for each timestep

        Todo
        ----
        * calculate here all information needed to draw results also
          in Taylor diagram
        """
        if self.x.ndim == 2:
            slope, intercept, r_value, p_value, std_err = stats.mstats.linregress(self.x.data[:, :].flatten(), self.y.data[:, :].flatten())
            self.slope = np.asarray([slope])
            self.r_value = np.asarray([r_value])
            self.intercept = np.asarray([intercept])
            self.p_value = np.asarray([p_value])
            self.std_err = np.asarray([std_err])
        elif self.x.ndim == 3:
            r = np.asarray([stats.mstats.linregress(self.x.data[i, :, :].flatten(), self.y.data[i, :, :].flatten()) for i in xrange(self.x.nt)])
            self.slope = np.asarray(r[:, 0])
            self.intercept = np.asarray(r[:, 1])
            self.r_value = np.asarray(r[:, 2])
            self.p_value = np.asarray(r[:, 3])
            self.std_err = np.asarray(r[:, 4])
        else:
            raise ValueError('Unsupported geometry')

        self._calculated = True

    def plot(self, ax=None, plot='line', **kwargs):
        """
        generate correlation plot

        Parameters
        ----------
        ax : axis
            axis to plot to. If not specified, a new figure
            will be generated

        Todo
        ----
        * implement plotting in Taylor diagram
        """
        if plot not in ['polar', 'line']:
            raise ValueError('Invalid plot type.')
        if not self._calculated:
            self._correlate()

        # here we have already correlations calculated
        if plot == 'polar':
            self._draw_polar()
        elif plot == 'line':
            self._draw_line(**kwargs)
        else:
            raise ValueError('Invalid plot type!')

        if plot in ['polar', 'line']:
            self.ax.legend(loc='lower left', prop={'size': 10})
            self.ax.set_xlabel('timestep #')
            self.ax.set_ylabel('$r_{pears}$')
            self.ax.grid()
            self.ax.set_ylim(0.5, 1.)

        return self.ax.figure

    def _draw_polar(self):
        raise ValueError('Polar plot not finally implemented yet!')
        # todo how to deal with negative correlations !!!
        t = 2. * np.pi * self.t / float(len(self.t))
        ax.scatter(t, self.r)

    def _draw_line(self, **kwargs):
        self.ax.plot(self.t, self.r_value, **kwargs)

#-----------------------------------------------------------------------


class EOF(object):
    """
    main class to perform an EOF analysis

    the concept of the EOF analysis implemented here is that the vector space defined by the data is a spatial space!
    It is therefore contrary to what is described in terms of terminology in von Storch and Zwiers, 1999.

    The EOF coefficients or principal components are therefore spatial fields, while the eigenvectors correspond to the
    temporal evolution of the field. Thus don't get confused when reading the reference!

    REFERENCES:
    -----------
    [1] von Storch, H. & Zwiers, F.W., 1999. Statistical Analysis in Climate Research, chapter 13
    """

    def __init__(self, x0, allow_gaps=False, normalize=False, cov_norm=True, anomalies=False, area_weighting=True,
                 use_corr=False, use_svd=True):
        """
        constructor for EOF analysis

        Parameters
        ----------
        x0 : Data
            C{Data} object with a 3D data. The data is assumed to have
            structure [time,ny,nx]
        allow_gaps : bool
            specifies if data gaps are allowed. If True, then temporal gaps are allowed
            and are considered approprately when calculating the covariance matrix
            if FALSE, then only timeseries without any gaps will be used.
        normalize : bool
            normalize timeseries of data to unity
        cov_norm : bool
            normalize covariance by sample size (uses np.cov() ).
            This is the standard.
            If FALSE, then the covariance is estimated from matrix
            multiplication.
            This is especially needed for testing!
        use_corr : bool
            use correlation matrix for EOF calculations instead of
            covariance matrix (default = False)
        anomalies : bool
            specifies if calculation should be performed based on
            anomalies (mean removed)
        area_weighting : bool
            perform area weighting of data prior to analysis
        use_svd : bool
            use SVD for decomposition; if False, then eigenvalue
            decomposition for symmetric matrices (eigh)
            is used

        TODO how to deal with negative eigenvalues, which sometimes occur?

        REFERENCES
        ----------
        (1) Bjoernsson, H., Venegas, S.A. (1997): A Manual for EOF and SVD analyses of Climate Data. online available
        (2) NCL EOF example: http://www.ncl.ucar.edu/Applications/eof.shtml
        """

        print('*** EOF ANALYSIS ***')

        # check geometries
        if x0.data.ndim != 3:
            raise ValueError('EOF analysis currently only supported for 3D data matrices of type [time,ny,nx]')

        x = x0.copy()  # copy input data object as the data will be weighted!
        self._x0 = x  # preserve information on original data

        #/// reshape data [time,npoints] ///
        self._shape0 = x.data[0, :, :].shape  # original data shape
        n = len(x.data)  # number of timestamps
        self.n = n

        # area weighting
        if area_weighting:
            wmat = np.sqrt(x._get_weighting_matrix())
        else:
            print '    WARNING: it is recommended to use area weighting for EOFs'
            wmat = np.sqrt(np.ones(x.data.shape))
        self._sum_weighting = np.sum(wmat)
        x.data *= wmat
        del wmat

        # estimate only valid data, discard any masked values
        if allow_gaps:
            lon, lat, vdata, msk = x.get_valid_data(return_mask=True, mode='one')
        else:
            lon, lat, vdata, msk = x.get_valid_data(return_mask=True, mode='all')

        self._x0mask = msk.copy()  # store mask applied to original data

        # reshape data
        self.x = vdata.copy()
        self.x.shape = (n, -1)  # time x npixels

        if anomalies:
            self._calc_anomalies()
        else:
            print '    WARNING: it is recommended that EOFs are calculated based on anomalies'

        if normalize:
            self.__time_normalization()  # results in unit variance for all data points

        # transpose data
        self.x = self.x.T  # [npoints,time]
        npoints, ntime = self.x.shape
        print '   EOF analysis with %s timesteps and %s grid cells ...' % (ntime, npoints)

        #/// calculate covariance matrix ///
        if allow_gaps:
            if use_corr:
                self.C = np.ma.corrcoef(self.x, rowvar=0)
            else:
                # calculation using covariance matrix
                if cov_norm:
                    self.C = np.ma.cov(self.x, rowvar=0)
                else:
                    raise ValueError('gappy data not supported for cov_norm option')
        else:
            if use_corr:
                self.C = np.corrcoef(self.x, rowvar=0)
            else:
                #--- covariance matrix for calculations
                if cov_norm:
                    self.C = np.cov(self.x, rowvar=0)
                else:
                    self.C = np.dot(self.x.T, self.x)

        #/// solve eigenvalue problem ///
        # The SVD implementation was validated by comparing U,l,V = svd(cov(x,rowvar=0)) against the results from
        # eigh(cov(x,rowvar=0)). Results are similar, WHICH IS A BIT STRANGE actually as after
        # Bjoernosson and Venegas, 1997, p. 17, the eigenvalues should correspond to the square of the singular values.
        # in the validdation, the eigenvalues however corresponded directly to the singular values!
        if use_svd:
            # Since the matrix is square and symmetric, eigenval(eof)=eigenval(svd)!
            self.eigvec, self.eigval, v = linalg.svd(self.C)
        else:
            #returns the eigenvalues in ASCENDING order (or no order at all!)
            # complex numbers in output matrices (eigenvalues not necessarily increasing!)
            self.eigval, self.eigvec = np.linalg.eigh(self.C)

        #self.eigvec /= self._sum_weighting #normalize Eigenvector with the sum of the weights that have been applied. This gives the timeseries mean amplitude (see NCL EOF example)
        #--- check if Eigenvalues are in descending order
        if np.any(np.diff(self.eigval) > 0.):
            print self.eigval
            raise ValueError('Eigenvalues are not in descending order. This is not supported yet so far.'
                             ' Needs ordering of results!')

        #/// calculate EOF expansion coefficients == PC (projection of original data to new parameter space)
        if allow_gaps:
            self.EOF = np.ma.dot(self.x, self.eigvec)  # A
        else:
            self.EOF = np.dot(self.x, self.eigvec)  # A

        #/// explained variance
        self._var = self.eigval / sum(self.eigval)  # explained variance

    def __time_normalization(self):
        """
        normalize timeseries x [time,position]
        by dividing by the standard deviation
        """
        nt, nx = np.shape(self.x)
        s = self.x.std(axis=0)  # temporal standard deviation
        S = np.repeat(s, nt).reshape(nx, nt).T  # generate array with all same std
        self.x /= S
        del S, s

    def _calc_anomalies(self):
        """
        calculate anomalies by removing temporal x [time,position]
        """
        nt, nx = np.shape(self.x)
        m = self.x.mean(axis=0)  # temporal mean
        M = np.repeat(m, nt).reshape(nx, nt).T
        self.x -= M
        del M, m

    def get_explained_variance(self):
        """
        Returns
        -------
        returns vector with explained variance
        ndarray
        """
        return self._var

    def plot_eof_coefficients(self, k, all=False, norm=False, ax=None, label=None, show_legend=True):
        """
        plot EOF coefficients = time series

        Paramters
        ---------
        k : list
            list of eof coefficients to be plotted
        all : bool
            plot all principle components (overwrites k)
        norm : bool
            normalize coefficients by stdv. to allow better plotting (default=True)
        """
        if all:
            k = range(self.n)
        else:
            if np.isscalar(k):
                k = [k]
        if ax is None:
            f = plt.figure()
            ax = f.add_subplot(111)
        else:
            f = ax.figure

        if label is None:
            label = ''
        else:
            label += ' '

        for i in k:
            y = self.eigvec[:, i].copy()
            if norm:
                y -= y.mean()
                y /= y.std()  # normalize to zero mean and unit std #todo: this kind of noramlization is not a standard. needs revision!
            ax.plot(self._x0.num2date(self._x0.time), y, label=label + 'EOF' + str(i + 1).zfill(3))  # caution: labeling is k+1

        if show_legend:
            ax.legend()

        return ax

    def plot_EOF(self, k, all=False, use_basemap=False, logplot=False,
                 ax=None, label=None, region=None, vmin=None,
                 vmax=None, show_coef=False, cmap=None, title=None, corr_plot=False, contours=False, norm=False, nclasses=10, levels=None):
        """
        plot multiple eof patterns

        Parameters
        ----------
        k : list or scalar
            scalar or list with principal component indices
        all : bool
            plot all principle components (overwrites k)
        logplot : bool
            take log of data for plotting
        show_coef : bool
            show coefficients in a separate plot
        corr_plot : bool
            normalize the EOF map, by correlating expansion coefficients
            with the data
        contours : bool
            specifies if contour plot shall be made instead of image
        norm : bool
            normalize EOFs like in NCDL ((former: data to plot EOFs in
            data units (see von Storch p. 298) NOT VALID ANY MORE)
        levels : list
            levels used for contour plotting (works only together with contours = True)
        """

        if all:
            k = range(self.n)
            ax = None
        else:
            if np.isscalar(k):
                k = [k]

        for i in k:
            if show_coef:
                f = plt.figure()
                gs = gridspec.GridSpec(2, 1, wspace=0.05, hspace=0.05, bottom=0.2, height_ratios=[5, 1])
                ax = f.add_subplot(gs[0])
                ax2 = f.add_subplot(gs[1])

            self._plot_single_EOF(i, use_basemap=use_basemap, logplot=logplot, ax=ax, label=label, region=region,
                                  vmin=vmin, vmax=vmax, cmap=cmap, title=title, corr_plot=corr_plot, contours=contours,
                                  norm=norm, nclasses=nclasses, levels=levels)
            if show_coef:
                self.plot_eof_coefficients(i, ax=ax2, show_legend=False, norm=False)
                ax2.grid()
                ti = ax2.get_yticks()
                n = len(ti) / 2
                ax2.set_yticks([ti[0], ti[n], ti[-1]])

        if show_coef:
            return f
        else:
            return None

#-----------------------------------------------------------------------------------------------------------------------

    def _plot_single_EOF(self, k, use_basemap=False, logplot=False, ax=None, label=None, region=None, vmin=None,
                         vmax=None, cmap=None, title=None, corr_plot=False, contours=False, norm=False,
                         nclasses=10, levels=None):
        """
        plot principal component k

        Parameters
        ----------
        k : int
            number of principal component to plot
        use_basemap : bool
            do plot using Basemap
        logplot : bool
            take log of data for plotting
        corr_plot : bool
            normalize the EOF map, by correlating expansion coefficients
            with the data
        contours : bool
            specifies if contour plot shall be made instead of image
        norm : bool
            normalize data to plot EOFs in data units
            (see von Storch p. 298) todo: validate if this really works
        nclasses : int
            number of classes for plotting
        levels : list
            levels used for contour plotting (works only together with
            contours = True)

        REFERENCES:
        -----------
        [1] NCAR EOF example: http://www.ncl.ucar.edu/Applications/eof.shtml

        """
        if k < 0:
            raise ValueError('k<0')

        if label is None:
            label = ''
        else:
            label += ' '

        if ax is None:
            f = plt.figure()
            ax = f.add_subplot(111)

        # remap data back to original shape
        #1) valid data --> all data
        hlp = np.zeros(len(self._x0mask)) * np.nan
        hlp[self._x0mask] = self.EOF[:, k].copy()
        #2) vector --> matrix
        hlp.shape = self._shape0
        hlp = np.ma.array(hlp, mask=np.isnan(hlp))

        if norm:
            ########normalize EOF pattern to represent physical units (see von Storch, p.298) NOT USED!!!
            #print '    WARNING: normalization is not validated yet!' #todo
            #hlp *= np.sqrt(self.eigval[k]) #von STORCH !!!

            #normalization like in NCL
            #The returned values are normalized such that the sum of squares for each EOF pattern equals one.
            #To denormalize the returned EOFs multiply by the square root of the associated eigenvalue
            #aka,the singular value).
            hlp /= np.sqrt(self.eigval[k])  # todo not sure if this really works!
            print 'WARNING, not sure if this normalization of EOF makes sense!'

        #/// normalize EOF timeseries by multiplying with the stdv of the principal components
        #this gives results which are similar to what the CDOs do (@todo: validate again, but fits well with NCL example [1])
        hlp *= self.eigvec[:, k].std()

        #/// calculate normalized EOFs by correlation of data with expansion coefficients ///
        if corr_plot:
            if norm:
                raise ValueError('Data normalization and correlation plot does not make sense and is not'
                                 ' supported therefore')
            #todo that can be done also more efficiently using matrix methods I guess
            Rout, Sout, Iout, Pout, Cout = self._x0.corr_single(self.eigvec[:, k])
            D = Rout.copy()
            D.unit = None
            del Rout, Sout, Iout, Pout, Cout
        else:
            #pyCMBS data object
            D = self._x0.copy()
            D.data = hlp
            D.unit = None  # reset units as EOF have no physical units

        D.label = label + 'EOF ' + str(k + 1).zfill(3) + ' (' + str(round(self._var[k] * 100., 2)) + '%)'  # caution: labeling is always k+1!

        map_plot(D, use_basemap=use_basemap, logplot=logplot, ax=ax, region=region, vmin=vmin, vmax=vmax,
                 cmap_data=cmap, title=title, contours=contours, nclasses=nclasses, levels=levels)

    def reconstruct_data(self, maxn=None, input=None):
        """
        reconstruct data from EOFs

        Parameters
        ----------
        maxn : int
            specifies the truncation number for EOF reconstruction
        input : int
            if this argument is given, then the reconstruction is based
            on the modes specified in this list. It can be an arbitrary
            list of mode valid mode indices
        """

        sh = (self.n, np.prod(self._shape0))
        F = np.zeros(sh)

        #- reconsturction list
        if input is None:
            #use all data up to maxn
            if maxn is None:
                maxn = self.n
            thelist = range(maxn)
        else:
            #use user defined list
            thelist = input

        #- reconstruct data matrix
        for i in thelist:
            #~ a = np.asarray([self.EOF[:,i]]).T
            #remap to original geometry first
            hlp = np.zeros(len(self._x0mask)) * np.nan
            hlp[self._x0mask] = self.EOF[:, i].copy()

            a = np.asarray([hlp]).T
            c = np.asarray([self.eigvec[:, i]])
            F += np.dot(a, c).T

        #- generate data object to be returned
        D = self._x0.copy()
        F.shape = self._x0.data.shape
        D.data = np.ma.array(F, mask=np.isnan(F))

        return D

#-----------------------------------------------------------------------

    def get_correlation_matrix(self):
        """
        correlation matrix of original data [ntimes,ntimes]
        """
        return np.corrcoef(self.x, rowvar=0)

    def get_eof_data_correlation(self, plot=True):
        """
        get correlation between original data and PCs
        """

        c = np.corrcoef(self.x, self.EOF, rowvar=0)  # correlate PCS and original data
        c1 = c[self.n:, 0:self.n]
        if plot:
            f = plt.figure()
            ax = f.add_subplot(111)

            im = ax.imshow(c1 ** 2, interpolation='nearest', vmin=0, vmax=1., origin='lower')
            plt.colorbar(im)
            ax.set_title('$R^2$ of EOFs with original data')
            ax.set_xlabel('original data channel #')
            ax.set_ylabel('PC #')

    def plot_channnel_correlations(self, samp):
        """
        generate a scatterplot of correlations of call channles vs. each other

        Parameters
        ----------
        samp : int
            stepsize for subsampling of data for faster plotting
        """

        f = plt.figure()
        cnt = 1
        for i in range(self.n):
            x = self.x[::samp, i]
            for j in xrange(self.n):
                print i, j
                y = self.x[::samp, j]
                if j >= i:
                    ax = f.add_subplot(self.n, self.n, cnt)
                    #~ ax.set_aspect('equal')
                    ax.hexbin(x, y, mincnt=1, bins='log')
                    ax.set_ylim(ax.get_xlim())
                    ax.set_xticks([])
                    ax.set_yticks([])
                cnt += 1

        f.subplots_adjust(wspace=0., hspace=0., right=1., left=0., bottom=0., top=1.)

        return f


#-----------------------------------------------------------------------
class ANOVA(object):
    """
    main class to perform an ANOVA analysis
    using C{Data} objects

    treatments are derived from data timeseries
    blocks are obtained by different experiments
    """
    def __init__(self):
        self.experiments = []
        self.data = {}

    def add_experiment(self, label):
        self.experiments.append(self.__trim(label))
        self.data.update({self.__trim(label): []})

    def __trim(self, s):
        return s.replace(' ', '_')

    def add_data(self, e, d):
        """
        adds data for each experiment to a list
        """
        k = self.__trim(e)  # experiment key
        if k in self.experiments:
            #experiment was registered
            #~ has_mask = True
            #~ try: #this is a hack; how to do it better ??? #TODO !!!!
                #~ d.data.shape == d.mask.shape
            #~ except:
                #~ has_mask = False
            #~ if not has_mask:
                #~ print d.data
                #~ print e
                #~ raise ValueError, 'All data objects need to me masked arrays!' #this is needed,as
                # otherwise common mask generation is not possible
            self.data[k].append(d)
        else:
            raise ValueError('Experiment was not yet registered!')

    def analysis(self, analysis_type=None):
        """
        perform ANOVA analysis based on the data given
        """

        if analysis_type is None:
            raise ValueError('Needs to specify type of ANOVA to be performed')

        #1) check if all data has the same length
        # this is not a strong prerequesite for ANOVA as such, but for
        # the implementation here
        # generate a common mask with points that are valid throughout
        # all timesteps and are not masked
        self._get_valid_mask()  # --> self.mask

        #2) rearange data to work only with valid (not masked data)
        #   check also that only data which is valid in all cases is used
        #   it is realized by getting the valid indices of the data
        idx = np.argwhere(self.mask)  # returns list of indices of valid pixels

        #3) perform ANOVA analysis on all pixels individually
        resA = np.zeros(self.refshape) * np.nan
        resB = np.zeros(self.refshape) * np.nan
        resI = np.zeros(self.refshape) * np.nan
        resE = np.zeros(self.refshape) * np.nan
        resPA = np.zeros(self.refshape) * np.nan
        resPB = np.zeros(self.refshape) * np.nan
        resPI = np.zeros(self.refshape) * np.nan

        resAa = np.zeros(self.refshape) * np.nan
        resBa = np.zeros(self.refshape) * np.nan
        resIa = np.zeros(self.refshape) * np.nan

        for p in idx:
            if analysis_type == 'one':  # one way ANOVA
                m = self._data2anova1(p)  # [nrens,ntime]
                A = Anova1(m)
                A.one_way_anova(verbose=False)

                resA[p[0], p[1]] = A.get_fractional_variance_explained(adjust=False)  # ssa
                resPA[p[0], p[1]] = A.p
                resB[p[0], p[1]] = A.sse / A.sst  # todo: adjustment here ???

            elif analysis_type == 'two':  # two way ANOVA
                m = self._data2anova2(p)
                #- perform 2-way anova
                A = Anova2(m)
                A.two_way_anova_with_replication()

                resA[p[0], p[1]] = A.get_fractional_variance_explained('a', adjust=False)  # todo: adjust variance
                resB[p[0], p[1]] = A.get_fractional_variance_explained('b', adjust=False)  # todo: adjust variance
                resI[p[0], p[1]] = A.get_fractional_variance_explained('i', adjust=False)  # todo: adjust variance
                resE[p[0], p[1]] = A.get_fractional_variance_explained('e', adjust=False)  # todo: adjust variance

                resPA[p[0], p[1]] = A.p_ssa
                resPB[p[0], p[1]] = A.p_ssb
                resPI[p[0], p[1]] = A.p_ssi

                #~ resAa[p[0],p[1]] = A.get_fractional_variance_explained('a',adjust=True) #todo: adjust variance
                #~ resBa[p[0],p[1]] = A.get_fractional_variance_explained('b',adjust=True) #todo: adjust variance
                #~ resIa[p[0],p[1]] = A.get_fractional_variance_explained('i',adjust=True) #todo: adjust variance

                #@todo significance

            else:
                raise ValueError('Invalid ANOVA type')

        self.resA = resA
        self.resB = resB
        self.resI = resI
        self.resE = resE

        self.resPA = resPA
        self.resPB = resPB
        self.resPI = resPI

        self.resAa = resAa
        self.resBa = resBa
        self.resIa = resIa

    def _data2anova1(self, p):
        """
        extract from the database all the data
        relevant for a single location, given by the indices in p

        p = indices

        ---> time (nt)
        |
        |
        v experiment (nexp)
        """

        nexp = len(self.experiments)

        if nexp != 1:
            raise ValueError('one-way anova only valid for signle experiments!')

        x = np.zeros((self.n, self.nt)) * np.nan  # [nrens,nt]

        e = self.experiments[0]
        for i in range(self.n):
            d = self.data[e][i]  # data object for experiment 'e' and ensemble nr [i]
            x[i, :] = d.data[:, p[0], p[1]]

        if np.any(np.isnan(x) > 0):
            raise ValueError('Something is wrong: not all data valid!')

        return x

    def _data2anova2(self, p):
        """
        extract from the database all the data
        relevant for a single location, given by the indices in p

        p = indices

        ---> time (nt)
        |
        |
        v experiment (nexp)
        """
        nexp = len(self.experiments)
        x = np.zeros((nexp, self.nt, self.n)) * np.nan

        for j in range(len(self.experiments)):
            e = self.experiments[j]
            for i in range(self.n):
                d = self.data[e][i]  # data object for experiment 'e' and ensemble nr [i]
                x[j, :, i] = d.data[:, p[0], p[1]]

        if np.any(np.isnan(x) > 0):
            raise ValueError('Something is wrong: not all data valid!')

        return x

    def _get_valid_mask(self):
        """
        generate a mask where all datasets are valid
        """
        #- check if geometry in general o.k.
        self.__same_geometry()

    def __same_geometry(self):
        """
        check if all data has the same geometry
        """
        cnt = 0
        for k in self.experiments:
            d = self.data[k]
            if cnt == 0:
                refshape = d[0].data.shape  # first dataset geometry as reference
                self.refshape = (refshape[1], refshape[2])
                nrens = len(d)
                self.n = nrens
                self.nt = refshape[0]
                refmsk = np.ones((refshape[1], refshape[2])).astype('bool')
                cnt += 1

            if len(d) != nrens:
                raise ValueError('Invalid Number of ensemble members found!')
            for i in range(len(d)):

                if d[i].data.shape != refshape:
                    print k, i
                    raise ValueError('Invalid data shape found!')

                #- generate common mask
                msk = d[i].get_valid_mask()
                #~ print sum(msk), k, i
                refmsk = refmsk & msk

        self.mask = refmsk

        return True

#-----------------------------------------------------------------------
#-----------------------------------------------------------------------


class SVD(object):
    """
    class to perform singular value decomposition analysis
    also known as Maximum covariance analysis (MCA)

    REFERENCES
    ==========
    1. Bjoernsson and Venegas: A manual for EOF and SVD analyses of Climate Data,
                           McGill University, available online
    """

    def __init__(self, X, Y, scf_threshold=0.01, label='', format='pdf'):
        """
        constructor for SVD class

        Parameters
        ----------

        X : Data
            x-variable field
        Y : Data
            y-variable field
        scf_threshold : float
            threshold for explained variance until which result maps
            are plotted
        label : str
            label for labeling figures
        format : str
            specifies the format of figures to be generated [png,pdf]
        """
        x = X.data.copy()
        y = Y.data.copy()  # these are masked arrays

        n = len(x)
        if n != len(y):
            raise ValueError('Datasets need to have same timelength!')

        x.shape = (n, -1)  # [time,position]
        y.shape = (n, -1)

        self.x = x
        self.y = y
        self.X = X
        self.Y = Y

        self.time = X.time.copy()
        self.label = label

        self.scf_threshold = scf_threshold  # threshold for explained variance until which result maps are plotted
        self.dpi = 150  # output dpi for plotting
        self.ext = format  # file extension for plotting
        self.use_basemap = False

#-----------------------------------------------------------------------

    def _get_valid_timeseries(self, x):
        """
        get only points where ALL
        timeseries are valid

        Parameters
        ----------
        x : ndarray
            numpy masked array with geometry [time,position]

        Returns
        -------
        masked array [time,nvalidpixels] and mask that can be applied
        to original data [norgpixels]
        """

        nt, n = x.shape
        mx = np.sum(~x.mask, axis=0) == nt  # get mask for valid pixels only
        m1 = mx

        r = np.ones((nt, sum(mx))) * np.nan
        for i in xrange(nt):
            tmp = x.data[i, :]
            if np.any(np.isnan(tmp[m1])):
                raise ValueError('Nans are not allowed here!')
            r[i, :] = tmp[m1] * 1.
            del tmp

        return np.ma.array(r), m1

#-----------------------------------------------------------------------

    def __detrend_time(self, x):
        """
        given a variable x[time,position]
        the data is linear detrended individually for each position

        Parameters
        ----------
        x : ndarray
            data array [time, position]

        Returns
        -------
        return detrended array [time, position]
        """

        if x.ndim != 2:
            raise ValueError('Invalid shape for detrending')
        n, m = x.shape
        for i in xrange(m):
            h = x[:, i].copy()
            h = plt.detrend_linear(h)
            x[:, i] = h.copy()
        return x

#-----------------------------------------------------------------------

    def __time_normalization(self, x):
        """
        normalize timeseries x [time,position]
        by dividing by the standard deviation

        Parameters
        ----------
        x : ndarray
            data array [time,position]

        Returns
        -------
        normalized timeseries numpy array
        """
        nt, nx = np.shape(x)
        s = x.std(axis=0)  # temporal standard deviation
        S = np.repeat(s, nt).reshape(nx, nt).T  # generate array with all same std
        x /= S
        del S, s
        return x

#-----------------------------------------------------------------------

    def svd_analysis(self, detrend=True, varnorm=False):
        """
        perform SVD analysis

        Parameters
        ----------
        detrend : bool
            detrend data
        varnorm : bool
            normalize variance of time series
        """

        #/// perform SVN only for data points which are valid throughout entire time series ///
        x, mskx = self._get_valid_timeseries(self.x)  # self.x is a masked array; returns an array [time,nvalid]
        y, msky = self._get_valid_timeseries(self.y)
        self.mskx = mskx
        self.msky = msky

        #/// detrend the data for each grid point ///
        print 'Detrending ...'
        if detrend:
            x = self.__detrend_time(x)
            y = self.__detrend_time(y)
        print 'Detrended!'

        #/// normalized each timeseries by its variance
        if varnorm:
            x = self.__time_normalization(x)
            y = self.__time_normalization(y)

        #/// calculate covariance matrix
        print 'Construct covariance matrix ...'
        C = dot(x.T, y)  # this covariance matrix does NOT contain the variances of the individual
        # grid points, but only the covariance terms!
        print 'Done!'
        self.C = C
        self.x_used = x.copy()  # store vectors like they are used for SVD calculations
        self.y_used = y.copy()

        #/// singular value decomposition
        print '   Doing singular value decomposition xxxxxx ...'

        U, s, V = linalg.svd(C)
        print 'Done!'
        L = linalg.diagsvd(s, len(C), len(V))  # construct diagonal maxtrix such that U L V.T = C; this is
        # somewhat python specific

        #/// expansion coefficients (time series)
        A = dot(x, U)
        B = dot(y, V.T)  # ACHTUNG!!! SCHOULD BE B = dot(y,V)

        #/// store results
        self.U = U
        self.V = V
        self.L = L
        self.A = A
        self.B = B
        self.scf = (s * s) / sum(s * s)  # fractions of variance explained CAUTION: not properly described in manual if squared or not!
        self.__get_mode_correlation()  # calculate correlation between modes

#-----------------------------------------------------------------------

    def __get_mode_correlation(self):
        """
        calculate correlations between expansion modes
        of the two fields
        """
        self.mcorr = []
        for i in range(len(self.scf)):
            c = np.corrcoef(self.A[:, i], self.B[:, i])[0][1]
            self.mcorr.append(c)
        self.mcorr = np.asarray(self.mcorr)

#-----------------------------------------------------------------------

    def get_singular_vectors(self, mode):
        """
        return the singular vectors of both fields for a specific mode
        as a spatial (2D) field

        Parameters
        ----------
        mode : int
            mode to be shown

        Returns
        -------
        numpy arrays for U and V
        """

        #x_used is a vector that only contains the valid values that were used for caluclation of covariance matrix C
        #mskx is the corresponding mask that maps x_used to the original geometry (both are estimated with
        # _get_valid_timeseries()  )
        u = self.U[:, mode]
        v = self.V[:, mode]  # get singular vectors

        #map singular vectors to 2D
        udat = self._map_valid2org(u, self.mskx, self.X.data[0, :, :].shape)
        vdat = self._map_valid2org(v, self.msky, self.Y.data[0, :, :].shape)

        U = self.X.copy()
        U.label = 'U(' + str(mode) + ')'
        U.data = udat.copy()

        V = self.Y.copy()
        V.label = 'V(' + str(mode) + ')'
        V.data = vdat.copy()

        return U, V

#-----------------------------------------------------------------------

    def _map_valid2org(self, data, mask, target_shape):
        """
        map valid data vector back to
        original data shape

        Parameters
        ----------
        data : ndarray
            data vector that was used for SVD calculations (1D)
        mask : ndarray
            1D data mask
        target_shape : tuple
            shape to map to
        """
        sz = np.shape(data)
        if sz[0] != mask.sum():
            print sz[1]
            print mask.sum()
            raise ValueError('Inconsistent mask and data')

        res = np.ones(target_shape) * np.nan
        res.shape = (-1)
        res[mask] = data.copy()

        res = np.ma.array(res, mask=np.isnan(res))
        res = np.reshape(res, target_shape)

        return res

#-----------------------------------------------------------------------

    def plot_var(self, ax=None, filename=None, maxvar=1.):
        """
        plot explained variance

        Parameters
        ----------
        ax : axis
            axis to put plot in. If None, then a new figure is generated
        filename : str
            name of the file to store figure to (if None, then no file is saved)
        maxvar : float
            upper limit of variance plot
        """

        def make_patch_spines_invisible(ax):
            #http://matplotlib.sourceforge.net/examples/pylab_examples/multiple_yaxis_with_spines.html
            ax.set_frame_on(True)
            ax.patch.set_visible(False)
            for sp in ax.spines.itervalues():
                sp.set_visible(False)

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
        else:
            ax = ax
            fig = ax.figure

        fig.subplots_adjust(right=0.75)

        ax1 = ax.twinx()  # axis for cumulated variance
        ax2 = ax.twinx()

        ax2.spines["right"].set_position(("axes", 1.2))
        make_patch_spines_invisible(ax2)
        ax2.spines["right"].set_visible(True)

        n = len(self.scf)
        ax.step(np.arange(n), self.scf, where='post')
        ax.set_ylabel('fraction of variance explained', color='blue')
        ax.set_xlabel('mode')
        ax.set_ylim(0., maxvar)
        ax.grid()

        ax1.plot(np.cumsum(self.scf), color='red')
        ax1.set_ylabel('cumulated variance [-]', color='red')
        ax1.set_ylim(0., 1.)

        ax2.plot(np.arange(n), self.mcorr, color='green')
        ax2.set_ylabel('mode correlation [-]', color='green')
        ax2.set_ylim(-1, 1.)
        ax2.grid(color='green')

        ax .tick_params(axis='y', colors='blue')
        ax1.tick_params(axis='y', colors='red')
        ax2.tick_params(axis='y', colors='green')

        if filename is not None:
            oname = filename + '_mode_var.' + self.ext
            ax.figure.savefig(oname, dpi=self.dpi)

#-----------------------------------------------------------------------

    def plot_singular_vectors(self, mode, use_basemap=False, logplot=False, filename=None):
        """
        generate maps of singular vectors U and V

        mode (list) : list of modes to be plotted
        """

        #--- mode list
        if mode is None:  # plot all modes with variance contained
            mode_list = []
            for i in range(len(self.scf)):
                if self.scf[i] > self.scf_threshold:
                    mode_list.append(i)
        else:
            mode_list = [mode]

        #--- generate plots
        for i in mode_list:
            fig = plt.figure()
            ax1 = fig.add_subplot(121)
            ax2 = fig.add_subplot(122)

            U, V = self.get_singular_vectors(i)  # get singular vector fields

            #--- determine min/max values
            mu = U.data.mean()
            su = U.data.std()
            mv = V.data.mean()
            sv = V.data.std()

            su *= 1.96
            sv *= 1.96  # not used at the moment

            if logplot:
                umin = None
                umax = None
                vmin = None
                vmax = None
            else:
                umin = mu - su
                umax = mu + su
                vmin = mv - sv
                vmax = mv + sv

            map_plot(U, use_basemap=use_basemap, ax=ax1, logplot=logplot, vmin=umin, vmax=umax)
            map_plot(V, use_basemap=use_basemap, ax=ax2, logplot=logplot, vmin=vmin, vmax=vmax)

            fig.suptitle('Mode: #' + str(i) + ' scf: ' + str(round(self.scf[i] * 100., 1)) + '%', size=14)

            if filename is not None:
                fig.savefig(filename + '_singular_vectors_mode_' + str(i).zfill(5) + '.pdf')

#-----------------------------------------------------------------------

    def plot_correlation_map(self, mode, ax1in=None, ax2in=None, pthres=1.01, plot_var=False, filename=None,
                             region1=None, region2=None, regions_to_plot=None):
        """
        plot correlation map of an SVN mode
        with original data

        mode specifies the number of the mode that should be correlated

        ctype specifies if homogeneous (homo) or heterogeneous (hetero)
        correlations shall be calculated. Homogeneous, means correlation
        of expansion coefficients with the same geophysical field, while
        heterogeneous means correlation with the other geophysical field

        pthres specifies the significance level. Values > pthres will be masked
        if you want to plot e.g only points with significant correlation at p < 0.05, then
        set pthres = 0.05

        plot_var: plot variance instead of correlation
        """

        n1, m1 = self.A.shape
        n2, m2 = self.B.shape

        if mode is not None:
            if mode > m1 - 1:
                raise ValueError('Mode > A')
            if mode > m2 - 1:
                raise ValueError('Mode > B')

        if mode is None:  # plot all modes with variance contained
            mode_list = []
            for i in xrange(len(self.scf)):
                if self.scf[i] > self.scf_threshold:
                    mode_list.append(i)
        else:
            mode_list = [mode]

        def plot_cmap(R, ax, title, vmin=-1., vmax=1., plot_var=False, use_basemap=False, region=None,
                      cmap='RdBu_r', cticks=None, regions_to_plot=None):
            """
            R data object
            """

            if plot_var:
                O = R.copy()
                O.data = O.data * O.data
                O.label = 'exp.frac.var.'
            else:
                O = R.copy()
                O.label = 'correlation'

            #calculate mean and stdv
            O.label = O.label + ' (' + str(round(O.data.mean(), 2)) + ' ' + str(round(O.data.std(), 2)) + ')'

            map_plot(O, use_basemap=use_basemap, ax=ax, region=region, cmap_data=cmap, vmin=vmin, vmax=vmax, cticks=cticks, title=title, regions_to_plot=regions_to_plot, show_stat=True)

        #/// calculate correlations and do plotting
        for i in mode_list:
            fig = plt.figure(figsize=(6, 8))
            ax1a = fig.add_subplot(421)  # homogeneous plots
            ax1b = fig.add_subplot(423)
            ax1c = fig.add_subplot(425)

            ax2a = fig.add_subplot(422)  # heterogeneous plots
            ax2b = fig.add_subplot(424)
            ax2c = fig.add_subplot(426)

            ax3 = fig.add_subplot(515)  # expansion coefficients

            #homogeneous correlations
            Rout1_ho, Sout1_ho, Iout1_ho, Pout1_ho, Cout1_ho = self.X.corr_single(self.A[:, i], pthres=pthres)
            Rout2_ho, Sout2_ho, Iout2_ho, Pout2_ho, Cout2_ho = self.Y.corr_single(self.B[:, i], pthres=pthres)

            #heterogeneous correlations
            Rout1_he, Sout1_he, Iout1_he, Pout1_he, Cout1_he = self.X.corr_single(self.B[:, i], pthres=pthres)
            Rout2_he, Sout2_he, Iout2_he, Pout2_he, Cout2_he = self.Y.corr_single(self.A[:, i], pthres=pthres)

            #R #output matrix for correlation
            #P #output matrix for p-value
            #S #output matrix for slope
            #I #output matrix for intercept
            #C #output matrix for covariance

            #--- plot maps
            print 'Starting map plotting'
            #homogeneous
            plot_cmap(Rout1_ho, ax1a, 'correlation (homo) ' + self.X.label, plot_var=False,
                      use_basemap=self.use_basemap, region=region1, vmin=-0.8, vmax=0.8, cmap='RdBu_r',
                      cticks=[-1., -0.5, 0., 0.5, 1.], regions_to_plot=regions_to_plot)  # correlation field 1
            plot_cmap(Rout2_ho, ax1b, 'correlation (homo) ' + self.Y.label, plot_var=False,
                      use_basemap=self.use_basemap, region=region2, vmin=-0.8, vmax=0.8, cmap='RdBu_r',
                      cticks=[-1., -0.5, 0., 0.5, 1.], regions_to_plot=regions_to_plot)  # correlation field 2
            plot_cmap(Rout2_ho, ax1c, 'exp.frac.var (homo)', plot_var=True,
                      use_basemap=self.use_basemap, region=region2, vmin=0., vmax=0.6, cmap='YlOrRd',
                      cticks=[0., 0.25, 0.5], regions_to_plot=regions_to_plot)  # explained variance field 2

            #heterogeneous
            plot_cmap(Rout1_he, ax2a, 'correlation (hetero) ' + self.X.label, plot_var=False,
                      use_basemap=self.use_basemap, region=region1, vmin=-0.8, vmax=0.8, cmap='RdBu_r',
                      cticks=[-1., -0.5, 0., 0.5, 1.], regions_to_plot=regions_to_plot)  # correlation field 1
            plot_cmap(Rout2_he, ax2b, 'correlation (hetero) ' + self.Y.label, plot_var=False,
                      use_basemap=self.use_basemap, region=region2, vmin=-0.8, vmax=0.8, cmap='RdBu_r',
                      cticks=[-1., -0.5, 0., 0.5, 1.], regions_to_plot=regions_to_plot)  # correlation field 2
            plot_cmap(Rout2_he, ax2c, 'exp.frac.var (hetero)', plot_var=True,
                      use_basemap=self.use_basemap, region=region2, vmin=0., vmax=0.6, cmap='YlOrRd',
                      cticks=[0., 0.25, 0.5], regions_to_plot=regions_to_plot)  # explained variance field 2

            #expansion coefficients
            self.plot_expansion_correlation(i, ax=ax3)

            #figure title
            fig.suptitle(self.label + ': Mode: #' + str(i) + ' (scf: ' + str(round(self.scf[i], 2)) + ')', size=14)
            fig.subplots_adjust(wspace=0.0, hspace=0.5)
            fig.set_figheight(10.)

            #--- save figure
            if filename is not None:
                oname = filename + '_mode_' + str(i) + '.' + self.ext
                ax1a.figure.savefig(oname, dpi=self.dpi)

#-----------------------------------------------------------------------

    def _get_variance_field(self, X, E, mode, pthres=1.01):
        """
        calculate variance field for a particular mode
        (explained variance by a particular expansion mode)
        This is obtained by correlating an expansion mode to
        a particular data field

        Parameters
        ----------
        X : Data
            data field that should be explained by expansion coefficient
        E : ndarray
            expansion cofficient to be used for correlation calculation

        Returns
        -------
        squared correlation as C{Data} object
        """
        Rout, Sout, Iout, Pout = X.corr_single(E[:, mode], pthres=pthres)
        Rout.data = Rout.data * Rout.data
        return Rout  # return squared correlation to get variance

#-----------------------------------------------------------------------

    def reconstruct_variance_fraction(self, X, E, mode_list, pthres=1.01):
        """
        reconstruct variance of data based on
        a list of modes that should be used
        for that purpose.

        The variances of the different modes are added
        assuming that they are indpendent of each other

        mode_list : list with up to N modes

        X Data object
        E expansion coefficients (data object)

        returns:
        array with variance
        """

        O = None
        for mode in mode_list:
            V = self._get_variance_field(X, E, mode, pthres=pthres)
            if O is None:
                O = V.data
            else:
                O = O + V.data  # add variances

        O = np.ma.array(O, mask=np.isnan(O))

        return O

#-----------------------------------------------------------------------

    def print_mode_statistic(self, filename=None):
        """
        print statistic of modes

        Parameters
        ----------
        filename : str
            filename to save table to
        """
        sep = ' & '
        rnd = 2
        self.__get_mode_correlation()  # calculate mode correlations

        if filename is not None:
            o = open(filename, 'w')
            o.write('mode' + sep + 'scf' + sep + 'r' + ' \\\ ' + '\n')

        for i in np.arange(len(self.scf)):
            if self.scf[i] > self.scf_threshold:
                print i, self.scf[i], self.mcorr[i]
                if filename is not None:
                    s = str(i) + sep + str(np.round(self.scf[i], rnd)) + sep \
                        + str(np.round(self.mcorr[i], rnd)) + ' \\\ ' + '\n'
                    o.write(s)

        if not filename is None:
            o.close()

#-----------------------------------------------------------------------

    def plot_expansion_correlation(self, mode, ax=None):
        """
        plot correlation and time series of expansion coeffcients

        mode : int
            mode to plot
        ax : axis
            axis to plot data
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
        else:
            ax = ax

        ax.plot(self.num2date(self.time), self.A[:, mode] / np.std(self.A[:, mode]), label='A', color='red')
        ax.plot(self.num2date(self.time), self.B[:, mode] / np.std(self.B[:, mode]), label='B', color='blue', linestyle='--')
        c = np.corrcoef(self.A[:, mode], self.B[:, mode])[0][1]
        plt.legend()
        ax.set_title('normalized expansion coefficient #' + str(mode) + ' (r=' + str(round(c, 2)) + ')', size=10)
        ax.set_xlabel('time')
        ax.set_ylim(-3., 3.)

#-----------------------------------------------------------------------
#-----------------------------------------------------------------------


class Diagnostic(object):
    def __init__(self, x, y=None):
        """
        constructor for diagnostic class
        diagnostic for one or multiple data sets

        x : Data
            x data to be analyzed
        y : Data
            y data to be analyzed
       """
        self.x = x
        if y is not None:
            self.y = y

#-----------------------------------------------------------------------

    def get_n(self):
        """
        return the number of valid samples
        """
        xm = ~self.xvec.mask  # vector with valid sample
        ym = ~self.yvec.mask
        m = xm & ym
        return sum(m)

#-----------------------------------------------------------------------

    def get_rmse_value(self):
        """
        calculate root-mean-squared error
        """
        return np.sqrt(np.mean((self.xvec - self.yvec) ** 2))

#-----------------------------------------------------------------------

    def lagged_correlation_vec(self, lags, pthres=1.01, detrend_linear=False, detrend_mean=False):
        """
        lagged correlation for two vectors

        x,y Data objects, where data needs to have been pre-processed
        to be a single vector

        lags: list of lags
        """

        if self.x.data.shape != self.y.data.shape:
            raise ValueError('Invalid geometries!')

        if not plt.isvector(self.x.data):
            raise ValueError('Routine works only with vectorized data!')

        if any(lags < 0.):
            raise ValueError('Negative lags currently not supported yet!')

        CO = []
        for lag in lags:
            hlpx = self.x.data.copy()
            hlpy = self.y.data.copy()

            if detrend_linear:
                hlpx = plt.detrend_linear(hlpx)
                hlpy = plt.detrend_linear(hlpy)
            if detrend_mean:
                hlpx = plt.detrend_mean(hlpx)
                hlpy = plt.detrend_mean(hlpy)

            #1) temporal subsetting of data
            if lag > 0:
                #temporal subset data
                hlpx = hlpx[lag:]
                hlpy = hlpy[:-lag]

            #2) calculation of lagged correlation
            if len(hlpx) > 1:
                slope, intercept, r_value, p_value, std_err = stats.linregress(hlpx, hlpy)
            else:
                r_value = np.nan
                p_value = 2.

            if p_value < pthres:
                CO.append(r_value)
            else:
                CO.append(np.nan)

        #~ #-- find best lag
        #~ best_lag=abs(np.asarray(CO)).argmax(axis=0).astype('float')
        #~ print 'BEST LAG: ', best_lag

        CO = np.asarray(CO)

        return CO

#-----------------------------------------------------------------------

    def get_correlation_value(self):
        """
        get correlation between two vectors
        """
        c = np.ma.corrcoef(self.xvec, self.yvec)[0][1]
        return c  # correlation coefficient

#-----------------------------------------------------------------------

    def _mat2vec(self, mask=None):
        """
        concatenate all information into
        a vector and apply a given
        mask if desired

        Parameters
        ----------
        mask : ndarray
            mask to be applied
        """

        #--- generated copies and mask data if desired
        X = self.x.copy()
        if mask is not None:
            X._apply_mask(mask, keep_mask=False)
        if self.y is not None:
            Y = self.y.copy()
            if mask is not None:
                Y._apply_mask(mask, keep_mask=False)
        else:
            Y = None

        #--- vectorize the data (concatenate in space and time)
        xvec = X.data.copy()
        xvec.shape = (-1)
        if self.y is not None:
            yvec = Y.data.copy()
            yvec.shape = (-1)
        self.xvec = xvec
        self.yvec = yvec

#-----------------------------------------------------------------------

    def calc_reichler_index(self, weights=None):
        """
        calculate index after Reichler & Kim (2008)
        for a single model

        it is assumed that the field has a time component

        variable x is assumed to be the reference dataset

        The weights need to be available for each timestep to account
        for temporally varying gaps in the data. weights can be calculated
        e.g. with the method _get_weighting_matrix() of the C{Data} class.

        returns E**2 as a list whereas each element corresponds to the weighted
        difference at a timestep. Thus to get the overall score, one still needs
        to take the sum of all values in the calling program!
        """

        if not hasattr(self, 'y'):
            raise ValueError('Can not calculate Reichler & Kim index without a second variable!')

        if not hasattr(self.x, 'std'):
            raise ValueError('Can not calculate Reichler & Kim index without STD information!')

        if not self.x._is_monthly():
            print self.x.label
            pickle.dump(self.x.date. open('debug_date.pkl', 'w'))
            raise ValueError('Variable X has no monthly stepping!')
        if not self.y._is_monthly():
            raise ValueError('Variable Y has no monthly stepping!')

        # spatial weights
        if weights is None:
            if self.x.cell_area is None:
                print 'WARNING: Reichler: can not calculated weighted index, as no cell_area given!'
                weights = np.ones(self.x.data.shape)
            else:
                weights = self.x._get_weighting_matrix()
        else:
            weights = weights.copy()

        x = self.x.data.copy()
        y = self.y.data.copy()
        std_x = self.x.std.copy()

        if np.shape(x) != np.shape(y):
            print np.shape(x), np.shape(y)
            raise ValueError('Invalid shapes of arrays!')

        if x.ndim == 1:  # only timeseries
            e2 = sum(weights * (x - y) ** 2. / std_x)
        else:
            n = len(x)
            x.shape = (n, -1)  # [time,index]
            y.shape = (n, -1)
            std_x.shape = (n, -1)
            weights.shape = (n, -1)
            if np.shape(x) != np.shape(weights):
                print x.shape, weights.shape
                raise ValueError('Invalid shape for weights!')

            # calculate weighted average for all timesteps
            e2 = np.ones(n) * np.nan
            for i in xrange(n):
                d = weights[i, :] * ((x[i, :] - y[i, :]) ** 2.) / std_x[i, :]
                e2[i] = np.sum(d)  # sum at end to avoid nan's   #it is important to use np.sum() !!
                # TODO apply proper temporal weighting here as well!

        if np.any(np.isnan(e2)):
            print 'd: ', d
            for i in xrange(n):
                print 'std_x', i, std_x[i, :]
            print('Reichler: e2 contains NAN, this happens most likely if STDV == 0')
            return None
        else:
            return e2

#-----------------------------------------------------------------------

    def get_correlationxxxxx(self, lag=0, nlags=None):
        """
        calculate correlation between two data sets
        """

        print 'Calculating correlation with lag=', lag, nlags

        def NormCrossCorrSlow(x1, x2,
                              nlags=400):
            res = []
            lags = []
            for i in range(-(nlags / 2), nlags / 2, 1):
                lags.append(i)
                if i < 0:
                    xx1 = x1[:i]
                    xx2 = x2[-i:]
                elif i == 0:
                    xx1 = x1
                    xx2 = x2
                else:
                    xx1 = x1[i:]
                    xx2 = x2[:-i]

                xx1 = xx1 - xx1.mean()
                xx2 = xx2 - xx2.mean()

                res.append((xx1 * xx2).sum() / ((xx1 ** 2).sum() * (xx2 ** 2).sum()) ** 0.5)

            return np.array(res), np.array(lags)

        if not hasattr(self, 'y'):
            raise ValueError('No y variable existing!')

        x = self.x.data.copy()
        y = self.y.data.copy()

        s1 = np.shape(x)
        s2 = np.shape(y)
        if s1 != s2:
            print s1, s2
            raise ValueError('Invalid shapes!')

        n = np.shape(x)[0]
        x.shape = (n, -1)
        y.shape = (n, -1)

        if len(s1) == 2:
            ndata = s1[1] * s1[2]
        elif len(s1) == 1:
            ndata = 1  # vector
        else:
            raise ValueError('Invalid shape!')

        R = np.zeros(ndata) * np.nan

        for i in range(ndata):
            xx = x[:, i]
            yy = y[:, i]
            msk = (~np.isnan(xx) & ~np.isnan(yy))
            if sum(msk) > 3:

                if lag == 0:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(xx[msk], yy[msk])
                else:

                    #print nlags
                    if nlags is None:
                        nlags = len(xx[msk])
                        if np.mod(nlags, 2) == 0:
                            nlags += 1
                    #print nlags

                    r1, lags = NormCrossCorrSlow(xx[msk], yy[msk], nlags=nlags)
                    idx = nlags / 2 + lag  # todo something does not work with the indices !!!
                    print idx, nlags, len(r1)
                    r_value = r1[idx]

                R[i] = r_value

        print x.ndim

        print self.x.data.ndim
        if len(s1) == 2:
            R = np.reshape(R, np.shape(self.x.data[0, :]))
        else:
            R = R

        return R

#-----------------------------------------------------------------------

    def slice_corr(self, timmean=True, spearman=False, partial=False, z=None):
        """
        perform correlation analysis for
        different starting times and length
        of the correlation period

        if timmean=True then the correlation is caluclated
        on basis of the mean spatial fields, thus
        the timeseries of each pixels is averaged over time
        before the correlation calculation

        partial: do partial correlation
        z: condition in case of partial correlation
        """

        if partial:
            if spearman:
                raise ValueError('Spearman and partial correlation not supported')
            if z is None:
                raise ValueError('no z-value given for partial correlation!')
            if self.x.data.shape != z.data.shape:
                print self.x.data.shape
                print z.data.shape
                raise ValueError('Invalid geometries for partial correlation!')

        x = self.x.data.copy()

        if not hasattr(self, 'y'):
            # if no y value is given, then time is used as independent variable
            print('No y-value specified. Use time as indpendent variable!')

            y = x.copy()
            x = np.ma.array(self.x.time.copy(), mask=self.x.time < 0.)
        else:
            y = self.y.data.copy()

        if np.shape(x) != np.shape(y):
            if np.prod(np.shape(x)) != np.prod(np.shape(y)):  # check if flattened arrays would work
                print np.shape(x), np.shape(y)
                raise ValueError('slice_corr: shapes not matching!')

        #--- reshape data
        n = len(x)  # timesteps
        x.shape = (n, -1)  # size [time,ngridcells]
        y.shape = (n, -1)

        if partial:
            z = z.data.copy()
            z.shape = (n, -1)

        R = np.ones((n, n)) * np.nan
        P = np.ones((n, n)) * np.nan
        L = np.ones((n, n)) * np.nan
        S = np.ones((n, n)) * np.nan

        # perform correlation analysis
        print('   Doing slice correlation analysis ...')
        i1 = 0
        while i1 < n - 1:  # loop over starting year
            i2 = i1 + 2
            # loop over different lengths
            while i2 < len(x) - 1:
                length = i2 - i1

                if timmean:
                    """ temporal mean -> all grid cells only (temporal mean) """
                    xdata = x[i1:i2, :].mean(axis=0)
                    ydata = y[i1:i2, :].mean(axis=0)

                    xmsk = xdata.mask
                    ymsk = ydata.mask
                    msk = xmsk | ymsk

                    if partial:
                        raise ValueError('No timmean supported yet for partial correlation!')

                else:
                    """ all grid cells at all times """
                    xdata = x.data[i1:i2, :]
                    ydata = y.data[i1:i2, :]
                    xmsk = x.mask[i1:i2, :]
                    ymsk = y.mask[i1:i2, :]
                    msk = xmsk | ymsk

                    if partial:
                        zdata = z.data[i1:i2, :]
                        zmsk = z.mask[i1:i2, :]
                        msk = msk | zmsk
                        zdata = zdata[~msk].flatten()

                xdata = xdata[~msk].flatten()
                ydata = ydata[~msk].flatten()

                # use spearman correlation
                if spearman:
                    tmpx = xdata.argsort()
                    tmpy = ydata.argsort()
                    xdata = tmpx
                    ydata = tmpy

                if partial:
                    #calculate residuals for individual correlations
                    slope, intercept, r, p, stderr = stats.linregress(zdata, xdata)
                    xdata = (xdata - intercept) / slope

                    slope, intercept, r, p, stderr = stats.linregress(zdata, ydata)
                    ydata = (ydata - intercept) / slope

                slope, intercept, r, p, stderr = stats.linregress(xdata, ydata)
                R[length, i1] = r
                P[length, i1] = p
                L[length, i1] = length
                S[length, i1] = slope

                i2 += 1
            i1 += 1

        self.slice_r = R
        self.slice_p = P
        self.slice_length = L
        self.slice_slope = S

#-----------------------------------------------------------------------

    def slice_corr_gap(self, timmean=True, spearman=False, pthres=None):
        """
        perform correlation analysis for
        different starting times and gap sizes

        if timmean=True then the correlation is calculated
        on basis of the mean spatial fields, thus
        the timeseries of each pixels is averaged over time
        before the correlation calculation
        """

        x = self.x.data.copy()

        if not hasattr(self, 'y'):
            #if no y value is given, then time is used as independent variable
            print 'No y-value specified. Use time as indpendent variable!'
            y = x.copy()
            x = np.ma.array(self.x.time.copy(), mask=self.x.time < 0.)
        else:
            y = self.y.data.copy()

        if np.shape(x) != np.shape(y):
            raise ValueError('slice_corr: shapes not matching!')

        #--- reshape data
        n = len(x)  # timesteps

        gaps = np.arange(n)

        x.shape = (n, -1)  # size [time,ngridcells]
        y.shape = (n, -1)
        maxgap = n

        #~ print 'maxgap: ', maxgap
        R = np.ones((maxgap, n)) * np.nan
        P = np.ones((maxgap, n)) * np.nan
        L = np.ones((maxgap, n)) * np.nan
        S = np.ones((maxgap, n)) * np.nan

        #--- perform correlation analysis
        print '   Doing slice correlation analysis ...'
        i1 = 0
        while i1 < n - 1:  # loop over starting year
            i2 = n  # always entire time period
            #- loop over different lengths
            for gap in gaps:

                if gap >= i2 - i1:
                    continue
                if timmean:
                    # temporal mean -> all grid cells only (temporal mean)
                    raise ValueError('TIMMEAN not supported yet for gap analysis')
                    xdata = x[i1:i2, :].mean(axis=0)
                    ydata = y[i1:i2, :].mean(axis=0)
                    xmsk = xdata.mask
                    ymsk = ydata.mask
                    msk = xmsk | ymsk
                else:
                    # all grid cells at all times
                    xdata = x.data.copy()
                    ydata = y.data.copy()
                    xmsk = x.mask.copy()  # [i1:i2,:]
                    ymsk = y.mask.copy()  # [i1:i2,:]

                    # mask data which has gaps and use whole period elsewhere
                    xmsk[i1:i1 + gap, :] = True
                    ymsk[i1:i1 + gap, :] = True

                    msk = xmsk | ymsk

                xdata = xdata[~msk].flatten()
                ydata = ydata[~msk].flatten()

                #use spearman correlation
                if spearman:
                    tmpx = xdata.argsort()
                    tmpy = ydata.argsort()
                    xdata = tmpx
                    ydata = tmpy

                slope, intercept, r, p, stderr = stats.linregress(xdata, ydata)
                R[gap, i1] = r
                P[gap, i1] = p
                L[gap, i1] = gap - 1
                S[gap, i1] = slope

            i1 += 1

        if pthres is not None:  # mask all insignificant values
            R = np.ma.array(R, mask=P > pthres)
            S = np.ma.array(S, mask=P > pthres)

        self.slice_r_gap = R
        self.slice_p_gap = P
        self.slice_length_gap = L
        self.slice_slope_gap = S

#-----------------------------------------------------------------------
    def _set_year_ticks(self, years, ax, axis='x', size=10, rotation=0.):
        """
        set ticks of timeline with
        yearly ticks

        years : list
            list of years
        ax : axis
            axis to handle
        axis : str
            specify which axis to handle 'x' or 'y'
        size : int
            fontisze for ticks
        rotation : float
            rotation angle for ticks
        """
        ticks = ax.get_xticks()

        #- calculate ticks from year
        oticks = []
        for t in ticks:
            if t < 0:
                oticks.append('')
            elif t > len(years) - 1:
                oticks.append('')
            else:
                oticks.append(years[int(t)])
        #- set ticks of axis
        if axis == 'x':
            ax.set_xticklabels(oticks, size=size, rotation=rotation)
        elif axis == 'y':
            ax.set_yticklabels(oticks, size=size, rotation=rotation)
        else:
            raise ValueError('Invalid axis (set_year_ticks)')

#-----------------------------------------------------------------------

    def plot_slice_correlation(self, pthres=1.01):
        """
        plot slice correlation results

        Parameters
        ----------
        pthres : float
            significance threshold. All results with p-values
            below this threshold will be plotted
        """

        cmap1 = plt.cm.get_cmap('RdBu_r', 10)
        cmap2 = plt.cm.get_cmap('jet', 10)

        if not hasattr(self, 'slice_r'):
            raise ValueError('Perform slice_corr() before plotting!')

        #- get years of data for ticks
        years = self.x._get_years()

        #- generate plots
        fig = plt.figure(figsize=(12, 6))
        fig.subplots_adjust(hspace=0.5)
        self.slice_fig = fig
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax3 = fig.add_subplot(223)
        ax4 = fig.add_subplot(224)

        r_data = self.slice_r.copy()
        p_data = self.slice_p.copy()
        length_data = self.slice_length.copy()
        slope_data = self.slice_slope.copy()

        msk = p_data > pthres
        r_data[msk] = np.nan
        p_data[msk] = np.nan
        length_data[msk] = np.nan
        slope_data[msk] = np.nan

        #- correlation
        imr = ax1.imshow(r_data, interpolation='nearest', cmap=cmap1)
        ax1.set_title('correlation')
        plt.colorbar(imr, ax=ax1, shrink=0.8)
        ax1.set_xlabel('start year')
        ax1.set_ylabel('correlation period [years]')

        #- significance
        imp = ax2.imshow(p_data, interpolation='nearest', cmap=cmap2)
        ax2.set_title('p-value')
        plt.colorbar(imp, ax=ax2, shrink=0.8)
        ax2.set_xlabel('start year')
        ax2.set_ylabel('correlation period [years]')

        #- length of period
        iml = ax3.imshow(length_data, interpolation='nearest', cmap='RdBu_r')
        ax3.set_title('length')
        plt.colorbar(iml, ax=ax3, shrink=0.8)
        ax3.set_xlabel('start year')
        ax3.set_ylabel('correlation period [years]')

        #- slope
        ims = ax4.imshow(slope_data, interpolation='nearest', cmap=cmap2)
        ax4.set_title('slope')
        plt.colorbar(ims, ax=ax4, shrink=0.8)
        ax4.set_xlabel('start year')
        ax4.set_ylabel('correlation period [years]')

        #/// set tick labels ///
        self._set_year_ticks(years, ax1, axis='x')
        self._set_year_ticks(years, ax2, axis='x')
        self._set_year_ticks(years, ax3, axis='x')
        self._set_year_ticks(years, ax4, axis='x')

        #- contour plots
        CP1 = ax1.contour(p_data, [0.01, 0.05, 0.1], linewidths=2)
        CP2 = ax2.contour(p_data, [0.01, 0.05, 0.1], linewidths=2)
        CP3 = ax3.contour(p_data, [0.01, 0.05, 0.1], linewidths=2)
        CP4 = ax4.contour(p_data, [0.01, 0.05, 0.1], linewidths=2)

        ax1.clabel(CP1, inline=1, fontsize=10)
        ax2.clabel(CP2, inline=1, fontsize=10)
        ax3.clabel(CP3, inline=1, fontsize=10)
        ax4.clabel(CP4, inline=1, fontsize=10)
#===========================================================================================
#
#
#===========================================================================================


class Koeppen(object):
    """
    KOEPPEN CLASS
    class to generate koeppen plot
    """

    def __init__(self, temp=None, precip=None, lsm=None):
        """
        Koeppen class
        This class implements the functionality to generate koeppen plots.

        Parameters
        ----------
        temp : Data
            data objekt of temperature
        precip : Data
            data objekt of precipitation
        lsm : Data
            data objekt of land-sea-mask (0.0 to 1.0)

        EXAMPLES
        ========

        """

        # check consistency
        if temp is None:
            raise ValueError('No temperature given')
        if precip is None:
            raise ValueError('No precipitation given')
        if lsm is None:
            raise ValueError('No land-sea-mask given')

        # set values of class
        self.temp = temp
        self.precip = precip
        self.lsm = lsm

        if not self._check_resolution():
            raise ValueError('ERROR:The three array differe in the resolution')
        if not self._check_units():
            raise ValueError('ERROR:The units of one value is wrong')

        # Create new koeppen Color map
        self.koeppen_cmap()
        self.cmap = cm.get_cmap('koeppen')
        # convert from [kg m-2 s-1] to [kg m-2 day-1] (= [mm day-1])
         # ??? Unklar warum nicht 'precip.mulc(60. * 60. * 24. * 365.)'
        self.precip = precip.mulc(60. * 60. * 24. * 365. / 12., copy=True)
        self.temp = temp.subc(273.15, copy=True)  # ??? Unklar warum nicht 'temp.subc(273.15)'

        Psum = self.precip.timsum(return_object=True)            # Berechnet die Summe der Jahresniederschlag

        nt, ny, nx = self.temp.shape
        nlat = ny
        nlon = nx

        Pmin = self.precip.data.min(axis=0)
        Pmax = self.precip.data.max(axis=0)

        precipHS = self.precip.copy()
        precipHS.data[(0, 1, 2, 3, 4, 5), 0:(nlat / 2 - 1), :] \
            = self.precip.data[(3, 4, 5, 6, 7, 8), 0:(nlat / 2 - 1), :]
        precipHS.data[(6, 7, 8, 9, 10, 11), 0:(nlat / 2 - 1), :] \
            = self.precip.data[(3, 4, 5, 6, 7, 8), 0:(nlat / 2 - 1), :]
        precipHS.data[(0, 1, 2, 3, 4, 5), (nlat / 2):(nlat - 1), :] \
            = self.precip.data[(0, 1, 2, 9, 10, 11), (nlat / 2):(nlat - 1), :]
        precipHS.data[(6, 7, 8, 9, 10, 11), (nlat / 2):(nlat - 1), :] \
            = self.precip.data[(0, 1, 2, 9, 10, 11), (nlat / 2):(nlat - 1), :]

        precipHW = self.precip.copy()
        precipHW.data[(0, 1, 2, 3, 4, 5), 0:(nlat / 2 - 1), :] = self.precip.data[(0, 1, 2, 9, 10, 11), 0:(nlat / 2 - 1), :]
        precipHW.data[(6, 7, 8, 9, 10, 11), 0:(nlat / 2 - 1), :] = self.precip.data[(0, 1, 2, 9, 10, 11), 0:(nlat / 2 - 1), :]
        precipHW.data[(0, 1, 2, 3, 4, 5), (nlat / 2):(nlat - 1), :] = self.precip.data[(3, 4, 5, 6, 7, 8), (nlat / 2):(nlat - 1), :]
        precipHW.data[(6, 7, 8, 9, 10, 11), (nlat / 2):(nlat - 1), :] = self.precip.data[(3, 4, 5, 6, 7, 8), (nlat / 2):(nlat - 1), :]

        PminHS = precipHS.data.min(axis=0)   # Bestimmt den minimalen Monastniederschlag aus PmaxHS
        PmaxHS = precipHS.data.max(axis=0)   # Bestimmt den maximalen Monastniederschlag aus PmaxHS
        PminHW = precipHW.data.min(axis=0)   # Bestimmt den minimalen Monastniederschlag aus PminHW
        PmaxHW = precipHW.data.max(axis=0)   # Bestimmt den maximalen Monastniederschlag aus PminHW

        Tavg = self.temp.data.mean(axis=0)   # Bestimmt die mittlere Jahrestemperatur
        Tmin = self.temp.data.min(axis=0)     # Bestimmt die minimale Monatstemperatur
        Tmax = self.temp.data.max(axis=0)     # Bestimmt die maximale Jahrestemperatur

        self.Clim = self.precip.timmean(return_object=True)
        self.Clim.units = "climate type"

        for lat in range(0, nlat):
            for lon in range(0, nlon):
                psum = Psum.data.data[lat][lon]
                pmin = Pmin[lat][lon]
                pminhs = PminHS[lat][lon]
                pminhw = PminHW[lat][lon]
                pmaxhs = PmaxHS[lat][lon]
                pmaxhw = PmaxHW[lat][lon]
                tavg = Tavg[lat][lon]
                tmin = Tmin[lat][lon]
                tmax = Tmax[lat][lon]
                self.Clim.data.data[lat][lon] = self.set_clim(psum, pmin, pminhs, pminhw, pmaxhs, pmaxhw, tavg, tmin, tmax)

        self.Clim.data.mask[less(self.lsm.data, 0.5)] = True

#-----------------------------------------------------------------------------------------------------------------------
    def koeppen_cmap(self):
        """
        Create a colormap with 14 discrete colors and register it
        """
        # define individual colors as hex values
        cpool = ['#7f0000', '#ff0000', '#ff4c4c', '#ff9999', '#ffa500',
                 '#ffff4c', '#009900', '#00ff00', '#99ff99', '#990099',
                 '#e500e5', '#ff66ff', '#0000ff', '#9999ff', '#000000']
        cmap3 = col.ListedColormap(cpool[0:14], 'koeppen')
#       plt.cm.register_cmap(cmap=cmap3,name='koeppen',lut=15)
        plt.cm.register_cmap(cmap=cmap3, name='koeppen')
        return cmap3

#-----------------------------------------------------------------------------------------------------------------------

    def set_clim(self, psum, pmin, pminhs, pminhw, pmaxhs, pmaxhw, tavg, tmin, tmax):
        clim = -999

        if tmin > 18:
            if pmin > 60:                 # A(B)
                clim = 1                    # Af
            else:
                if pmin > (0.04 * (2500 - psum)):      # A(B)-msw
                    clim = 2                  # Am
                else:
                    if (pminhs < 40) and (pminhs < (pmaxhw / 3)):   # A(B)-sw
                        if (psum / 10) < (2 * tavg):          # A(B)-s
                            if (psum / 10) < (tavg):            # B
                                clim = 6                    # BW
                            else:
                                clim = 5                    # BS
                        else:
                            clim = 3                      # As
                    else:
                        if (psum / 10) < (2 * (tavg + 14)):       # A(B)-w
                            if (psum / 10) < (tavg + 14):       # B
                                clim = 6                    # BW
                            else:
                                clim = 5                    # BS
                        else:
                            clim = 4                      # Aw
        else:
            if (pminhs < 40) and (pminhs < (pmaxhw / 3)):   # CDE(B)
                if (psum / 10) < (2 * tavg):          # CDE(B)-s
                    if (psum / 10) < (tavg):            # B
                        clim = 6                    # BW
                    else:
                        clim = 5                    # BS
                else:
                    if tmax < 10:                # CDE-s
                        if tmax < 0:                # E
                            clim = 14                 # EF
                        else:
                            clim = 13                 # ET
                    else:
                        if (tmin > -3):             # CD-s
                            clim = 8                  # Cs
                        else:
                            clim = 11                 # Ds
            else:
                if pminhw < (pmaxhs / 10):            # CDE(B)-fw
                    if (psum / 10) < (2 * (tavg + 14)):     # CDE(B)-w
                        if (psum / 10) < (tavg + 14):         # B
                            clim = 6                  # BW
                        else:
                            clim = 5                  # BS
                    else:
                        if tmax < 10:               # CDE-w

                            if (tmax < 0):                # E
                                clim = 14               # EF
                            else:
                                clim = 13              # ET
                        else:
                            if (tmin > -3):               # CD-w
                                clim = 9                # Cw
                            else:
                                clim = 12               # Dw
                else:
                    if (psum / 10) < (2 * (tavg + 7)):      # CDE(B)-f
                        if (psum / 10) < (tavg + 7):          # B
                            clim = 6                  # BW
                        else:
                            clim = 5                  # BS
                    else:
                        if (tmax < 10):             # CDE-f
                            if (tmax < 0):                # E
                                clim = 14               # EF
                            else:
                                clim = 13              # ET
                        else:
                            if (tmin > -3):               # CD-f
                                clim = 7                # Cf
                            else:
                                clim = 10              # Df
        return clim

#-----------------------------------------------------------------------------------------------------------------------

    def _check_resolution(self):
        """
        This routine just checks if all three array have a equal number of ny and nx values
        """
        nt_t, ny_t, nx_t = self.temp.shape
        nt_p, ny_p, nx_p = self.precip.shape
        ny_l, nx_l = self.lsm.shape

        if (ny_t != ny_p) or (ny_t != ny_l):
            sys.exit('ERROR: The resolution ot the three arrays differ in \
       Y-dimension: \n' + str(ny_t) + "(temp)  " + str(ny_p)
                     + "(precip) " + str(ny_l) + "(lsm) ")
            return False

        if (nx_t != nx_p) or (nx_t != nx_l):
            sys.exit('ERROR: The resolution ot the three arrays differ in \
       X-dimension: \n' + str(nx_t) + "(temp)  " + str(nx_p)
                     + "(precip) " + str(nx_l) + "(lsm) ")
            return False

        return True

#-----------------------------------------------------------------------------------------------------------------------

    def _check_units(self):
        """
        This routine just checks if all three array have a equal number of ny and nx values
        """
        if self.precip.unit != "kg/m^2s":
            raise ValueError('ERROR: The unit of the precip is not [kg/m^2s] its set to [' + self.precip.unit + "]")

        if self.temp.unit != "K":
            raise ValueError('ERROR: The unit of the temperature is not [K] its set to [' + self.temp.unit + "]")

        if self.lsm.unit != "fractional":
            raise ValueError('ERROR: The unit of the temperature is not [fractional] its set to [' + self.temp.unit + "]")

        return True

#-----------------------------------------------------------------------------------------------------------------------
    def copy(self):
        """
        Returns the Clim Data as an Data variable
        """
        return self.Clim

#-----------------------------------------------------------------------------------------------------------------------

    def climfrac(self):
        """
        This routine calculats the fraction of each type in per centum.
        ToDo:
        Unclear id the print is OK or if the values should given back as an array.
        """
        climfrac = [0] * 14

        ny, nx = self.Clim.data.data.shape
        for ny in range(0, ny - 1):
            Aweight = cos(self.Clim.lat[ny][0] / 180 * 3.14159265359)
            for nx in range(0, nx - 1):
                clim = int(self.Clim.data.data[ny][nx])
                climfrac[clim - 1] = climfrac[clim - 1] + Aweight

        s = sum(climfrac)
        climfrac[:] = [x / s for x in climfrac]

        print "Af: " + str(climfrac[0])
        print "Am: " + str(climfrac[1])
        print "As: " + str(climfrac[2])
        print "Aw: " + str(climfrac[3])
        print "BS: " + str(climfrac[4])
        print "BW: " + str(climfrac[5])
        print "Cf: " + str(climfrac[6])
        print "Cs: " + str(climfrac[7])
        print "Cw: " + str(climfrac[8])
        print "Df: " + str(climfrac[9])
        print "Ds: " + str(climfrac[10])
        print "Dw: " + str(climfrac[11])
        print "ET: " + str(climfrac[12])
        print "EF: " + str(climfrac[13])

#-----------------------------------------------------------------------------------------------------------------------

    def legend(self):
        """
        This routine prints a legend of the geiger-koeppen types.
        The description is taken from:
        MARKUS KOTTEK, JUERGEN GRIESER, CHRISTOPH BECK , BRUNO RUDOLF and FRANZ RUBEL
        World Map of the Koeppen-Geiger climate classification updated
        Meteorologische Zeitschrift, Vol. 15, No. 3, 259-263 (June 2006)

        """

        print "|================= Class legend =================|"
        print "| Af: Equatorial rainforest, fully humid         |"
        print "| Am: Equatorial climates                        |"
        print "| As: Equatorial monsoon                         |"
        print "| Aw: Equatorial savannah with dry winter        |"
        print "|------------------------------------------------|"
        print "| BS: Steppe climate                             |"
        print "| BW: Desert climate                             |"
        print "|------------------------------------------------|"
        print "| Cf: Warm temperate climate, fully humid        |"
        print "| Cs: Warm temperate climate with dry summer     |"
        print "| Cw: Warm temperate climate with dry winter     |"
        print "|------------------------------------------------|"
        print "| Df: Snow climate, fully humid                  |"
        print "| Ds: Snow climate with dry summer               |"
        print "| Dw: Snow climate with dry winter               |"
        print "|------------------------------------------------|"
        print "| ET: Tundra climate                             |"
        print "| EF: Frost climate                              |"
        print "|================================================|"

#-----------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------
    def plot(self, **kwargs):
        """
        This routine plots the data of his own geiger-koeppen data by
        using the plot-routine map_plot.
        It use the own created color-map and sets the color-bar to a
        horizontal orientation.
        It set the range of values between 0.5 and 14.5. Which are the
        possible values of geiger-koeppen.
        ToDo:
        At the moment the label of the geiger-koeppen types are missing
        at the color-bar
        """
        map_plot(self.Clim, cmap_data=self.cmap, colorbar_orientation='horizontal', vmin=0.5, vmax=14.5,
                 cticks=[1., 2., 3., 4., 5., 6., 7., 8., 9., 10., 11., 12., 13., 14.],
                 cticklabels=["Af", "Am", "As", "Aw", "BS", "BW", "Cf",
                              "Cs", "Cw", "Df", "Ds", "Dw", "ET", "EF"],
                 nclasses=15, **kwargs)
