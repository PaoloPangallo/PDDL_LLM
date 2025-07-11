(define (domain xr17-recharge-mission)
    (:requirements :strips :typing)
    (:types
        entity
        robot_type - entity
        door_type - entity
        panel_type - entity
        drone_type - entity
        location_type - entity
        terminal_type - entity
        zone_type - entity
        battery_type - entity
        dock_type - entity
        module_type - entity
        start_location_type
        door_cleared_location_type
        warehouse_entrance_location_type
        emi_cleared_location_type
        drone_cleared_location_type
        battery_pickup_location_type
        charging_station_location_type
    )
    (:predicates
        (at ?x - entity ?l - location_type)
        (panel_damaged ?p - panel_type)
        (door_sealed ?d - door_type)
        (door_open ?d - door_type)
        (door_bypassed ?d - door_type)
        (entered_warehouse)
        (active ?d - drone_type)
        (drone_neutralized ?d - drone_type)
        (terminal_available ?t - terminal_type)
        (access_code_obtained)
        (in_emi_zone ?z - zone_type)
        (not_shielded)
        (battery_lowered)
        (has_shielding)
        (drone_patrolling ?d - drone_type)
        (battery_sufficient_stealth)
        (drone_eluded ?d - drone_type)
        (battery_sufficient_emp)
        (drone_disabled ?d - drone_type)
        (emergency_battery_collected)
        (battery_available ?b - battery_type)
        (dock_available ?d - dock_type)
        (battery_critical)
        (battery_full)
        (contact_established)
        (module_available ?m - module_type)
    )
    (:action Bypass_Door_Reroute
        :parameters (
        ?robot - robot_type
        ?door - door_type
        ?panel - panel_type
        ?start_loc - start_location_type
        ?door_cleared_loc - door_cleared_location_type
        )
        :precondition (and
            (at ?robot ?start_loc)
            (panel_damaged ?panel)
            (door_sealed ?door)
        )
        :effect (and
            (door_open ?door)
            (at ?robot ?door_cleared_loc)
            (door_bypassed ?door)
            (not (door_sealed ?door))
            (not (panel_damaged ?panel))
            (not (at ?robot ?start_loc))
        )
    )
    (:action Detour_Through_Warehouse
        :parameters (
        ?robot - robot_type
        ?door - door_type
        ?start_loc - start_location_type
        ?warehouse_entrance_loc - warehouse_entrance_location_type
        )
        :precondition (and
            (at ?robot ?start_loc)
            (door_sealed ?door)
        )
        :effect (and
            (at ?robot ?warehouse_entrance_loc)
            (entered_warehouse)
            (not (at ?robot ?start_loc))
        )
    )
    (:action Neutralize_Warehouse_Drone
        :parameters (
        ?robot - robot_type
        ?drone - drone_type
        ?location - warehouse_entrance_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (active ?drone)
            (entered_warehouse)
        )
        :effect (and
            (drone_neutralized ?drone)
            (not (active ?drone))
        )
    )
    (:action Retrieve_Access_Code
        :parameters (
        ?robot - robot_type
        ?drone - drone_type
        ?terminal - terminal_type
        ?location - warehouse_entrance_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (drone_neutralized ?drone)
            (terminal_available ?terminal)
        )
        :effect (and
            (access_code_obtained)
            (not (terminal_available ?terminal))
        )
    )
    (:action Open_Door_With_Code
        :parameters (
        ?robot - robot_type
        ?door - door_type
        ?location - location_type
        ?door_cleared_loc - door_cleared_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (access_code_obtained)
            (door_sealed ?door)
        )
        :effect (and
            (door_open ?door)
            (at ?robot ?door_cleared_loc)
            (door_bypassed ?door)
            (not (door_sealed ?door))
            (not (access_code_obtained))
            (not (at ?robot ?location))
        )
    )
    (:action Sprint_Through_EMI
        :parameters (
        ?robot - robot_type
        ?zone - zone_type
        ?door_cleared_loc - door_cleared_location_type
        ?emi_cleared_loc - emi_cleared_location_type
        )
        :precondition (and
            (at ?robot ?door_cleared_loc)
            (in_emi_zone ?zone)
            (not_shielded)
        )
        :effect (and
            (at ?robot ?emi_cleared_loc)
            (battery_lowered)
            (not (at ?robot ?door_cleared_loc))
        )
    )
    (:action Hunt_Magnetic_Shielding
        :parameters (
        ?robot - robot_type
        ?location - warehouse_entrance_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (entered_warehouse)
            (not_shielded)
        )
        :effect (and
            (has_shielding)
            (at ?robot ?location)
            (not (not_shielded))
        )
    )
    (:action Traverse_EMI_With_Shielding
        :parameters (
        ?robot - robot_type
        ?zone - zone_type
        ?door_cleared_loc - door_cleared_location_type
        ?emi_cleared_loc - emi_cleared_location_type
        )
        :precondition (and
            (at ?robot ?door_cleared_loc)
            (in_emi_zone ?zone)
            (has_shielding)
        )
        :effect (and
            (at ?robot ?emi_cleared_loc)
            (not (at ?robot ?door_cleared_loc))
        )
    )
    (:action Engage_Stealth
        :parameters (
        ?robot - robot_type
        ?drone - drone_type
        ?location - emi_cleared_location_type
        ?drone_cleared_loc - drone_cleared_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (drone_patrolling ?drone)
            (battery_sufficient_stealth)
        )
        :effect (and
            (drone_eluded ?drone)
            (at ?robot ?drone_cleared_loc)
            (not (drone_patrolling ?drone))
            (not (at ?robot ?location))
        )
    )
    (:action EMP_Burst
        :parameters (
        ?robot - robot_type
        ?drone - drone_type
        ?location - emi_cleared_location_type
        ?drone_cleared_loc - drone_cleared_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (drone_patrolling ?drone)
            (battery_sufficient_emp)
        )
        :effect (and
            (drone_disabled ?drone)
            (at ?robot ?drone_cleared_loc)
            (battery_lowered)
            (not (drone_patrolling ?drone))
            (not (at ?robot ?location))
        )
    )
    (:action Collect_Emergency_Battery
        :parameters (
        ?robot - robot_type
        ?battery - battery_type
        ?location - battery_pickup_location_type
        )
        :precondition (and
            (at ?robot ?location)
            (battery_available ?battery)
        )
        :effect (and
            (emergency_battery_collected)
            (not (battery_available ?battery))
        )
    )
    (:action Use_HyperCharge
        :parameters (
        ?robot - robot_type
        ?dock - dock_type
        ?station - charging_station_location_type
        ?drone_cleared_loc - drone_cleared_location_type
        )
        :precondition (and
            (at ?robot ?drone_cleared_loc)
            (dock_available ?dock)
            (battery_critical)
        )
        :effect (and
            (battery_full)
            (contact_established)
            (at ?robot ?station)
            (not (battery_critical))
            (not (at ?robot ?drone_cleared_loc))
        )
    )
    (:action Use_Battery_Swap
        :parameters (
        ?robot - robot_type
        ?module - module_type
        ?station - charging_station_location_type
        ?battery - battery_type
        ?drone_cleared_loc - drone_cleared_location_type
        )
        :precondition (and
            (at ?robot ?drone_cleared_loc)
            (module_available ?module)
            (emergency_battery_collected)
            (battery_critical)
        )
        :effect (and
            (battery_full)
            (contact_established)
            (at ?robot ?station)
            (not (battery_critical))
            (not (emergency_battery_collected))
            (not (at ?robot ?drone_cleared_loc))
        )
    )
)