# import requests
# import mysql.connector
# import pandas as pd

# open from 9AM to 5PM (t=0 and t=8)
# simulate
# 1st shift: A B C D workers
# new customer every 10 minutes
# salon capacity = 15, if customer arrives when full, the customer leaves -> unhappy customer
# worker can only work on one customer, takes between 20-40 minutes -> happy customer
# customer can wait maximum of 30 minutes, if he's not taken by then -> unhappy customer
# 4 hour shifts, will go home immediately unless there's a customer being serviced
# 2nd shift: E F G H, go home at 5PM (t=8)
# closes at 5, any arrivals after that -> unhappy customer

# output: [Salon time: HH:MM]


# I've tested multiple scenarios by changing the capacity and increasing customer count, all seemed to have worked well
# See comments in main about intesity

from collections import deque
from random import seed, randint


def _minutes_to_hhmm(minutes):
    hours = minutes // 60
    # add offset
    hours += 9
    hours = str(hours)
    if len(hours) == 1:
        hours = '0' + hours
    hour_minutes = minutes % 60
    hour_minutes = str(hour_minutes)
    if len(hour_minutes) == 1:
        hour_minutes = '0' + hour_minutes

    return hours + ':' + hour_minutes


# quick and dirty tests, normally I wouldn't do it like this.
assert _minutes_to_hhmm(0) == '09:00'
assert _minutes_to_hhmm(1) == '09:01'
assert _minutes_to_hhmm(480) == '17:00'


def _print_with_time(minute, who, action):
    pretty_time = _minutes_to_hhmm(minute)
    print(f'[{pretty_time}] [{who}] {action}')


class Barber(object):
    def __init__(self, starts_at, ends_at, name):
        self.str_id = name
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.active_customer_finish_at = None
        self.active_customer_name = None


class Customer(object):
    def __init__(self, arrives_at, name, time_to_process):
        self.arrives_at = arrives_at
        self.str_id = name
        self.time_to_process = time_to_process
        self.waits_until = None


class HairSalon(object):
    def __init__(self, capacity, opens_at, closes_at, barbers_to_start, customers_to_start):
        self.capacity = capacity
        self.waiting_customers = deque()
        self.barbers_to_start = barbers_to_start
        self.active_barbers = []
        self.customers_to_start = customers_to_start
        self.opens_at = opens_at
        self.closes_at = closes_at
        self.str_id = 'Hair Salon'

    def can_append_customer(self):
        return len(self.waiting_customers) < self.capacity

    def simulate_begin_shift(self, minute):
        for waiting_barber in self.barbers_to_start:
            if waiting_barber.starts_at == minute:
                _print_with_time(minute, waiting_barber.str_id, '[started] shift')
                self.active_barbers.append(waiting_barber)

    def simulate_end_shift(self, minute):
        to_remove = []
        for barber in self.active_barbers:
            if minute == barber.active_customer_finish_at:
                _print_with_time(minute, barber.str_id,
                                 f"[ended] cutting [{barber.active_customer_name}]'s hair")
                _print_with_time(minute, barber.active_customer_name,
                                 f"left [satisfied]")
                barber.active_customer_finish_at = None
                barber.active_customer_name = None
            if minute >= barber.ends_at:
                if not barber.active_customer_name:
                    _print_with_time(minute, barber.str_id, f"[ended] shift")
                    to_remove.append(barber)

        # remove barbers that ended shift.
        for barber in to_remove:
            self.active_barbers.remove(barber)

    def simulate_close(self, minute):
        if len(self.active_barbers) == 0:
            assert minute >= self.closes_at
            for customer in self.waiting_customers:
                _print_with_time(minute, customer.str_id, 'left [furious]')
            _print_with_time(minute, self.str_id, '[closed]')
            self.waiting_customers = deque()
            return False
        else:
            return True

    def simulate_incoming_customers(self, minute):
        for customer in self.customers_to_start:
            if customer.arrives_at == minute:
                _print_with_time(minute, customer.str_id, 'entered')
                if minute > self.closes_at:
                    _print_with_time(minute, customer.str_id, 'left [cursing themselves]')
                elif not self.can_append_customer():
                    _print_with_time(minute, customer.str_id, 'left [impatiently]')
                else:
                    customer.waits_until = minute + 30
                    self.waiting_customers.append(customer)

    def simulate_waiting_customers(self, minute):
        to_remove = []
        for customer in self.waiting_customers:
            # try to find a free barber.
            for active_barber in self.active_barbers:
                if not active_barber.active_customer_name:
                    # let's service this customer.
                    active_barber.active_customer_name = customer.str_id
                    active_barber.active_customer_finish_at = minute + customer.time_to_process
                    _print_with_time(minute, active_barber.str_id, f"[started] cutting [{customer.str_id}]'s hair")
                    to_remove.append(customer)
                    break
            else:
                # no free barber, customer unserviced.
                if minute == customer.waits_until:
                    _print_with_time(minute, customer.str_id, "[left] unfulfilled")
                    to_remove.append(customer)

                assert minute <= customer.waits_until

        # remove customers that started processing or those that left.
        for customer in to_remove:
            self.waiting_customers.remove(customer)

    def simulate_minute(self, minute):
        if minute == self.opens_at:
            _print_with_time(minute, self.str_id, '[opened]')

        self.simulate_begin_shift(minute)

        self.simulate_end_shift(minute)

        # close if possible
        if not self.simulate_close(minute):
            return False

        self.simulate_incoming_customers(minute)

        # process waiting customers in the FIFO order.
        self.simulate_waiting_customers(minute)

        return True

    def simulate(self, end_time):
        for minute in range(end_time + 1):
            if not self.simulate_minute(minute):
                break


def main():
    seed()

    # generate customers.
    total_time = 8 * 60

    # this isn't quite what the task wants, what we want is to use
    # exponetial random variable with intensity=10 minutes, but this is much easier.
    customers_to_generate = total_time // 10

    max_time = total_time + (10)  # + 10 minutes for late arrivals
    customers = [Customer(arrives_at=randint(0, max_time),
                          name=None,
                          time_to_process=randint(20, 40)) for _ in range(customers_to_generate)]
    customers = sorted(customers, key=lambda _: _.arrives_at)
    for i, customer in enumerate(customers):
        customer.str_id = f'Customer-{i + 1}'

    # generate barbers.
    first_shift_end = 4 * 60
    second_shift_end = total_time
    barbers = [Barber(name='Anne', starts_at=0, ends_at=first_shift_end),
               Barber(name='Ben', starts_at=0, ends_at=first_shift_end),
               Barber(name='Carol', starts_at=0, ends_at=first_shift_end),
               Barber(name='Derek', starts_at=0, ends_at=first_shift_end),
               Barber(name='Erin', starts_at=first_shift_end, ends_at=second_shift_end),
               Barber(name='Frank', starts_at=first_shift_end, ends_at=second_shift_end),
               Barber(name='Gloria', starts_at=first_shift_end, ends_at=second_shift_end),
               Barber(name='Heber', starts_at=first_shift_end, ends_at=second_shift_end)]

    # simulate.
    salon = HairSalon(15, 0, total_time, barbers, customers)
    salon.simulate(total_time + 40)  # last customer can arrive at 5PM and take 40 minutes to get cut


main()
