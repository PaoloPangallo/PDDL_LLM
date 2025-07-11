(define (domain xr17-mission)
    (:requirements :strips :typing)
    (:types
        entity
        robot - entity
        drone - entity
        door - entity
        terminal - entity
        location
        corridor - location
        plant_area - location
        warehouse - location
        charging_station - location
        em_interference_zone - corridor
        maintenance_tunnel - corridor
        charging_dock - entity
        battery_module - entity
        em_shield_coil - entity
        emergency_battery - battery_module
    )
    (:predicates
        (at ?x - entity ?l - location)
        (connected ?from - location ?to - location)
        (door_locked ?d - door)
        (has_access_code ?h - robot)
        (drone_neutralized ?d - drone)
        (terminal_hacked ?t - terminal)
        (shield_acquired ?h - robot)
        (battery_critical ?h - robot)
        (charging ?h - robot ?c - charging_dock)
        (recharged ?h - robot)
        (emp_active ?d - drone)
    )
    (:action reroute_power
        :parameters (
        ?r - robot
        ?d - door
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
            (door_locked ?d)
        )
        :effect (and
            (not (door_locked ?d))
        )
    )
    (:action hack_terminal
        :parameters (
        ?r - robot
        ?t - terminal
        ?d - drone
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?t ?l)
            (drone_neutralized ?d)
            (at ?d ?l)
            (not (terminal_hacked ?t))
        )
        :effect (and
            (terminal_hacked ?t)
            (has_access_code ?r)
        )
    )
    (:action neutralize_drone_emp
        :parameters (
        ?r - robot
        ?d - drone
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
            (not (emp_active ?d))
        )
        :effect (and
            (emp_active ?d)
            (drone_neutralized ?d)
        )
    )
    (:action stealth_through_drone_zone
        :parameters (
        ?r - robot
        ?d - drone
        ?c - corridor
        )
        :precondition (and
            (at ?r ?c)
            (at ?d ?c)
            (not (emp_active ?d))
        )
        :effect (and
        )
    )
    (:action sprint_through_em_zone
        :parameters (
        ?r - robot
        ?c - em_interference_zone
        )
        :precondition (and
            (at ?r ?c)
        )
        :effect (and
        )
    )
    (:action acquire_shield_coil
        :parameters (
        ?r - robot
        ?s - em_shield_coil
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?s ?l)
            (not (shield_acquired ?r))
        )
        :effect (and
            (shield_acquired ?r)
            (not (at ?s ?l))
        )
    )
    (:action move
        :parameters (
        ?r - robot
        ?from - location
        ?to - location
        )
        :precondition (and
            (at ?r ?from)
            (connected ?from ?to)
        )
        :effect (and
            (at ?r ?to)
            (not (at ?r ?from))
        )
    )
    (:action charge_hypercharge_dock
        :parameters (
        ?r - robot
        ?c - charging_dock
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?c ?l)
        )
        :effect (and
            (recharged ?r)
            (not (battery_critical ?r))
        )
    )
    (:action charge_battery_swap
        :parameters (
        ?r - robot
        ?c - charging_dock
        ?b - emergency_battery
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?c ?l)
            (has_access_code ?r)
            (at ?b ?l)
        )
        :effect (and
            (recharged ?r)
            (not (battery_critical ?r))
            (not (at ?b ?l))
        )
    )
)