from cbadc.simulator import get_simulator
from cbadc.digital_estimator import BatchEstimator
from cbadc.analog_signal import ConstantSignal, Clock
from cbadc.analog_system import AnalogSystem
from cbadc.digital_control import DigitalControl

import numpy as np
from tests.fixture.chain_of_integrators import chain_of_integrators

beta = 6250.0
rho = -62.5
N = 2
M = 2
A = np.eye(N) * rho + np.eye(N, k=-1) * beta
B = np.zeros((N, 1))
B[0, 0] = beta
# B[0, 1] = -beta
CT = np.eye(N)
Gamma_tildeT = np.eye(M)
Gamma = Gamma_tildeT * (-beta)
Ts = 1 / (2 * beta)


def controlSequence():
    while True:
        yield np.ones(M, dtype=np.uint8)


def test_initialization():
    clock = Clock(Ts)
    digitalControl = DigitalControl(clock, M)
    analog_system = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    eta2 = 1.0
    K1 = 100
    K2 = 0
    BatchEstimator(analog_system, digitalControl, eta2, K1, K2)


def test_estimation():
    clock = Clock(Ts)
    digitalControl = DigitalControl(clock, M)
    eta2 = 100.0
    K1 = 100
    K2 = 10

    analogSystem = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)

    estimator = BatchEstimator(
        analogSystem, digitalControl, eta2, K1, K2, stop_after_number_of_iterations=25
    )
    estimator(controlSequence())
    for est in estimator:
        print(np.array(est))


def test_batch_iterations():
    clock = Clock(Ts)
    digitalControl = DigitalControl(clock, M)
    eta2 = 100.0
    K1 = 25
    K2 = 1000

    analogSystem = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    estimator = BatchEstimator(
        analogSystem,
        digitalControl,
        eta2,
        K1,
        K2=K2,
        stop_after_number_of_iterations=200,
    )
    estimator(controlSequence())
    for est in estimator:
        print(np.array(est))
    # raise "temp"


def test_estimation_simulator():
    eta2 = 1e12
    K1 = 1000
    K2 = 0

    analogSystem = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    # analogSignals = [Sinusoidal(0.5, 10)]
    analogSignals = [ConstantSignal(0.25)]
    clock = Clock(Ts)
    digitalControl = DigitalControl(clock, M)
    circuitSimulator = get_simulator(
        analogSystem, digitalControl, analogSignals, clock, t_stop=Ts * 1000
    )
    estimator = BatchEstimator(analogSystem, digitalControl, eta2, K1, K2)
    estimator(circuitSimulator)
    for est in estimator:
        print(est)
    # raise "Temp"


def test_ntf():
    eta2 = 1e4
    K1 = 1 << 8
    K2 = K1
    analogSystem = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    clock = Clock(Ts)
    digitalControl = DigitalControl(clock, M)
    estimator = BatchEstimator(analogSystem, digitalControl, eta2, K1, K2)
    omega = np.logspace(-5, 0) * beta
    ntf = estimator.noise_transfer_function(omega)
    print(ntf)


def test_stf():
    eta2 = 1e4
    K1 = 1 << 8
    K2 = K1
    analogSystem = AnalogSystem(A, B, CT, Gamma, Gamma_tildeT)
    clock = Clock(Ts)
    digitalControl = DigitalControl(clock, M)
    estimator = BatchEstimator(analogSystem, digitalControl, eta2, K1, K2)
    omega = np.logspace(-5, 0) * beta
    stf = estimator.signal_transfer_function(omega)
    print(stf)
