from cbadc.analog_system cimport AnalogSystem
from cbadc.digital_control cimport DigitalControl
from cbadc.analog_signal cimport AnalogSignal
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm
import math


cdef class StateSpaceSimulator(object):
    """Simulate the analog system and digital control interactions
    in the precense on analog signals.

    Parameters
    ----------
    analog_system : :py:class:`cbadc.analog_system.AnalogSystem`
        the analog system
    digital_control: :py:class:`cbadc.digital_control.DigitalControl`
        the digital control
    input_signals : [:py:class:`cbadc.analog_signal.AnalogSignal`]
        a python list of analog signals (or a derived class)
    Ts : `float`, optional
        specify a sampling rate at which we want to evaluate the systems
        , defaults to digitalContro.Ts. Note that this Ts must be smaller 
        than digital_control.Ts. 
    t_stop : `float`, optional
        determines a stop time, defaults to :py:obj:`math.inf`



    Attributes
    ----------
    analog_system : :py:class:`cbadc.analog_system.AnalogSystem`
        the analog system being simulated.
    digital_control : :py:class:`cbadc.digital_control.DigitalControl`
        the digital control being simulated.
    t : `float`
        current time of simulator.
    Ts : `float` 
        sample rate of simulation.
    t_stop : `float`
        end time at which the generator raises :py:class:`StopIteration`.
    rtol, atol : `float`, `optional`
        Relative and absolute tolerances. The solver keeps the local error estimates less 
        than atol + rtol * abs(y). Effects the underlying solver as described in 
        :py:func:`scipy.integrate.solve_ivp`. Default to 1e-3 for rtol and 1e-6 for atol.
    max_step : `float`, `optional`
        Maximum allowed step size. Default is np.inf, i.e., the step size is not 
        bounded and determined solely by the solver. Effects the underlying solver as 
        described in :py:func:`scipy.integrate.solve_ivp`. Defaults to :py:obj:`math.inf`. 
    See also
    --------
    :py:class:`cbadc.analog_signal.AnalogSignal`
    :py:class:`cbadc.analog_system.AnalogSystem`
    :py:class:`cbadc.digital_control.DigitalControl`

    Examples
    --------
    >>> from cbadc import StateSpaceSimulator, Sinusodial, AnalogSystem, DigitalControl
    >>> import numpy as np
    >>> A = np.array([[0., 0], [6250., 0.]])
    >>> B = np.array([[6250., 0]]).transpose()
    >>> CT = np.array([[1, 0], [0, 1]])
    >>> Gamma = np.array([[-6250, 0], [0, -6250]])
    >>> Gamma_tildeT = CT
    >>> analog_system = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    >>> digital_control = DigitalControl(1e-6, 2)
    >>> input_signal = Sinusodial(1.0, 250)
    >>> simulator = StateSpaceSimulator(analog_system, digital_control, (input_signal,))
    >>> _ = simulator.__next__()
    >>> _ = simulator.__next__()
    >>> print(np.array(simulator.__next__()))
    [1 1]
    
    See also
    --------

    Yields
    ------
    `array_like`, shape=(M,), dtype=numpy.int8
    
    Raises
    ------
    str : unknown

    """
    cdef readonly AnalogSystem analog_system
    cdef readonly DigitalControl digital_control
    cdef dict __dict__
    cdef readonly double t, Ts, t_stop
    cdef double [:] _state_vector
    cdef double [:] _input_vector,_control_vector, _temp_state_vector, _control_observation
    cdef double [:] _char_control_vector, _res
    cdef double [:,:] _pre_computed_state_transition_matrix
    cdef double [:,:] _pre_computed_control_matrix
    cdef double _atol, _rtol, _max_step
        
    def __init__(self, 
            AnalogSystem analog_system, 
            DigitalControl digital_control, 
            input_signal, 
            Ts=None,
            t_stop=math.inf,
            atol = 1e-6,
            rtol = 1e-3,
            max_step = math.inf,
        ):
        if analog_system.L != len(input_signal):
            raise """The analog system does not have as many inputs as in input
            list"""
        self.analog_system = analog_system
        self.digital_control = digital_control
        self.input_signals = input_signal
        self.t_stop = t_stop
        if Ts:
            self.Ts = Ts
        else:
            self.Ts = self.digital_control.T
        if self.Ts > self.digital_control.T:
            raise f"Simulating with a sample period {self.Ts} that exceeds the control period of the digital control {self.digital_control.T}"
        self._state_vector = np.zeros(self.analog_system.N, dtype=np.double)
        self._temp_state_vector = np.zeros(self.analog_system.N, dtype=np.double)
        self._control_observation = np.zeros(self.analog_system.M_tilde, dtype=np.double)
        self._input_vector = np.zeros(self.analog_system.L, dtype=np.double)
        self._control_vector = np.zeros(self.analog_system.M, dtype=np.double)
        self._res = np.zeros(self.analog_system.N, dtype=np.double)
        self._atol = atol # 1e-6
        self._rtol = rtol # 1e-6
        self._max_step = max_step # self.Ts / 10.
        self._pre_computations()
        # self.solve_oder = self._ordinary_differential_solution
        # self.solve_oder = self._full_ordinary_differential_solution
    
    def state_vector(self):
        """return current analog system state vector :math:`\mathbf{x}(t)`
        evaluated at time :math:`t`.

        Examples
        --------
        >>> from cbadc import StateSpaceSimulator, Sinusodial, AnalogSystem, DigitalControl
        >>> import numpy as np
        >>> A = np.array([[0., 0], [6250., 0.]])
        >>> B = np.array([[6250., 0]]).transpose()
        >>> CT = np.array([[1, 0], [0, 1]])
        >>> Gamma = np.array([[-6250, 0], [0, -6250]])
        >>> Gamma_tildeT = CT
        >>> analog_system = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
        >>> digital_control = DigitalControl(1e-6, 2)
        >>> input_signal = Sinusodial(1.0, 250)
        >>> simulator = StateSpaceSimulator(analog_system, digital_control, (input_signal,))
        >>> _ = simulator.__next__()
        >>> _ = simulator.__next__()
        >>> print(np.array(simulator.state_vector()))
        [0.01217279 0.01222796]

        Returns
        -------
        `array_like`, shape=(N,)
            returns the state vector :math:`\mathbf{x}(t)`
        """
        return self._state_vector[:]

    def __iter__(self):
        """Use simulator as an iterator
        """
        return self
    
    def __next__(self):
        """Computes the next control signal :math:`\mathbf{s}[k]`
        """
        cdef double t_end = self.t + self.Ts
        cdef double[2] t_span = (self.t, t_end)
        cdef double[1] t_eval = (t_end,)
        if t_end >= self.t_stop:
            raise StopIteration
        self._state_vector = self._ordinary_differential_solution(t_span)
        # self._state_vector = self._full_ordinary_differential_solution(t_span)
        self.t = t_end
        return self.digital_control.control_signal()

    cdef double [:, :] _analog_system_matrix_exponential(self, double t):
        return expm(np.asarray(self.analog_system.A) * t)

    cdef _pre_computations(self):
        """Precomputes quantites for quick evaluation of state transistion and control
        contribution.

        Specifically, 

        :math:`\exp\\left(\mathbf{A} T_s \\right)`

        and 

        :math:`\mathbf{A}_c = \int_{0}^{T_s} \exp\\left(\mathbf{A} (T_s - \tau)\\right) \mathbf{\Gamma} \mathbf{d}(\tau) \mathrm{d} \tau`

        are computed where the formed describes the state transition and the latter 
        the control contributions. Furthermore, :math:`\mathbf{d}(\tau)` is the DAC waveform 
        (or impulse response) of the digital control.
        """

        # expm(A T_s)
        self._pre_computed_state_transition_matrix = self._analog_system_matrix_exponential(self.Ts)

        def derivative(t, x):
            dac_waveform = np.zeros((self.analog_system.M, self.analog_system.M)) 
            for m in range(self.analog_system.M):
                dac_waveform[:, m] = self.digital_control.impulse_response(m, t)
            return np.dot(
                np.asarray(self._analog_system_matrix_exponential(self.Ts - t)), 
                    np.dot(np.asarray(self.analog_system.Gamma), 
                        dac_waveform)
                    ).flatten()
        
        cdef double [:] tspan = np.array([0, self.Ts])
        cdef double atol = 1e-20
        cdef double rtol = 1e-13
        cdef double max_step = self.Ts * 1e-4
        
        self._pre_computed_control_matrix = solve_ivp(derivative, 
            tspan, 
            np.zeros((self.analog_system.N * self.analog_system.M)), 
            atol=atol, rtol=rtol, max_step=max_step
            ).y[:,-1].reshape((self.analog_system.N, self.analog_system.M), order='C')
        print(f"self._pre_computed_control_matrix: {np.asarray(self._pre_computed_control_matrix)}")
    
    cdef double [:] _ordinary_differential_solution(self, t_span):
        """Computes system ivp in three parts:

        First solve input signal contribution by computing

        :math:`\mathbf{u}_{c} = \int_{t_1}^{t_2} \mathbf{A} x(t) + \mathbf{B} \mathbf{u}(t) \mathrm{d} t`

        where :math:`\mathbf{x}(t_1) = \begin{pmatrix} 0, & \dots, & 0 \end{pmatrix}^{\mathsf{T}}`.

        Secondly advance the previous state as

        :math:`\mathbf{x}_c = \mathbf{x}(t_2) = \exp\\left( \mathbf{A} T_s \\right) \mathbf{x}(t_1)`

        Thirdly, compute the control contribution by 

        :math:`\mathbf{s}_c = \mathbf{A}_c \mathbf{s}[k]`

        where :math:`\mathbf{A}_c = \int_{0}^{T_s} \exp\\left(\mathbf{A} (T_s - \tau)\\right) \mathbf{\Gamma} \mathbf{d}(\tau) \mathrm{d} \tau`
        and :math:`\mathbf{d}(\tau)` is the DAC waveform (or impulse response) of the digital control.

        Finally, all contributions are added and returned as

        :math:`\mathbf{u}_{c} + \mathbf{x}_c + \mathbf{s}_c`.

        Parameters
        ----------
        t_span : (float, float)
            the inital time :math:`t_1` and end time :math:`t_2` of the simulations.

        Returns
        -------
        array_like, shape=(N,)
            computed state vector.
        """
        cdef int n = 0
        cdef int nn = 0 
        cdef int m = 0 
        cdef int m_tilde = 0

        # Compute signal contribution
        def f(t, x):
            return self._signal_derivative(t, x)
        self._temp_state_vector =  solve_ivp(
            f, 
            t_span, 
            np.zeros(self.analog_system.N), 
            atol=self._atol, 
            rtol=self._rtol, 
            max_step=self._max_step
            ).y[:,-1]
        
        for n in range(self.analog_system.N):
            for nn in range(self.analog_system.N):
                self._temp_state_vector[n] += self._pre_computed_state_transition_matrix[n, nn]  *  self._state_vector[nn]
        
        # Compute control observation s_tilde(t)
        for m_tilde in range(self.analog_system.M_tilde):
            self._control_observation[m_tilde] = 0
            for n in range(self.analog_system.N):
                self._control_observation[m_tilde] += self.analog_system.Gamma_tildeT[m_tilde, n] * self._state_vector[n]
        # update control at time t_span[0]
        self._char_control_vector = self.digital_control.control_contribution(t_span[0], self._control_observation)
        for n in range(self.analog_system.N):
            for m in range(self.analog_system.M):
                self._temp_state_vector[n] += self._pre_computed_control_matrix[n, m] * self._char_control_vector[m]
        return self._temp_state_vector


    cdef double [:] _signal_derivative(self, double t, double [:] x):
        cdef int l = 0
        cdef int n = 0
        cdef int nn = 0
        for n in range(self.analog_system.N):
            self._res[n] = 0
            for nn in range(self.analog_system.N):
                self._res[n] += self.analog_system.A[n, nn] * x[nn]
            for l in range(self.analog_system.L):
                self._res[n] += self.analog_system.B[n, l] * self.input_signals[l].evaluate(t)
        return np.asarray(self._res)

    cdef double [:] _full_ordinary_differential_solution(self, t_span):
        def f(t, x):
            return self._ordinary_differentail_function(t, x)
        return solve_ivp(
            f, 
            t_span, 
            self._state_vector, 
            atol=self._atol, 
            rtol=self._rtol, 
            max_step=self._max_step
            ).y[:,-1]

    cdef _ordinary_differentail_function(self, t, y):
        """Solve the differential computational problem
        of the analog system and digital control interaction

        Parameters
        ----------
        t : `float`
            the time for evaluation
        y : array_lik, shape=(N,)
            state vector
        
        Returns
        -------
        array_like, shape=(N,)
            vector of derivatives evaluated at time t.
        """
        cdef int l,
        for l in range(self.analog_system.L):
            self._input_vector[l] = self.input_signals[l].evaluate(t)
        self._temp_state_vector = np.dot(self.analog_system.Gamma_tildeT, y)
        self._control_vector = self.digital_control.control_contribution(t, self._temp_state_vector)
        return np.asarray(self.analog_system.derivative(self._temp_state_vector, t, self._input_vector, self._control_vector)).flatten()


