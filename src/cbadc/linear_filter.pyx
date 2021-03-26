"""
The digital estimator.
"""
#cython: language_level=3
from cbadc.offline_computations import care
from scipy.linalg import expm, solve
from scipy.integrate import solve_ivp
from numpy import dot as dot_product, eye, zeros, int8, double, roll, array


cdef class LinearFilter():

    def __cinit__(self, AnalogSystem analog_system, DigitalControl digital_control, double eta2, int K1, int K2 = 0):
        """Initializes filter object by computing filter coefficents and allocation buffer memory.

        Args:
            analog_system (:obj:`AnalogSystem`): an anlog system
            digital_control (:obj:`DigitalControl`): a digital control
            eta2 (float): the bandwidth parameter.
            K1 (int): the batch size
            K2 (int): the lookahead size  
        """
        self._M = analog_system.M
        self._N = analog_system.N
        self._L = analog_system.L
        self._K1 = K1
        self._K2 = K2
        self._K3 = K1 + K2
        self.compute_filter_coefficients(analog_system, digital_control, eta2)
        self.allocate_memory_buffers()
    
    cpdef void compute_batch(self):
        cdef int k1, k2, k3
        cdef double [:] temp_forward_mean
        temp_forward_mean = zeros(self._N, dtype=double) 
        # check if ready to compute buffer
        if (self._control_signal_in_buffer < self._K3):
            raise "Control signal buffer not full"
        # compute lookahead
        # print(array(self._control_signal))
        for k1 in range(self._K3, self._K1, -1):
            temp = dot_product(self._Ab, self._mean[self._K1,:]) + dot_product(self._Bb, self._control_signal[k1, :])
            for n in range(self._N):
                self._mean[self._K1, n] = temp[n]
        # print(array(self._mean[self._K1, :]))
        # compute forward recursion
        for k2 in range(1, self._K1):
            temp = dot_product(self._Af, self._mean[k2 - 1, :]) + dot_product(self._Bf, self._control_signal[k2 - 1, :])
            for n in range(self._N):
                self._mean[k2, n] = temp[n]
            # print(array(self._mean[k2, :]))
        for n in range(self._N):
            temp_forward_mean[n] = self._mean[self._K1 - 1, n]
        # compute backward recursion and estimate
        # print("Backward")
        for k3 in range(self._K1, 0, -1):
            temp = dot_product(self._Ab, self._mean[k3, :]) + dot_product(self._Bb, self._control_signal[k3-1, :])
            temp_estimate = dot_product(self._WT, temp - self._mean[k3-1, :])
            for l in range(self._L):
                self._estimate[k3 - 1, l] = temp_estimate[l]
            for n in range(self._N):
                self._mean[k3 - 1, n] = temp[n]
            # print(array(self._mean[k3-1, :]))
        # reset intital means
        for n in range(self._N):
            self._mean[0, n] = temp_forward_mean[n]
            self._mean[self._K1, n] = 0
        # print(array(self._mean))
        # rotate buffer to make place for new control signals
        self._control_signal = roll(self._control_signal, -self._K1, axis=0)
        self._control_signal_in_buffer -= self._K1
        
    cdef void compute_filter_coefficients(self, AnalogSystem analog_system, DigitalControl digital_control, double eta2):
        # Compute filter coefficients
        A = array(analog_system.A).transpose()
        B = array(analog_system.CT).transpose()
        Q = dot_product(array(analog_system.B), array(analog_system.B).transpose())
        R = eta2 * eye(analog_system.N_tilde)
        # Solve care
        Vf, Vb = care(A, B, Q, R)
        cdef double T = digital_control.T
        CCT = dot_product(array(analog_system.CT).transpose(), array(analog_system.CT))
        tempAf = analog_system.A - dot_product(Vf,CCT) / eta2
        tempAb = analog_system.A + dot_product(Vb,CCT) / eta2
        self._Af = expm(tempAf * T)
        self._Ab = expm(-tempAb * T)
        Gamma = array(analog_system.Gamma)
        # Solve IVPs
        self._Bf = zeros((self._N, self._M))
        self._Bb = zeros((self._N, self._M))

        atol = 1e-200
        rtol = 1e-10
        max_step = T/1000.0
        for m in range(self._M):
            derivative = lambda t, x: dot_product(tempAf, x) + dot_product(Gamma, digital_control.impulse_response(m, t))
            solBf = solve_ivp(derivative, (0, T), zeros(self._N), atol=atol, rtol=rtol, max_step=max_step).y[:,-1]
            derivative = lambda t, x: - dot_product(tempAb, x) + dot_product(Gamma, digital_control.impulse_response(m, t))
            solBb = -solve_ivp(derivative, (0, T), zeros(self._N), atol=atol, rtol=rtol, max_step=max_step).y[:,-1]
            for n in range (self._N):
                self._Bf[n, m] = solBf[n]
                self._Bb[n, m] = solBb[n]

        # Solve linear system of equations
        # print(f"New Bf: {array(self._Bf)}")
        # print(f"New Bb: {array(self._Bb)}")
        self._WT = solve(Vf + Vb, analog_system.B).transpose()

    cdef void allocate_memory_buffers(self):
        # Allocate memory buffers
        self._control_signal = zeros((self._K3 + 1, self._M), dtype=int8)
        self._estimate = zeros((self._K1, self._L), dtype=double)
        self._control_signal_in_buffer = 0
        self._mean = zeros((self._K1 + 1, self._N), dtype=double)


    def input(self, char [:] s):
        if (self._control_signal_in_buffer == self._K3 + 1):
            raise "Input buffer full. You must compute batch before adding more control signals"
        for m in range(self._M):
            self._control_signal[self._control_signal_in_buffer, m] = 2 * s[m] - 1
        self._control_signal_in_buffer += 1
        return self._control_signal_in_buffer == (self._K3)

    def output(self, int index):
        if (index < 0 or index >= self._K1):
            raise "index out of range"
        return array(self._estimate[index, :], dtype=double)
    
    cpdef int batch_size(self):
        return self._K1

    cpdef int lookahead(self):
        return self._K2

    cpdef int size(self):
        return self._K3