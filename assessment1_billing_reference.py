"""Procedural billing prototype for Taylor's Smart Campus EV system."""

from math import ceil


CHARGER_RATES = {
    "AC": ((2, 4.00), (4, 6.00), (6, 8.00), (float("inf"), 12.00)),
    "DC": ((2, 10.00), (4, 15.00), (6, 20.00), (float("inf"), 30.00)),
}
OVERTIME_CAPS = {"AC": 80.00, "DC": 150.00}


def calculate_bill(member_type, charger_type, hours, first_time=False,
                   peak=False, idle=False, lost_card=False, eco_pass=False):
    """Return an itemized bill; all amounts are in Malaysian ringgit."""
    billable_hours = ceil(hours)  # any part of an hour is charged as a full hour
    gross = 0.0
    remaining = billable_hours
    previous_limit = 0
    for upper_limit, hourly_rate in CHARGER_RATES[charger_type]:
        tier_hours = min(max(remaining - previous_limit, 0),
                         upper_limit - previous_limit)
        gross += tier_hours * hourly_rate
        previous_limit = upper_limit
        if remaining <= upper_limit:
            break
    if billable_hours > 6:
        gross = min(gross, OVERTIME_CAPS[charger_type])

    discount_rate = 0.0
    flat_discount = 0.0
    waiver = False
    if first_time:
        waiver = True  # complimentary first charge replaces other discounts
    elif member_type == "staff":
        discount_rate = 0.50
    elif member_type == "student" and charger_type == "AC":
        discount_rate = 0.25
    if eco_pass and not first_time:
        flat_discount = 2.00

    percentage_discount = gross * discount_rate
    if waiver:
        percentage_discount = gross
        flat_discount = 0.0
    subtotal = max(0.0, gross - percentage_discount)
    surcharge_items = [5.00 if peak else 0.0,
                       15.00 if idle else 0.0,
                       30.00 if lost_card else 0.0]
    surcharges = sum(surcharge_items)
    # The Eco-Pass discount applies to the total after surcharges are added.
    flat_discount = min(flat_discount, subtotal + surcharges)
    net = subtotal + surcharges - flat_discount
    return {
        "hours": billable_hours, "gross": gross,
        "percentage_discount": percentage_discount,
        "flat_discount": flat_discount, "waiver": waiver,
        "peak_surcharge": 5.00 if peak else 0.0,
        "idle_surcharge": 15.00 if idle else 0.0,
        "card_fee": 30.00 if lost_card else 0.0,
        "net": net,
    }


def prompt_yes_no(message):
    while True:
        answer = input(message + " (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter y or n.")


def main():
    print("Taylor's Smart Campus EV Billing")
    while True:
        user_id = input("User ID: ").strip()
        vehicle_number = input("Vehicle number: ").strip().upper()
        member_type = input("Member type (staff/student/visitor): ").strip().lower()
        while member_type not in ("staff", "student", "visitor"):
            member_type = input("Enter staff, student, or visitor: ").strip().lower()
        charger_type = input("Charger type (AC/DC): ").strip().upper()
        while charger_type not in CHARGER_RATES:
            charger_type = input("Enter AC or DC: ").strip().upper()
        while True:
            try:
                hours = float(input("Hours charged (> 0): "))
                if hours > 0:
                    break
                print("Hours must be greater than zero.")
            except ValueError:
                print("Enter a numeric duration.")

        first_time = prompt_yes_no("First-time registered user")
        eco_pass = prompt_yes_no("Certified Green Eco-Pass")
        peak = prompt_yes_no("Session during 12 PM–4 PM")
        idle = prompt_yes_no("Vehicle remained after full charge")
        lost_card = prompt_yes_no("Lost RFID card replacement required")
        bill = calculate_bill(member_type, charger_type, hours, first_time,
                              peak, idle, lost_card, eco_pass)

        print("\n--- ITEMIZED EV BILL ---")
        print(f"User / vehicle: {user_id} / {vehicle_number}")
        print(f"Charger / billable hours: {charger_type} / {bill['hours']}")
        print(f"Gross charging fee:          RM {bill['gross']:7.2f}")
        print(f"Member discount:            -RM {bill['percentage_discount']:7.2f}")
        print(f"Eco-Pass discount:          -RM {bill['flat_discount']:7.2f}")
        if bill["waiver"]:
            print("First-time waiver:           applied")
        print(f"Peak-hour surcharge:         RM {bill['peak_surcharge']:7.2f}")
        print(f"Idle surcharge:              RM {bill['idle_surcharge']:7.2f}")
        print(f"RFID replacement fee:        RM {bill['card_fee']:7.2f}")
        print(f"NET PAYABLE:                 RM {bill['net']:7.2f}")
        if not prompt_yes_no("Process another vehicle"):
            print("Billing session closed.")
            break


if __name__ == "__main__":
    main()
