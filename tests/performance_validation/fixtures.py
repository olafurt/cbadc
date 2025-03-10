from cbadc.specification import get_chain_of_integrator, get_leap_frog


def setup_filter(
    N, ENOB, BW, analog_system, digital_control, excess_delay=0.0, local_feedback=False
):
    res = {'N': N, 'ENOB': ENOB, 'BW': BW}
    if analog_system == 'chain-of-integrators':
        analog_system, digital_control = get_chain_of_integrator(
            N=N,
            BW=BW,
            ENOB=ENOB,
            digital_control=digital_control,
            excess_delay=excess_delay,
            local_feedback=local_feedback,
        )
        res['analog_system'] = analog_system
        res['digital_control'] = digital_control
    elif analog_system == 'leap_frog':
        analog_system, digital_control = get_leap_frog(
            N=N,
            BW=BW,
            ENOB=ENOB,
            digital_control=digital_control,
            excess_delay=excess_delay,
            local_feedback=local_feedback,
        )
        res['analog_system'] = analog_system
        res['digital_control'] = digital_control
    return res


def pytest_generate_tests(metafunc):
    if all(
        fix in metafunc.fixturenames
        for fix in ('analog_system_and_digital_control', 'N', 'BW', 'ENOB')
    ):
        N = metafunc.config.getoption("N")
        BW = metafunc.config.getoption("BW")
        ENOB = metafunc.config.getoption("ENOB")
        analog_system_and_digital_control_CI = get_chain_of_integrator(
            N=N, BW=BW, ENOB=ENOB
        )
        analog_system_and_digital_control_LF = get_leap_frog(N=N, BW=BW, ENOB=ENOB)
        metafunc.parametrize(
            "analog_system_and_digital_control",
            [
                analog_system_and_digital_control_CI,
                analog_system_and_digital_control_LF,
            ],
            ids=["chain-of-integrators", "leap-frog"],
        )
