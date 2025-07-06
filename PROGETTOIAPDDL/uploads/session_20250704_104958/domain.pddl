(define (domain BatteryRecharge)
  (:requirements :strips :typing)
  (:types Robot ChargingStation Block Obstacle)
  (:predicates (at ?Robot ?ChargingStation) (on-ground ?Battery ?ChargingStation) (blocked ?Obstacle) (at - at) (on-ground - on-ground) (blocked - blocked))
  (:action ReachChargingStation
    :parameters (?Robot - Robot ?ChargingStation - ChargingStation)
    :precondition (and (at robot charging-station) (on-ground battery charging-station))
    :effect (and (at ?Robot ?ChargingStation) (not (blocked ?Obstacle))))
  (:action UnknownAction - unknown action))