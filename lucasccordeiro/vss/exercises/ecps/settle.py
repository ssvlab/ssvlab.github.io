def settle(setpoint: int) -> int:
    """Ramp the heater until the measured temperature reaches the setpoint.
    The actuator moves in fixed 2-degree steps."""
    temp = 0
    while temp != setpoint:
        temp = temp + 2
    return temp

settle(10)  # reachable in 5 ticks
settle(7)   # unreachable: an odd setpoint is never hit in steps of 2
