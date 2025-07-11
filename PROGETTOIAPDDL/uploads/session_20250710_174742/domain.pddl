(define (domain helios-dynamics-robot-rescue)
    (:requirements :strips :typing)
    (:types
        entity
        robot - entity
        drone_guard - entity
        location
        door_panel - entity
        terminal - entity
        device - entity
        battery_unit - entity
        charging_station - location
        module - entity
    )
    (:predicates
        (at ?x - entity ?l - location)
        (has_battery_level ?r - robot ?level - battery_unit)
        (powered ?d - door_panel)
        (access_code_retrieved ?r - robot)
        (drone_disabled ?d - drone_guard)
        (shielding_active ?r - robot)
        (charging ?r - robot ?c - charging_station)
        (contact_restored ?r - robot)
        (connected ?from - location ?to - location)
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
    (:action reroute_power_bypass_fuses
        :parameters (
        ?r - robot
        ?d - door_panel
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
            (powered ?d)
        )
        :effect (and
            (not (powered ?d))
        )
    )
    (:action detour_maintenance_tunnel
        :parameters (
        ?r - robot
        ?d - drone_guard
        ?t - terminal
        ?m - location
        ?w - location
        )
        :precondition (and
            (at ?r ?w)
            (at ?d ?m)
            (at ?t ?m)
        )
        :effect (and
            (access_code_retrieved ?r)
            (not (at ?d ?m))
        )
    )
    (:action sprint_through_em_zone
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
    (:action use_em_shielding_coil
        :parameters (
        ?r - robot
        ?c - device
        ?w - location
        ?m - location
        )
        :precondition (and
            (at ?r ?w)
            (at ?c ?w)
        )
        :effect (and
            (shielding_active ?r)
        )
    )
    (:action stealth_navigation
        :parameters (
        ?r - robot
        ?d - drone_guard
        ?l - location
        ?next - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
            (not (drone_disabled ?d))
        )
        :effect (and
            (at ?r ?next)
            (not (at ?r ?l))
        )
    )
    (:action emp_burst_disable_drone
        :parameters (
        ?r - robot
        ?d - drone_guard
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
        )
        :effect (and
            (drone_disabled ?d)
        )
    )
    (:action charge_hypercharge_dock
        :parameters (
        ?r - robot
        ?c - charging_station
        ?m - module
        )
        :precondition (and
            (at ?r ?c)
            (at ?m ?c)
        )
        :effect (and
            (contact_restored ?r)
        )
    )
    (:action charge_battery_swap_module
        :parameters (
        ?r - robot
        ?c - charging_station
        ?m - module
        ?b - battery_unit
        )
        :precondition (and
            (at ?r ?c)
            (at ?m ?c)
            (has_battery_level ?r ?b)
        )
        :effect (and
            (contact_restored ?r)
        )
    )
)