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

from typing import Tuple, List, Union, Deque, Optional, TypeVar
from collections import deque
from random import seed, randint
from enum import Enum

import numpy as np

_CUTTING_TIME = 30


def _minutes_to_hhmm(minutes: int, offset: int = 9):
    hours = minutes // 60
    # add offset
    hours += offset
    hours_str = str(hours)
    if len(hours_str) == 1:
        hours_str = '0' + hours_str
    hour_minutes = minutes % 60
    hour_minutes_str = str(hour_minutes)
    if len(hour_minutes_str) == 1:
        hour_minutes_str = '0' + hour_minutes_str

    return hours_str + ':' + hour_minutes_str


# quick and dirty tests, normally I wouldn't do it like this.
assert _minutes_to_hhmm(0) == '09:00'
assert _minutes_to_hhmm(1) == '09:01'
assert _minutes_to_hhmm(480) == '17:00'


def _add_name_time(minute, who, action):
    pretty_time = _minutes_to_hhmm(minute)
    return f'[{pretty_time}] [{who.str_id}] {action}'


class BarberStatus(Enum):
    NOT_STARTED = 1
    IN_SHIFT = 2
    CUTTING = 3
    FINISHED = 4


class CustomerStatus(Enum):
    NOT_STARTED = 1
    ARRIVED = 2
    IN_Q = 3
    FINISHED = 4


class Customer(object):

    def __init__(self, arrives_at: int, name: str, time_to_process: int):
        self.arrives_at = arrives_at
        self.str_id = name
        self.time_to_process = time_to_process
        self.waits_until: Optional[int] = None
        self.status = CustomerStatus.NOT_STARTED
        self.fulfillment_status: Optional[str] = None

    def cannot_enqueue_closed(self) -> List[str]:
        self.status = CustomerStatus.FINISHED
        self.fulfillment_status = '[left] cursing themselves'

        return [self.fulfillment_status]

    def cannot_enqueue_q_full(self) -> List[str]:
        self.status = CustomerStatus.FINISHED
        self.fulfillment_status = '[left] impatiently'

        return [self.fulfillment_status]

    def cannot_process_barbers_left(self) -> List[str]:
        self.status = CustomerStatus.FINISHED
        self.fulfillment_status = '[left] furiously'

        return [self.fulfillment_status]

    def can_enqueue(self, time) -> None:
        self.status = CustomerStatus.IN_Q
        self.waits_until = time + self.time_to_process

    def start_cutting(self) -> None:
        self.status = CustomerStatus.FINISHED
        self.fulfillment_status = '[left] satisfied'

    def simulate(self, time) -> Tuple[CustomerStatus, List[str]]:
        messages: List[str] = []
        if self.status == CustomerStatus.FINISHED:
            # no-op.
            pass
        elif self.status == CustomerStatus.IN_Q:
            if time == self.waits_until:
                self.status = CustomerStatus.FINISHED
                self.fulfillment_status = '[left] unfulfilled'
                messages = [self.fulfillment_status]
        elif self.status == CustomerStatus.NOT_STARTED:
            if time == self.arrives_at:
                self.status = CustomerStatus.ARRIVED
                messages = ['entered']
        else:
            raise KeyError('unknown status')

        return self.status, messages


class Barber(object):
    def __init__(self, starts_at: int, ends_at: int, name: str) -> None:
        self.str_id = name
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.active_customer: Optional[Customer] = None
        self.active_customer_finish_at: Optional[int] = None
        self.status = BarberStatus.NOT_STARTED

    def add_customer(self, customer: Customer, finishes_at: int) -> List[str]:
        assert self.status == BarberStatus.IN_SHIFT
        assert self.active_customer is None
        assert self.active_customer_finish_at is None

        self.active_customer = customer
        self.active_customer_finish_at = finishes_at

        self.status = BarberStatus.CUTTING

        return [f"[started] cutting [{self.active_customer.str_id}]'s hair"]

    def simulate(self, time: int) -> Tuple[BarberStatus, List[str]]:
        messages: List[str] = []

        if self.status == BarberStatus.FINISHED:
            # no-op
            pass
        elif self.status == BarberStatus.NOT_STARTED:
            if self.starts_at == time:
                self.status = BarberStatus.IN_SHIFT
                messages = ['[started] shift']
        elif self.status == BarberStatus.IN_SHIFT:
            if self.ends_at <= time:
                self.status = BarberStatus.FINISHED
                messages = ['[ended] shift']
        elif self.status == BarberStatus.CUTTING:
            assert self.active_customer
            if self.active_customer_finish_at == time:
                if self.ends_at > time:
                    self.status = BarberStatus.IN_SHIFT
                    messages = [f"[ended] cutting [{self.active_customer.str_id}]'s hair"]
                else:
                    self.status = BarberStatus.FINISHED
                    messages = [f"[ended] cutting [{self.active_customer.str_id}]'s hair",
                                '[ended] shift']

                self.active_customer = None
                self.active_customer_finish_at = None
        else:
            raise KeyError('bad status')

        return self.status, messages


HairSalonType = TypeVar('HairSalonType', bound='HairSalon')
class HairSalon(object):
    def __init__(self, capacity: int, opens_at: int, closes_at: int,
                 barbers_to_start: List[Barber], customers_to_start: List[Customer]):
        self.capacity = capacity
        self.waiting_customers: Deque[Customer] = deque()
        self.barbers_to_start = barbers_to_start
        self.active_barbers: List[Barber] = []
        self.customers_to_start = customers_to_start
        self.opens_at = opens_at
        self.closes_at = closes_at
        self.str_id = 'Hair Salon'
        self.messages: List[str] = []

    def add_messages(self, new_messages: List[str],
                     minute: int, what: Union[Customer, Barber, HairSalonType]):
        if len(new_messages) > 0:
            self.messages.extend([_add_name_time(minute, what, message) for message in new_messages])

    def can_append_customer(self):
        return len(self.waiting_customers) < self.capacity

    def simulate_begin_shift(self, minute):
        to_remove = []
        for waiting_barber in self.barbers_to_start:
            status, messages = waiting_barber.simulate(minute)
            self.add_messages(messages, minute, waiting_barber)
            if status == BarberStatus.IN_SHIFT:
                self.active_barbers.append(waiting_barber)
                to_remove.append(waiting_barber)

        for now_active_barber in to_remove:
            self.barbers_to_start.remove(now_active_barber)

    def simulate_end_shift(self, minute):
        to_remove = []
        for barber in self.active_barbers:
            status, messages = barber.simulate(minute)
            self.add_messages(messages, minute, barber)

            if status == BarberStatus.FINISHED:
                to_remove.append(barber)

        # remove barbers that ended shift.
        for barber in to_remove:
            self.active_barbers.remove(barber)

    def simulate_close(self, minute: int) -> bool:
        if len(self.active_barbers) == 0:
            assert minute >= self.closes_at
            for customer in self.waiting_customers:
                messages = customer.cannot_process_barbers_left()
                self.add_messages(messages, minute, customer)

            self.add_messages(['closed'], minute, self)

            self.waiting_customers = deque()
            return False
        else:
            return True

    def simulate_incoming_customers(self, minute):
        to_remove = []
        for customer in self.customers_to_start:
            status, messages = customer.simulate(minute)
            self.add_messages(messages, minute, customer)

            messages = []
            if status == CustomerStatus.ARRIVED:
                # Customer will be processed or will leave.
                to_remove.append(customer)
                if minute > self.closes_at:
                    messages = customer.cannot_enqueue_closed()
                elif not self.can_append_customer():
                    messages = customer.cannot_enqueue_q_full()
                else:
                    customer.can_enqueue(minute)
                    self.waiting_customers.append(customer)

            self.add_messages(messages, minute, customer)

        for customer in to_remove:
            self.customers_to_start.remove(customer)

    def simulate_waiting_customers(self, minute):
        to_remove = []
        for customer in self.waiting_customers:
            # try to find a free barber.
            for active_barber in self.active_barbers:
                if active_barber.status == BarberStatus.IN_SHIFT:
                    # let's service this customer.
                    messages = active_barber.add_customer(customer, minute + _CUTTING_TIME)
                    self.add_messages(messages, minute, active_barber)

                    # we no longer care about this customer, it's being done and will be done no matter what.
                    customer.start_cutting()
                    to_remove.append(customer)
                    break
            else:
                # no free barber, customer unserviced.
                status, messages = customer.simulate(minute)
                self.add_messages(messages, minute, customer)

                if status == CustomerStatus.FINISHED:
                    to_remove.append(customer)

        # remove customers that started processing or those that left.
        for customer in to_remove:
            self.waiting_customers.remove(customer)

    def simulate_minute(self, minute):
        if minute == self.opens_at:
            self.add_messages(['opened'], minute, self)

        self.simulate_end_shift(minute)

        self.simulate_begin_shift(minute)

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
    for message in salon.messages:
        print(message)


main()
