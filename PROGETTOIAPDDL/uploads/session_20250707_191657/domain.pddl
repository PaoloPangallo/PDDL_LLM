(define (domain rover-domain)
  (:requirements :strips :typing)
  (:types agent vehicle location object)
  (:predicates (at ?x - object ?y - location)
               (in ?a - agent ?v - vehicle)
               (has ?a - agent ?o - object)
               (at ?v - vehicle ?l - location))
  (:action mount-rover
    :parameters (?a - agent ?r - vehicle ?l - location)
    :precondition (and (at ?a ?l) (at ?r ?l))
    :effect (and (not (at ?a ?l)) (in ?a ?r)))
  (:action drive
    :parameters (?r - vehicle ?from - location ?to - location)
    :precondition (and (in ?a ?r) (at ?r ?from))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action dismount-rover
    :parameters (?a - agent ?r - vehicle ?l - location)
    :precondition (and (in ?a ?r) (at ?r ?l))
    :effect (and (not (in ?a ?r)) (at ?a ?l)))
  (:action pickup
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (at ?o ?l))
    :effect (and (has ?a ?o) (not (at ?o ?l))))
)