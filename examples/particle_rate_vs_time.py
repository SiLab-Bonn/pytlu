import numpy as np
import matplotlib.pyplot as plt
import tables as tb
from scipy.misc import factorial
from pybar.analysis import analysis_utils
import os


def diff(x, array, n):
    return np.sum(array[0:x*n])


def poisson(k, *p):
    A, lamb = p
    return A * (lamb**k / factorial(k)) * np.exp(-lamb)


def plot_rate(x, y, output_pdf, x_label, y_label, title, markerstyle, plot_mean_max_rate=None, plot_mean_rate=False, x_err=None, y_err=None, x_lim=None, y_lim=None):
        plt.close()
        plt.grid(True)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        if x_err is not None:
            x_err = [x_err, x_err]
        if y_err is not None:
            y_err = [y_err, y_err]
        if x_err is not None or y_err is not None:
            plt.errorbar(x, y, y_err, x_err, markerstyle, lw=1, label="Particle Rate")
        else:
            plt.plot(x, y, markerstyle, markersize=4, lw=1, label="Particle Rate")
        if plot_mean_rate is True:
            mean_rate = np.mean(y)
            plt.axhline(y=mean_rate, xmin=0, xmax=5, linewidth=1.5, color='darkorange', linestyle='--', label=('Mean Rate: %.1f kHz' % (mean_rate)))
        if plot_mean_max_rate is not None:
            cut = 0.9
            mean_max_rate = np.mean(y[np.where(y > cut * plot_mean_max_rate)])
            # plt.plot(x[np.where(y > cut * plot_mean_max_rate)], y[np.where(y > cut * plot_mean_max_rate)], color='r')
            plt.axhline(y=mean_max_rate, xmin=0, xmax=5, linewidth=1.5, color='firebrick', linestyle='--', label=('Mean Maximum Rate: %.1f kHz' % (mean_max_rate)))
        if x_lim is not None:
            plt.xlim(x_lim[0], x_lim[1])
        if y_lim is not None:
            plt.ylim(top=y_lim)
        #if y_lim is None:
        #    plt.ylim(top=1.6 * mean_max_rate)
        plt.legend(loc='best', fancybox=True, frameon=True)
        plt.tight_layout()
        plt.savefig(output_pdf)
        plt.close()

        return mean_rate


def plot_frequency_spectrum(hist, n_bins, x_label, y_label, output_pdf, x_lim=None, plot_mean=False, plot_mpv=False, plot_cut_freq=None):
    hist, edges, _ = plt.hist(hist, bins=n_bins, label='Time Stamp Frequency Distribution')
    bin_center = (edges[1:] + edges[:-1]) / 2.0

    if plot_mpv is True:
        mpv = edges[np.where(hist == np.max(hist))]
        plt.axvline(x=mpv,
                    linestyle='--',
                    color='firebrick',
                    label='Most Probable Frequency: %.1f kHz' % mpv)
    else:
        mpv = None

    mean = analysis_utils.get_mean_from_histogram(hist, bin_positions=bin_center)
    if plot_mean is True:
        plt.axvline(x=mean,
                    color='darkorange',
                    label='Mean Frequency: %.1f kHz' % mean)

    if plot_cut_freq is not None:
        plt.axvline(x=plot_cut_freq,
                    linestyle='--',
                    color='firebrick',
                    label=('Max trigger rate: %.1f kHz' % plot_cut_freq))

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    if x_lim is not None:
        plt.xlim(x_lim[0], x_lim[1])
    plt.grid()
    plt.legend()
    plt.savefig(output_pdf)
    plt.close()

    return mean, mpv


# input_folder = '/media/silab/7D945E0202CD4D3B/ITK_PIXEL_TESTBEAM_MAY/Runs/run_%i/'
# # search tlu file
# for root, dirs, files in os.walk((os.path.normpath(input_folder)), topdown=False):
#     for name in files:
#         if name.startswith('tlu_2018') and name.endswith('.h5'):
#             print "Found"
#             SourceFolder = os.path.join(root, name)
#             print SourceFolder, name
#             input_file = SourceFolder

input_file = '/home/silab/Downloads/pytlu_98_200304-000124.h5'
# input_folder = '/media/silab/7D945E0202CD4D3B/ELSA_TB_APRIL_2019/data_tlu/'
name = input_file

output_file = input_file[:-3] + '_event_rate.h5'
with tb.open_file(input_file, mode='r') as in_file_h5:
    timestamp = (in_file_h5.root.raw_data[:]['time_stamp']).astype(np.float64)

# calculate relative difference of timestamp
rel_diff = np.diff(timestamp)

# new method to determine event rate from single timestamps
# calculate absoulte times from relative time difference with cumulative sum
absolute_times = np.cumsum(rel_diff) / 40. / 10**6  # convert to seconds
time_step = 100e-3  # define binning of timestamps, in seconds
bin_ed = np.arange(absolute_times[0], absolute_times[-1], time_step)
time_hist, time_edges = np.histogram(absolute_times, bins=bin_ed)
rate_new = time_hist / time_step / 1000.
time_center = (time_edges[1:] + time_edges[:-1]) / 2.0

# plot event rate
mean_rate = plot_rate(time_center,
                      rate_new,
                      output_pdf=(name[:-3] + 'particle_rate_vs_time.pdf'),
                      x_label='t / s',
                      y_label='Particle Rate / kHz',
                      title=('Particle Rate, Time Interval of combined Time Stamps (40 MHz): %.2f s' % time_step),
                      markerstyle='-o',
                      # x_lim=(30., 40.),
                      y_lim=None,
                      plot_mean_rate=True)
print mean_rate, 'mean_rate'
mean_combined_new, mpv_combined_new = plot_frequency_spectrum(rate_new,
                                                              n_bins=400,
                                                              x_label='Frequency / kHz',
                                                              y_label='#',
                                                              plot_mpv=False,
                                                              output_pdf=name[:-3] + 'timestamp_distribution_binned.pdf')

rel_diff = rel_diff / 40. / 10**6 * 1000.  # convert to ms

mean, mpv = plot_frequency_spectrum((1. / rel_diff),
                                    n_bins=np.arange(0, 75, 0.5),
                                    x_label='Frequency / kHz',
                                    y_label='#',
                                    plot_mpv=False,
                                    x_lim=(0, 75),
                                    output_pdf=name[:-3] + 'timestamp_distribution_unbinned.pdf')
