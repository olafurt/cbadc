"""
=============
Downsampling
=============

In this tutorial we demonstrate how to configure the digital estimator
for downsampling.
"""
import scipy.signal
import numpy as np
import cbadc as cbc
import matplotlib.pyplot as plt

###############################################################################
# Setting up the Analog System and Digital Control
# ------------------------------------------------
#
# In this example, we assume that we have access to a control signal
# s[k] generated by the interactions of an analog system and digital control.
# Furthermore, we a chain-of-integrators converter with corresponding
# analog system and digital control.
#
# .. image:: /images/chainOfIntegratorsGeneral.svg
#    :width: 500
#    :align: center
#    :alt: The chain of integrators ADC.

# Setup analog system and digital control

# We fix the number of analog states.
N = 6
M = N
# Set the amplification factor.
beta = 6250.
rho = 1e-2
# In this example, each nodes amplification and local feedback will be set
# identically.
betaVec = beta * np.ones(N)
rhoVec = - betaVec * rho
kappaVec = - beta * np.eye(N)

# Instantiate a chain-of-integrators analog system.
analog_system = cbc.analog_system.ChainOfIntegrators(betaVec, rhoVec, kappaVec)


T = 1/(2 * beta)
digital_control = cbc.digital_control.DigitalControl(T, M)


# Summarize the analog system, digital control, and digital estimator.
print(analog_system, "\n")
print(digital_control)


###############################################################################
# Loading Control Signal from File
# --------------------------------
#
# Next, we will load an actual control signal to demonstrate the digital
# estimator's capabilities. To this end, we will use the
# `sinusodial_simulation.adcs` file that was produced in
# :doc:`./plot_b_simulate_a_control_bounded_adc`.
#
# The control signal file is encoded as raw binary data so to unpack it
# correctly we will use the :func:`cbadc.utilities.read_byte_stream_from_file`
# and :func:`cbadc.utilities.byte_stream_2_control_signal` functions.

byte_stream = cbc.utilities.read_byte_stream_from_file(
    '../a_getting_started/sinusodial_simulation.adcs', M)
control_signal_sequences1 = cbc.utilities.byte_stream_2_control_signal(
    byte_stream, M)

byte_stream = cbc.utilities.read_byte_stream_from_file(
    '../a_getting_started/sinusodial_simulation.adcs', M)
control_signal_sequences2 = cbc.utilities.byte_stream_2_control_signal(
    byte_stream, M)

byte_stream = cbc.utilities.read_byte_stream_from_file(
    '../a_getting_started/sinusodial_simulation.adcs', M)
control_signal_sequences3 = cbc.utilities.byte_stream_2_control_signal(
    byte_stream, M)


byte_stream = cbc.utilities.read_byte_stream_from_file(
    '../a_getting_started/sinusodial_simulation.adcs', M)
control_signal_sequences4 = cbc.utilities.byte_stream_2_control_signal(
    byte_stream, M)


###############################################################################
# Oversampling
# -------------
#

OSR = 16

omega_3dB = 2 * np.pi / (T * OSR)


###############################################################################
# Oversampling = 1
# ----------------------------------------
#
# First we initialize our default estimator without a downsampling parameter
# which then defaults to 1, i.e., no downsampling.

# Set the bandwidth of the estimator
G_at_omega = np.linalg.norm(
    analog_system.transfer_function_matrix(np.array([omega_3dB / 2])))
eta2 = G_at_omega**2
# eta2 = 1.0
print(f"eta2 = {eta2}, {10 * np.log10(eta2)} [dB]")

# Set the filter size
L1 = 1 << 12
L2 = L1

# Instantiate the digital estimator.
digital_estimator_ref = cbc.digital_estimator.FIRFilter(
    analog_system, digital_control, eta2, L1, L2)
digital_estimator_ref(control_signal_sequences1)

print(digital_estimator_ref, "\n")


###############################################################################
# Visualize Estimator's Transfer Function
# ---------------------------------------
#

# Logspace frequencies
frequencies = np.logspace(-3, 0, 100)
omega = 4 * np.pi * beta * frequencies

# Compute NTF
ntf = digital_estimator_ref.noise_transfer_function(omega)
ntf_dB = 20 * np.log10(np.abs(ntf))

# Compute STF
stf = digital_estimator_ref.signal_transfer_function(omega)
stf_dB = 20 * np.log10(np.abs(stf.flatten()))

# Signal attenuation at the input signal frequency
stf_at_omega = digital_estimator_ref.signal_transfer_function(
    np.array([omega_3dB]))[0]

# Plot
plt.figure()
plt.semilogx(frequencies, stf_dB, label='$STF(\omega)$')
for n in range(N):
    plt.semilogx(frequencies, ntf_dB[0, n, :], label=f"$|NTF_{n+1}(\omega)|$")
plt.semilogx(frequencies, 20 * np.log10(np.linalg.norm(
    ntf[:, 0, :], axis=0)), '--', label="$ || NTF(\omega) ||_2 $")

# Add labels and legends to figure
plt.legend()
plt.grid(which='both')
plt.title("Signal and noise transfer functions")
plt.xlabel("$\omega / (4 \pi \\beta ) $")
plt.ylabel("dB")
plt.xlim((frequencies[5], frequencies[-1]))
plt.gcf().tight_layout()

###############################################################################
# FIR Filter With Downsampling
# ----------------------------
#
# Next we repeat the initialization steps above but for a downsampled estimator

digital_estimator_dow = cbc.digital_estimator.FIRFilter(
    analog_system,
    digital_control,
    eta2,
    L1,
    L2,
    downsample=OSR)
digital_estimator_dow(control_signal_sequences2)

print(digital_estimator_dow, "\n")

###############################################################################
# Estimating (Filtering)
# ----------------------
#

# Set simulation length
size = 1 << 17
u_hat_ref = np.zeros(size)
u_hat_dow = np.zeros(size // OSR)
for index in range(size):
    u_hat_ref[index] = next(digital_estimator_ref)
for index in range(size // OSR):
    u_hat_dow[index] = next(digital_estimator_dow)

###############################################################################
# Aliasing
# ========
#
# We compare the difference between the downsampled estimate and the default.
# Clearly, we are suffering from aliasing as is also explained by considering
# the PSD plot.

# compensate the built in L1 delay of FIR filter.
t = np.arange(-L1 + 1, size - L1 + 1)
t_down = np.arange(-(L1) // OSR, (size - L1) // OSR) * OSR + 1
plt.plot(t, u_hat_ref, label="$\hat{u}(t)$ Reference")
plt.plot(t_down, u_hat_dow, label="$\hat{u}(t)$ Downsampled")
plt.xlabel('$t / T$')
plt.legend()
plt.title("Estimated input signal")
plt.grid(which='both')
plt.xlim((-50, 1000))
plt.tight_layout()

plt.figure()
u_hat_ref_clipped = u_hat_ref[(L1 + L2):]
u_hat_dow_clipped = u_hat_dow[(L1 + L2) // OSR:]
f_ref, psd_ref = cbc.utilities.compute_power_spectral_density(
    u_hat_ref_clipped, fs=1.0/T)
f_dow, psd_dow = cbc.utilities.compute_power_spectral_density(
    u_hat_dow_clipped, fs=1.0/(T * OSR))
plt.semilogx(f_ref, 10 * np.log10(psd_ref), label="$\hat{U}(f)$ Referefence")
plt.semilogx(f_dow, 10 * np.log10(psd_dow), label="$\hat{U}(f)$ Downsampled")
plt.legend()
plt.ylim((-300, 50))
plt.xlim((f_ref[1], f_ref[-1]))
plt.xlabel('$f$ [Hz]')
plt.ylabel('$ \mathrm{V}^2 \, / \, (1 \mathrm{Hz})$')
plt.grid(which='both')
plt.show()

###############################################################################
# Prepending a Virtual Bandlimiting Filter
# ----------------------------------------
#
# To battle the aliasing we extend the current estimator by placing a
# bandlimiting filter in front of the system. Note that this filter is a
# conceptual addition and not actually part of the physical analog system.
# Regardless, this effectively suppresses aliasing since we now reconstruct
# a signal shaped by both the STF of the system in addition
# to a bandlimiting filter.
#

wp = omega_3dB / 2.0
ws = omega_3dB
gpass = 0.1
gstop = 80

filter = cbc.analog_system.IIRDesign(wp, ws, gpass, gstop, ftype="ellip")

# Compute transfer functions for each frequency in frequencies
transfer_function_filter = filter.transfer_function_matrix(omega)

plt.semilogx(
    omega/(2 * np.pi),
    20 * np.log10(np.linalg.norm(
        transfer_function_filter[:, 0, :],
        axis=0)),
    label="Cauer")
# Add labels and legends to figure
# plt.legend()
plt.grid(which='both')
plt.title("Filter Transfer Functions")
plt.xlabel("$f$ [Hz]")
plt.ylabel("dB")
plt.xlim((5e1, 1e4))
plt.gcf().tight_layout()

###############################################################################
# New Analog System
# -------------------------------
#

new_analog_system = cbc.analog_system.chain([filter, analog_system])
print(new_analog_system)

transfer_function_analog_system = analog_system.transfer_function_matrix(omega)

transfer_function_new_analog_system = new_analog_system.transfer_function_matrix(
    omega)

plt.semilogx(
    omega/(2 * np.pi),
    20 * np.log10(np.linalg.norm(
        transfer_function_analog_system[:, 0, :],
        axis=0)),
    label="Default Analog System")
plt.semilogx(
    omega/(2 * np.pi),
    20 * np.log10(np.linalg.norm(
        transfer_function_new_analog_system[:, 0, :],
        axis=0)),
    label="Combined Analog System")

# Add labels and legends to figure
plt.legend()
plt.grid(which='both')
plt.title("Analog System Transfer Function")
plt.xlabel("$f$ [Hz]")
plt.ylabel("$||\mathbf{G}(\omega)||_2$ dB")
# plt.xlim((frequencies[0], frequencies[-1]))
plt.gcf().tight_layout()

###############################################################################
# New Digital Estimator
# --------------------------------------
#
# Combining the virtual pre filter together with the default analog system
# results in the following system.

digital_estimator_dow_and_pre_filt = cbc.digital_estimator.FIRFilter(
    new_analog_system,
    digital_control,
    eta2,
    L1,
    L2,
    downsample=OSR)
digital_estimator_dow_and_pre_filt(control_signal_sequences3)
print(digital_estimator_dow_and_pre_filt)


###############################################################################
# Post filtering the FIR filter coefficients
# -----------------------------------------------------------
#
# Yet another approach is to, instead of pre-filtering, post filter
# the resulting FIR filter coefficients with another lowpass FIR filter.

numtaps = 1 << 10
f_cutoff = 1.0 / OSR
fir_filter = scipy.signal.firwin(numtaps, f_cutoff)

digital_estimator_dow_and_post_filt = cbc.digital_estimator.FIRFilter(
    analog_system,
    digital_control,
    eta2,
    L1,
    L2,
    downsample=OSR)
digital_estimator_dow_and_post_filt(control_signal_sequences4)

# Apply the FIR post filter
digital_estimator_dow_and_post_filt.convolve(fir_filter)

print(digital_estimator_dow_and_post_filt, "\n")

FIR_frequency_response = np.fft.rfft(fir_filter)
f_FIR = np.fft.rfftfreq(numtaps, d=T)
plt.figure()
plt.semilogx(f_FIR, 20 * np.log10(np.abs(FIR_frequency_response)))
plt.xlabel('$f$ [Hz]')
plt.ylabel('$|h|$ dB')
plt.grid(which='both')

impulse_response_dB_dow = 20 * \
    np.log10(np.linalg.norm(
        np.array(digital_estimator_dow.h[0, :, :]), axis=1))

impulse_response_dB_dow_and_post_filt = 20 * \
    np.log10(np.linalg.norm(
        np.array(digital_estimator_dow_and_post_filt.h[0, :, :]), axis=1))

impulse_response_dB_FIR_filter = 20 * np.log10(np.abs(fir_filter[numtaps//2:]))

plt.figure()
plt.plot(np.arange(0, L1),
         impulse_response_dB_dow[L1:],
         label="Ref")
plt.plot(np.arange(0, numtaps//2),
         impulse_response_dB_FIR_filter,
         label="Post FIR Filter")
plt.plot(np.arange(0, L1),
         impulse_response_dB_dow_and_post_filt[L1:],
         label="Combined Post Filtered")

plt.legend()
plt.xlabel("filter tap k")
plt.ylabel("$|| \mathbf{h} [k]||_2$ [dB]")
plt.xlim((0, 1024))
plt.ylim((-160, 0))
plt.grid(which='both')

###############################################################################
# Plotting the Estimator's Signal and Noise Transfer Function
# -----------------------------------------------------------
#
# Next we visualize the resulting STF and NTF of the new digital estimator
# filters.

# Compute NTF
ntf_pre = digital_estimator_dow_and_pre_filt.noise_transfer_function(omega)
ntf_post = digital_estimator_dow_and_post_filt.noise_transfer_function(
    2 * np.pi * f_FIR) * FIR_frequency_response
ntf_dow = digital_estimator_dow.noise_transfer_function(omega)

# Compute STF
stf_pre = digital_estimator_dow_and_pre_filt.signal_transfer_function(omega)
stf_dB_pre = 20 * np.log10(np.abs(stf_pre.flatten()))
stf_post = digital_estimator_dow_and_post_filt.signal_transfer_function(
    2 * np.pi * f_FIR) * FIR_frequency_response
stf_dB_post = 20 * np.log10(np.abs(stf_post.flatten()))
stf_dow = digital_estimator_dow.signal_transfer_function(omega)
stf_dow_dB = 20 * np.log10(np.abs(stf_dow.flatten()))

# Plot
plt.figure()
plt.semilogx(omega/(2 * np.pi), stf_dB_pre, label='$STF(\omega)$ pre-filter')
plt.semilogx(f_FIR, stf_dB_post, label='$STF(\omega)$ post-filter')
plt.semilogx(omega/(2 * np.pi), stf_dow_dB,
             label='$STF(\omega)$ ref',  color='black')
plt.semilogx(omega/(2 * np.pi), 20 * np.log10(np.linalg.norm(
    ntf_pre[:, 0, :], axis=0)), '--', label="$ || NTF(\omega) ||_2 $ pre-filter")
plt.semilogx(f_FIR, 20 * np.log10(np.linalg.norm(
    ntf_post[:, 0, :], axis=0)), '--', label="$ || NTF(\omega) ||_2 $ post-filter")
plt.semilogx(omega/(2 * np.pi), 20 * np.log10(np.linalg.norm(
    ntf_dow[:, 0, :], axis=0)), '--', label="$ || NTF(\omega) ||_2 $ ref", color='black')

# Add labels and legends to figure
plt.legend()
plt.grid(which='both')
plt.title("Signal and noise transfer functions")
plt.xlabel("$f$ [Hz]")
plt.ylabel("dB")
plt.xlim((1e2, 5e3))
plt.gcf().tight_layout()

###############################################################################
# Filtering Estimate
# --------------------
#
# Finally, we plot the resulting input estimate PSD for each estimator.
# Clearly, both the pre and post filter effectively suppresses the aliasing
# effect.
#

u_hat_dow_and_pre_filt = np.zeros(size // OSR)
u_hat_dow_and_post_filt = np.zeros(size // OSR)
for index in cbc.utilities.show_status(range(size // OSR)):
    u_hat_dow_and_pre_filt[index] = next(digital_estimator_dow_and_pre_filt)
    u_hat_dow_and_post_filt[index] = next(digital_estimator_dow_and_post_filt)

plt.figure()
u_hat_dow_and_pre_filt_clipped = u_hat_dow_and_pre_filt[(L1 + L2) // OSR:]
u_hat_dow_and_post_filt_clipped = u_hat_dow_and_post_filt[(L1 + L2) // OSR:]
_, psd_dow_and_pre_filt = cbc.utilities.compute_power_spectral_density(
    u_hat_dow_and_pre_filt_clipped, fs=1.0/(T * OSR))
_, psd_dow_and_post_filt = cbc.utilities.compute_power_spectral_density(
    u_hat_dow_and_post_filt_clipped, fs=1.0/(T * OSR))
plt.semilogx(f_ref, 10 * np.log10(psd_ref), label="$\hat{U}(f)$ Referefence")
plt.semilogx(f_dow, 10 * np.log10(psd_dow), label="$\hat{U}(f)$ Downsampled")
plt.semilogx(f_dow, 10 * np.log10(psd_dow_and_pre_filt),
             label="$\hat{U}(f)$ Downsampled & Pre Filtered")
plt.semilogx(f_dow, 10 * np.log10(psd_dow_and_post_filt),
             label="$\hat{U}(f)$ Downsampled & Post Filtered")
plt.legend()
plt.ylim((-300, 50))
plt.xlim((f_ref[1], f_ref[-1]))
plt.xlabel('$f$ [Hz]')
plt.ylabel('$ \mathrm{V}^2 \, / \, (1 \mathrm{Hz})$')
plt.grid(which='both')
plt.show()

###############################################################################
# In Time Domain
# ---------------
#
# The corresponding estimate samples are plotted. As is evident from the plots
# the different filter realization all result in different filter lags.
# Naturally, the filter lag follows from the choice of K1, K2, and the pre or
# post filter design and is therefore a known parameter.

t = np.arange(size)
t_down = np.arange(size // OSR) * OSR
plt.plot(t, u_hat_ref, label="$\hat{u}(t)$ Reference")
plt.plot(t_down, u_hat_dow, label="$\hat{u}(t)$ Downsampled")
plt.plot(t_down, u_hat_dow_and_pre_filt,
         label="$\hat{u}(t)$ Downsampled and Pre Filtered")
plt.plot(t_down, u_hat_dow_and_post_filt,
         label="$\hat{u}(t)$ Downsampled and Post Filtered")
plt.xlabel('$t / T$')
plt.legend()
plt.title("Estimated input signal")
plt.grid(which='both')
offset = (L1 + L2) * 4
plt.xlim((offset, offset + 1000))
plt.ylim((-0.6, 0.6))
plt.tight_layout()

###############################################################################
# Compare Filter Coefficients
# ---------------------------
#
# Futhermore, the filter coefficient's magnitude decay varies for the different
# implementations. Keep in mind that the for this example the pre and post
# filter are parametrized such that the formed slightly outperforms the latter
# in terms of precision (see the PSD plot above).

impulse_response_dB_dow_and_pre_filt = 20 * \
    np.log10(np.linalg.norm(
        np.array(digital_estimator_dow_and_pre_filt.h[0, :, :]), axis=1))

plt.plot(np.arange(0, L1),
         impulse_response_dB_dow[L1:],
         label="Ref")

plt.plot(np.arange(0, L1),
         impulse_response_dB_dow_and_pre_filt[L1:],
         label="Pre Filtered")
plt.plot(np.arange(0, L1),
         impulse_response_dB_dow_and_post_filt[L1:],
         label="Post Filtered")
plt.legend()
plt.xlabel("filter tap k")
plt.ylabel("$|| \mathbf{h} [k]||_2$ [dB]")
plt.xlim((0, 1024))
plt.ylim((-160, -20))
plt.grid(which='both')

# sphinx_gallery_thumbnail_number = 9
