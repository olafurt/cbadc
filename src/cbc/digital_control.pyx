#cython: language_level=3
import numpy as np

cdef class DigitalControl:
    """Represents a digital control system.

    This is the simplest digital control where
    :math:`M=\\tilde{M}` and each control signal is updated
    independently. Furthermore, the DAC waveform is a constant signal
    as :math:`\mathbf{s}(t)=\mathbf{s}[k]` for :math:`t\in[k T, (k+1)T)`.

    Parameters
    ----------
    T : `float`
        clock period at which the digital control updates.
    M : `int`
        number of controls.
    t0 : `float`: optional
        determines inital time, defaults to 0.

    Attributes
    ----------
    T : `float`
        clock period :math:`T` of digital control system.
    M : `int`
        number of controls :math:`M`.
    M_tilde : `int`
        number of control observations :math:`\\tilde{M}`.

    Note
    ----
    For this digital control system :math:`M=\\tilde{M}`.

    See also
    ---------
    :py:class:`cbc.state_space_simulator.StateSpaceSimulator`

    Examples
    --------
    TODO: this needs doing
    """

    def __init__(self, T, M, t0 = 0.0):
        self.T = T
        self._M = M
        self._M_tilde = M
        self._t_next = t0 + self.T
        self._s = np.zeros(self._M, dtype=np.int8)
        self._dac_values = np.zeros(self._M, dtype=np.double)

    cpdef double [:] evaluate(self, double t, double [:] s_tilde):
        """Evaluates the control signal at time t given a control observation s_tilde

        Parameters
        ----------
        t : `float`
            time at which the digital control i evaluated.
        s_tilde : `array_like`, shape=(M_tilde,)
            state vector evaluated at time t

        Returns
        -------
        `array_like`, shape=(M,)
            the control signal :math:`\mathbf{s}(t)`

        """
        cdef int m
        # Check if time t has passed the next control update
        if t >= self._t_next:
            # if so update the control signal state
            for m in range(self._M):
                self._s[m] = s_tilde[m] > 0
                if self._s[m]:
                    self._dac_values[m] = 1 
                else: 
                    self._dac_values[m] = -1
            self._t_next += self.T
        # DAC
        return self._dac_values
        
    cpdef char [:] control_signal(self):
        """Returns the current control state, i.e, :math:`\mathbf{s}[k]`.

        Returns
        -------
        `array_like`, shape=(M,), dtype=numpy.int8
            current control state.
        """
        return self._s

    cdef double [:] impulse_response(self, m, t):
        """The impulse response of the corresponding DAC waveform

        Parameters
        ----------
        m : `int`
            determines which :math:`m\in\{0,\dots,M-1\}` control dimension
            which is triggered.
        t : `float`
            evaluate the impulse response at time t.

        Returns
        -------
        `array_like`, shape=(M,)
            the dac waveform of the digital control system.
        
        """
        temp = np.zeros(self._M, dtype=np.double)
        temp[m] = 1
        return temp
