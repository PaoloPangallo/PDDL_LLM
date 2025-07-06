(define (domain RechargeBattery)
  (:requirements :strips :adl)
  (:types robot battery charging-station obstacle)
  (:predicates (at ?r ?s) (on-ground ?b ?s) (blocked ?o ?s))
  (:action move-robot-to-charging-station
    :parameters (?r ?cs - charging-station)
    :precondition (and (at ?r ?s) (not (blocked ?r ?cs)))
    :effect (and (at ?r ?cs) (on-ground ?b ?cs))))